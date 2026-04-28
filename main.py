import os
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
import traceback
from typing import List, Optional, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

import models
import schemas
import httpx
import database
from typing import Dict, Any, List
import time

# Cache for Notion page list to reduce API calls and latency
NOTION_PAGE_CACHE = {
    "data": None,
    "timestamp": 0
}
CACHE_TTL = 300  # 5 minutes

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="Tents Database AI API")

# Helper for tool sessions
def get_db_session():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Tool: List and Filter Tents
def list_tents(skip: int = 0, min_price: Optional[float] = None, max_price: Optional[float] = None):
    """List all available tents with optional price filtering."""
    db = next(get_db_session())
    try:
        # Cast skip to int to ensure type safety
        skip = int(skip)
        
        query = db.query(models.Tent)
        if min_price is not None:
            query = query.filter(models.Tent.price >= min_price)
        if max_price is not None:
            query = query.filter(models.Tent.price <= max_price)
            
        tents = query.offset(skip).all()
        print(f"[DEBUG] Tool: list_tents(skip={skip}, min_price={min_price}, max_price={max_price}) - Found {len(tents)}")
        return [{"id": t.id, "name": t.name, "brand": t.brand, "price": t.price} for t in tents]
    finally:
        db.close()

# Tool: Search Tents by Name
def search_tents(query: str):
    """Search for tents by name or brand keyword."""
    db = next(get_db_session())
    try:
        tents = db.query(models.Tent).filter(
            (models.Tent.name.ilike(f"%{query}%")) | (models.Tent.brand.ilike(f"%{query}%"))
        ).limit(20).all()
        print(f"[DEBUG] Tool: search_tents(query='{query}') - Found {len(tents)}")
        return [{"id": t.id, "name": t.name, "brand": t.brand, "price": t.price} for t in tents]
    finally:
        db.close()

def get_tent_by_id(tent_id: int):
    """
    指定したIDのテントの詳細情報を取得します。
    """
    print(f"[DEBUG] Tool: get_tent_by_id(id={tent_id})")
    db = next(get_db_session())
    try:
        t = db.query(models.Tent).filter(models.Tent.id == tent_id).first()
        if not t:
            return f"テントID {tent_id} は見つかりませんでした。"
        return {
            "id": t.id, "name": t.name, "brand": t.brand, "price": t.price,
            "capacity": t.capacity, "material": t.material, "purchase_date": str(t.purchase_date)
        }
    finally:
        db.close()

def get_tent_stats():
    """
    テントの統計データ（合計数、平均価格など）を取得します。
    """
    print("[DEBUG] Tool: get_tent_stats()")
    db = next(get_db_session())
    try:
        count = db.query(func.count(models.Tent.id)).scalar()
        avg_price = db.query(func.avg(models.Tent.price)).scalar()
        return {
            "total_count": count,
            "avg_price": round(avg_price, 2) if avg_price else 0
        }
    finally:
        db.close()

def update_tent_fields(tent_id: int, updates: Dict[str, Any]):
    """
    指定したIDのテントの情報を「画面上のみ」更新提案します。
    更新可能なフィールド: name, brand, price, capacity, weight_kg, material, purchase_date,
    size_w, size_d, size_h, pack_w, pack_d, pack_h
    
    TIPS: Size/Packの情報を "210x130x105" のような形式で受け取った場合、自動的に W/D/H に分解します。
    """
    import json
    
    # スマートパース機能: "size" や "pack" というキーで "WxDxH" 形式が来たら分解する
    new_updates = dict(updates)
    for composite_key in ['size', 'pack']:

        if composite_key in new_updates and isinstance(new_updates[composite_key], str):
            val = new_updates.pop(composite_key)
            parts = val.replace('x', ' ').replace('*', ' ').split()
            if len(parts) >= 3:
                new_updates[f"{composite_key}_w"] = parts[0]
                new_updates[f"{composite_key}_d"] = parts[1]
                new_updates[f"{composite_key}_h"] = parts[2]

    def decimal_default(obj):
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return float(obj)
        return str(obj)

    proposal = {"id": tent_id, "updates": new_updates}
    return f"[UI_PROPOSAL: {json.dumps(proposal, default=decimal_default)}]"


def bulk_update_tents(tent_ids: List[int], updates: Dict[str, Any]):
    """
    複数のテントに対して、同一の変更を一括で「画面上のみ」更新提案します。
    TIPS: Size/Packの情報を "210x130x105" のような形式で受け取った場合、自動的に W/D/H に分解します。
    """
    import json
    
    new_updates = dict(updates)
    for composite_key in ['size', 'pack']:

        if composite_key in new_updates and isinstance(new_updates[composite_key], str):
            val = new_updates.pop(composite_key)
            parts = val.replace('x', ' ').replace('*', ' ').split()
            if len(parts) >= 3:
                new_updates[f"{composite_key}_w"] = parts[0]
                new_updates[f"{composite_key}_d"] = parts[1]
                new_updates[f"{composite_key}_h"] = parts[2]

    def decimal_default(obj):
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return float(obj)
        return str(obj)

    proposal = {"ids": tent_ids, "updates": new_updates}
    return f"[UI_BULK_PROPOSAL: {json.dumps(proposal, default=decimal_default)}]"


def delete_tent_by_id(tent_id: int):
    """
    指定したIDのテントを「画面上のみ」削除提案します。
    """
    import json
    print(f"[DEBUG] Tool: delete_tent_by_id(id={tent_id}) proposal")
    proposal = {"id": tent_id, "delete": True}
    return f"[UI_DELETE_PROPOSAL: {json.dumps(proposal)}]"

def add_tent(name: str, brand: str = None, price: float = None, capacity: float = None):
    """
    新しいテントを「画面上のみ」追加提案します。
    """
    import json
    new_data = {
        "id": -1, # マーカー
        "name": name,
        "brand": brand,
        "price": price,
        "capacity": capacity
    }
    print(f"[DEBUG] Tool: add_tent(name={name}) proposal")
    return f"[UI_ADD_PROPOSAL: {json.dumps(new_data)}]"

def validate_ui_proposals(proposals: List[Dict[str, Any]]):
    """
    提案された変更内容が妥当か検証します。
    proposals: [{"id": 1, "updates": {"price": 100}}] のような形式。
    """
    errors = []
    numeric_fields = ['price', 'capacity', 'weight_kg', 'size_w', 'size_d', 'size_h', 'pack_w', 'pack_d', 'pack_h']
    
    for p in proposals:
        tid = p.get("id")
        updates = p.get("updates", {})
        for field, value in updates.items():
            if field in numeric_fields:
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.push(f"ID {tid}: {field} は数値である必要があります（現在の値: {value}）")
            if field == 'name' and not str(value).strip():
                errors.push(f"ID {tid}: 名前を空にすることはできません。")
    
    if errors:
        return f"検証エラーが発生しました:\n" + "\n".join(errors)
    return "検証OK: 全てのデータが妥当です。書き込みが可能です。"



# --- Notion API Tools via Direct HTTP (httpx) ---

NOTION_API_VERSION = "2022-06-28"
# 「煩悩テント」親ページ ID
BONNOU_TENT_PARENT_ID = "10c9fa68-e7ac-809a-8512-eca278b82750"

def list_notion_tents() -> Any:
    """
    「煩悩テント」親ページの下にある子ページ（各テント）の一覧を取得します。
    ページネーション（100件以上の取得）に対応。
    """
    token = (os.getenv("NOTION_TOKEN") or "").strip()
    if not token: return "ERROR: Notion token missing."
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION
    }
    
    output = []
    has_more = True
    start_cursor = None
    
    print(f"[DEBUG] Notion Sync: Fetching all children of {BONNOU_TENT_PARENT_ID}")
    
    # Check cache
    now = time.time()
    if NOTION_PAGE_CACHE["data"] is not None and (now - NOTION_PAGE_CACHE["timestamp"]) < CACHE_TTL:
        print(f"[DEBUG] Notion Sync: Returning cached data ({len(NOTION_PAGE_CACHE['data'])} items)")
        return NOTION_PAGE_CACHE["data"]

    try:
        with httpx.Client() as client:
            while has_more:
                url = f"https://api.notion.com/v1/blocks/{BONNOU_TENT_PARENT_ID}/children"
                params = {}
                if start_cursor:
                    params["start_cursor"] = start_cursor
                
                response = client.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    return f"ERROR: API {response.status_code} - {response.text}"
                    
                data = response.json()
                results = data.get("results", [])
                
                # Filter only child_page types and collect
                for b in results:
                    if b["type"] == "child_page":
                        output.append({
                            "page_id": b["id"],
                            "name": b["child_page"].get("title", "Untitled Page")
                        })
                
                has_more = data.get("has_more", False)
                start_cursor = data.get("next_cursor")
                print(f"[DEBUG] Notion Sync: Fetched {len(results)} items, cumulative output count: {len(output)}")
                
            print(f"[DEBUG] Notion Sync: Finished fetching all {len(output)} tent pages.")
            
            # Update cache
            NOTION_PAGE_CACHE["data"] = output
            NOTION_PAGE_CACHE["timestamp"] = time.time()
            
            return output if output else "煩悩テントの下に子ページが見つかりませんでした。"
    except Exception as e:
        print(f"[ERROR] Notion Sync Exception: {str(e)}")
        return f"Error connecting to Notion: {str(e)}"


def get_notion_tent_detail(page_id: str) -> Any:
    """
    指定されたテントページの「本文（テキストブロック）」をすべて読み取り、平文（非構造化データ）として返します。
    """
    token = (os.getenv("NOTION_TOKEN") or "").strip()
    if not token: return "ERROR: Notion token missing."
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION
    }
    
    print(f"[DEBUG] Notion Content (Direct API): Reading blocks for {page_id}")
    try:
        with httpx.Client() as client:
            # Get block children (the page content)
            url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            response = client.get(url, headers=headers)
            
            if response.status_code != 200:
                return f"ERROR: API {response.status_code} - {response.text}"
                
            data = response.json()
            results = data.get("results", [])
            
            # Extract plain text from paragraphs, list items, etc.
            text_parts = []
            for b in results:
                btype = b["type"]
                content_obj = b.get(btype, {})
                rich_text = content_obj.get("rich_text", [])
                text = "".join(t.get("plain_text", "") for t in rich_text)
                if text:
                    text_parts.append(text)
            
            full_text = "\n".join(text_parts)
            print(f"[DEBUG] Notion Content: Extracted {len(full_text)} characters.")
            
            # Return result as a dictionary containing the unstructured text for AI to parse
            return {
                "page_id": page_id,
                "unstructured_content": full_text
            }
    except Exception as e:
        print(f"[ERROR] Notion Content Failure: {str(e)}")
        return f"Failed to retrieve Notion page text: {str(e)}"

def add_notion_tent_to_db(page_id: str):
    """
    Notionのデータを取得し、ローカルのデータベースに「一発登録」します。
    """
    print(f"[DEBUG] Tool: add_notion_tent_to_db(page_id={page_id})")
    detail = get_notion_tent_detail(page_id)
    if isinstance(detail, str): return detail # Return error string
    
    if not detail.get("name") or detail.get("name") == "Unnamed Tent": 
        return "ERROR: Page has no valid name, cannot import."
    
    # Ensure numerical values are correctly typed for models.Tent
    try:
        price = float(detail.get("price")) if detail.get("price") is not None else 0.0
        capacity = float(detail.get("capacity")) if detail.get("capacity") is not None else 0.0
    except (ValueError, TypeError):
        price = 0.0
        capacity = 0.0

    return add_tent(
        name=detail["name"],
        brand=detail.get("brand"),
        price=price,
        capacity=capacity
    )

# --- End Notion Tools ---

def sync_all_from_notion(tent_ids: List[int]):
    """
    指定した全てのテントIDについて、Notionから情報を一括取得して画面に反映提案します。
    内部で asyncio を使用して並列処理を行い、高速に同期します。
    """
    import json, re, asyncio
    print(f"[DEBUG] Tool: sync_all_from_notion (PARALLEL BRIDGE) for {len(tent_ids)} items")
    
    notion_pages = list_notion_tents()
    if isinstance(notion_pages, str): return notion_pages
    
    db = next(get_db_session())
    final_proposals = ""
    processed_count = 0
    try:
        tents_in_db = db.query(models.Tent).filter(models.Tent.id.in_(tent_ids)).all()
        id_name_map = {t.id: t.name for t in tents_in_db}
        
        async def run_parallel_sync():
            tasks = []
            task_info = []
            for tid in tent_ids:
                name = id_name_map.get(tid)
                if not name: continue
                page = next((p for p in notion_pages if p['name'] == name), None)
                if not page: continue
                tasks.append(get_notion_tent_detail_async(page['id']))
                task_info.append(tid)
            
            if not tasks: return []
            return await asyncio.gather(*tasks), task_info

        # Run the async loop inside the sync tool
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If running in FastAPI (which is async), we must use another way
                import nest_asyncio
                nest_asyncio.apply()
                details, task_info = loop.run_until_complete(run_parallel_sync())
            else:
                details, task_info = loop.run_until_complete(run_parallel_sync())
        except Exception as e:
            # Fallback for complex loop environments
            details, task_info = asyncio.run(run_parallel_sync())
        
        for tid, detail in zip(task_info, details):
            if isinstance(detail, dict) and "unstructured_content" in detail:
                text = detail["unstructured_content"]
                updates = {}
                # SOFTENED STRICT: Extract Purchase Date in various formats
                d_m = re.search(r'(?:購入日|purchase\s*date)[\s:：]*(\d{4})[-/年\s](\d{1,2})[-/月\s](\d{1,2})', text, re.IGNORECASE)
                if d_m:
                    y, m, d = d_m.groups()
                    raw_date = f"{y}-{int(m):02d}-{int(d):02d}"
                    updates['purchase_date'] = raw_date

                
                if updates:
                    final_proposals += f"[UI_PROPOSAL: {json.dumps({'id': tid, 'updates': updates})}]\n"
                    processed_count += 1
        
        return f"合計 {processed_count} 件の Notion 購入情報を同期反映しました。\n{final_proposals}"
    finally:
        db.close()

async def get_notion_tent_detail_async(page_id: str) -> Any:
    # (Helper remained async as it's called within gather)
    token = (os.getenv("NOTION_TOKEN") or "").strip()
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_API_VERSION}
    async with httpx.AsyncClient() as client:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        try:
            response = await client.get(url, headers=headers)
            if response.status_code != 200: return {}
            data = response.json()
            text_parts = []
            for b in data.get("results", []):
                btype = b["type"]
                rich_text = b.get(btype, {}).get("rich_text", [])
                text = "".join(t.get("plain_text", "") for t in rich_text)
                if text: text_parts.append(text)
            return {"page_id": page_id, "unstructured_content": "\n".join(text_parts)}
        except: return {}

# Initialize Gemini Model with Tools
model = genai.GenerativeModel(
    model_name='models/gemini-3.1-flash-lite-preview',
    tools=[
        list_tents, search_tents, get_tent_by_id, get_tent_stats, 
        update_tent_fields, bulk_update_tents, delete_tent_by_id, add_tent,
        list_notion_tents, get_notion_tent_detail, add_notion_tent_to_db,
        sync_all_from_notion, validate_ui_proposals
    ]
)


# チャットの履歴保存機能は完全に削除（常に初期状態から開始）
@app.post("/api/chat")
async def chat_with_agent(
    message: str = Body(..., embed=True),
    session_id: str = Body("default", embed=True),
    history: List[Dict[str, Any]] = Body([], embed=True),
    mode: str = Body("management", embed=True)
):
    # モードに応じたシステムプロンプトとモデル（ツールセット）の設定
    if mode == "assistant":
        system_message = (
            "あなたは親切で博識なキャンプ用品コンシェルジュです。\n"
            "テントデータベースの管理だけでなく、キャンプ全般の知識やWEB上の最新情報（価格、レビュー、トレンド）を提供します。\n"
            "\n"
            "【相談モードのルール】\n"
            "1. **丁寧な対話**: ユーザーの質問に対して、専門的かつ親しみやすい口調で回答してください。\n"
            "2. **WEB検索の活用**: 最新の価格情報や、DBにないテントの詳細については積極的にGoogle検索（ツール）を使用してください。\n"
            "3. **DB操作も可能**: 引き続き、DB内のテント情報を調べたり、修正を提案したりすることも可能です。\n"
            "4. **至れり尽くせりな提案**: 「このテントを買うなら、こちらのタープもおすすめですよ」といった先回りした提案を歓迎します。"
        )
        # 相談モード時はGoogle検索ツールを追加
        current_tools = [
            list_tents, search_tents, get_tent_by_id, get_tent_stats, 
            update_tent_fields, bulk_update_tents, delete_tent_by_id, add_tent,
            list_notion_tents, get_notion_tent_detail, add_notion_tent_to_db,
            sync_all_from_notion, validate_ui_proposals,
            {"google_search_retrieval": {}} # WEB検索機能を有効化
        ]
        active_model = genai.GenerativeModel(
            model_name='models/gemini-3.1-flash-lite-preview',
            tools=current_tools
        )
    else:
        system_message = (
            "あなたは優秀なテントDB管理エージェントです。\n"
            "Notion上の非構造化データ（平文）から情報を読み取り、SupabaseのDBを補完する役割を担います。\n"
            "\n"
            "【基本動作ルール】\n"
            "1. **個別指示の尊重**: ユーザーから「〇〇の項目だけ入力して」と指示された場合、Notionのテキストに他の情報があっても、無視して指定された項目のみを提案してください。\n"
            "2. **Notionの読み解き**: Notionには「購入日 2024/01/01」のような直接的な記述のほか、「去年の夏に買った」などの曖昧な記述もあります。これらを文脈から判断し、可能な限り正確な値を導き出してください。\n"
            "3. **UI提案（ドラフト形式）**: 変更は必ず `update_tent_fields` などのツールを使い、画面上への反映（赤字表示）として提案してください。直接DBを書き換えることはしません。\n"
            "4. **根拠の提示**: データを抽出した際は「Notionの本文に〇〇という記述があったため、購入日を××と判断しました」と根拠を添えてください。\n"
            "5. **勝手な一括同期の禁止**: ユーザーが明示的に求めていない限り、全件の自動同期は行わないでください。"
        )
        # 管理モード用モデルを定義
        active_model = genai.GenerativeModel(
            model_name='models/gemini-3.1-flash-lite-preview',
            tools=[
                list_tents, search_tents, get_tent_by_id, get_tent_stats, 
                update_tent_fields, bulk_update_tents, delete_tent_by_id, add_tent,
                list_notion_tents, get_notion_tent_detail, add_notion_tent_to_db,
                sync_all_from_notion, validate_ui_proposals
            ]
        )

    print(f"[DEBUG] Chat request from session {session_id}, history length: {len(history)}")
    try:
        # 履歴を構築 (構造化された履歴を復元)
        formatted_history = []
        if not history:
            formatted_history.append({"role": "user", "parts": [system_message]})
            formatted_history.append({"role": "model", "parts": ["了解しました。DBの整理と最適な提案を自由に行います。"]})
        else:
            # フロントエンドから送られてきた詳細な履歴（text, function_call, function_responseを含む）を復元
            for h in history:
                parts = []
                for p in h.get("parts", []):
                    if "text" in p:
                        parts.append(p["text"])
                    elif "function_call" in p:
                        # Convert dict to FunctionCallPart
                        fc = p["function_call"]
                        parts.append(genai.types.FunctionCallPart(name=fc["name"], args=fc["args"]))
                    elif "function_response" in p:
                        # Convert dict to FunctionResponsePart
                        fr = p["function_response"]
                        parts.append(genai.types.FunctionResponsePart(name=fr["name"], response=fr["response"]))
                
                if parts:
                    formatted_history.append({"role": h["role"], "parts": parts})

        chat = active_model.start_chat(
            history=formatted_history,
            enable_automatic_function_calling=True
        )
        
        # Retry logic for transient AI API errors (500, 503)
        max_retries = 3
        retry_delay = 2 # seconds
        response = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = chat.send_message(message)
                break # Success
            except Exception as e:
                last_error = e
                # Check for 500 or 503 internal errors
                error_str = str(e).lower()
                if "500" in error_str or "503" in error_str or "internal" in error_str:
                    print(f"[WARNING] AI API transient error (attempt {attempt+1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                raise e # Persistent or non-retryable error
        
        if not response:
            raise last_error
        
        # Collect response text
        full_response_text = response.text
        
        # Collect ALL tool execution results (the [UI_PROPOSAL] tags) from history
        history = chat.history
        found_tags = []
        for entry in history:
            if hasattr(entry, 'parts'):
                for part in entry.parts:
                    if hasattr(part, 'function_response') and part.function_response:
                        val = part.function_response.response.get('result')
                        if val and isinstance(val, str) and ('[UI_' in val):
                            # Extract tags (one or many) from the tool result
                            for line in val.splitlines():
                                if '[UI_' in line:
                                    tag = line.strip()
                                    if tag not in found_tags:
                                        found_tags.append(tag)
        
        # Append found tags to response text if not already present
        for tag in found_tags:
            if tag not in full_response_text:
                full_response_text += "\n" + tag

        # Get the UPDATED history to send back to frontend
        # Serialize to JSON-friendly format
        updated_history = []
        for c in chat.history:
            parts = []
            for p in c.parts:
                if p.text:
                    parts.append({"text": p.text})
                elif p.function_call:
                    parts.append({"function_call": {"name": p.function_call.name, "args": dict(p.function_call.args)}})
                elif p.function_response:
                    parts.append({"function_response": {"name": p.function_response.name, "response": p.function_response.response}})
            updated_history.append({"role": c.role, "parts": parts})

        return {
            "response": full_response_text,
            "history": updated_history
        }

    except Exception as e:
        err_msg = f"Chat interaction failed: {str(e)}"
        print(f"[ERROR] {err_msg}")
        traceback.print_exc()
        
        # エラーハンドリング（履歴機能は削除されたため、単純にエラーを返すのみ）
        raise HTTPException(status_code=500, detail=str(e))

# Existing CRUD Endpoints
@app.get("/tents", response_model=List[schemas.Tent])
def read_tents(skip: int = 0, db: Session = Depends(database.get_db)):
    try:
        print(f"[DEBUG] Fetching tents from database. URL: {database.SQLALCHEMY_DATABASE_URL}")
        tents = db.query(models.Tent).offset(skip).all()
        print(f"[DEBUG] Found {len(tents)} tents.")
        return tents
    except Exception as e:
        print(f"[ERROR] Failed to fetch tents: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tents/stats", response_model=schemas.TentAggregates)
def get_stats_endpoint(db: Session = Depends(database.get_db)):
    return get_tent_stats()

@app.get("/tents/{tent_id}", response_model=schemas.Tent)
def read_tent(tent_id: int, db: Session = Depends(database.get_db)):
    db_tent = db.query(models.Tent).filter(models.Tent.id == tent_id).first()
    if db_tent is None:
        raise HTTPException(status_code=404, detail="Tent not found")
    return db_tent

@app.put("/tents/{tent_id}", response_model=schemas.Tent)
def update_tent(tent_id: int, tent: schemas.TentUpdate, db: Session = Depends(database.get_db)):
    db_tent = db.query(models.Tent).filter(models.Tent.id == tent_id).first()
    if db_tent is None:
        raise HTTPException(status_code=404, detail="Tent not found")
    update_data = tent.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_tent, key, value)
    db.commit()
    db.refresh(db_tent)
    return db_tent

@app.post("/tents/batch")
def batch_update_tents(updates: Dict[int, Dict[str, Any]], db: Session = Depends(database.get_db)):
    """
    一括で複数のテント情報を更新します。
    """
    updated_count = 0
    for tent_id_str, fields in updates.items():
        try:
            tent_id = int(tent_id_str)
            db_tent = db.query(models.Tent).filter(models.Tent.id == tent_id).first()
            if db_tent:
                for key, value in fields.items():
                    setattr(db_tent, key, value)
                updated_count += 1
        except ValueError:
            continue
    db.commit()
    return {"status": "success", "updated_count": updated_count}

# Serve Frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")
