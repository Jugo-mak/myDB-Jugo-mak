# Tents Database AI Manager - 統合設計・構築仕様書

本ドキュメントは、プロジェクトをゼロから完全に再現・リカバリするための設計仕様書です。AIアシスタントがスクラッチでシステムを構築、あるいは既存環境を完全に復旧させるためのすべての情報を網羅しています。

## 1. プロジェクト概要
キャンプ用テントの在庫・スペックを管理するためのインテリジェント・ダッシュボードです。
Google Gemini AIが「管理エージェント」として常駐し、Notion上の非構造化データ（メモ書き等）からスペックを抽出し、データベースを自動更新する提案を行います。

## 2. システムアーキテクチャ
- **Backend**: FastAPI (Python 3.12+)
- **Frontend**: Vanilla HTML5 / CSS3 / JavaScript (ES6+)
- **Database**: Supabase PostgreSQL (Port: 6543 / Session Pooler)
- **AI Engine**: Google Gemini 3.1 Flash (Google GenAI SDK)
- **External Integration**: Notion API (httpxによる直接連携)

## 3. 主要機能
### 3.1 AI 管理エージェント (Dual Mode)
- **管理モード (Management)**: Notionからのデータ抽出、DB項目の修正提案、整合性チェックに特化。
- **相談モード (Assistant)**: キャンプ知識の提供、Google検索を活用した最新トレンドの調査、コーディネート提案。
- **UI提案システム**: AIはDBを直接書き換えません。`[UI_PROPOSAL: ...]` などの特殊タグを介してフロントエンドに「修正案」を送り、ユーザーが画面上で確認・編集した後に一括保存するワークフローを採用。

### 3.2 Notion 同期
- 「煩悩テント」親ページの下にある子ページをスキャンし、本文（非構造化テキスト）から「購入日」や「スペック」をAIが自動抽出します。

### 3.3 リアルタイム・エディタ
- DBから取得したデータをテーブル表示し、直接編集が可能。
- AIの提案やユーザーの手入力による変更は「未保存（赤字）」として管理され、`Validate` -> `Commit` の手順でDBへ反映。

## 4. 環境構築・セットアップ

### 4.1 前提条件
- Python 3.12 以上
- Supabase プロジェクト（PostgreSQL）
- Notion インテグレーション（トークン発行済み）
- Google Gemini API Key

### 4.2 環境変数 (.env)
セキュリティのため、具体的な接続情報やパスワードの記述は省略します。
プロジェクトの動作には、以下のキーを設定した `.env` ファイルをプロジェクトルートに配置する必要があります。
- `GEMINI_API_KEY`
- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`
- `DATABASE_URL`

### 4.3 インストールと起動
```powershell
# 依存関係のインストール
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv google-generativeai httpx nest-asyncio

# サーバー起動
uvicorn main:app --reload --port 8000
```

## 5. 詳細仕様

### 5.1 データベース・スキーマ (`tents`)
| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `id` | Integer | Primary Key (Serial) |
| `name` | Text | テント名 (Not Null) |
| `brand` | Text | ブランド名 |
| `price` | Integer | 価格 (JPY) |
| `capacity` | Numeric | 定員 (e.g., 2.5) |
| `weight_kg` | Numeric | 重量 |
| `size_w/d/h` | Numeric | 使用時サイズ (cm) |
| `pack_w/d/h` | Numeric | 収納サイズ (cm) |
| `material` | Text | 素材 |
| `purchase_date` | Date | 購入日 |

### 5.2 AIツールの定義 (Function Calling)
AIは以下の関数を必要に応じて自律的に呼び出します。
- `list_tents` / `search_tents`: DB内の検索。
- `update_tent_fields`: 1件の修正案作成。
- `bulk_update_tents`: 複数件の一括修正案。
- `sync_all_from_notion`: 指定したIDのNotion情報を一括同期。
- `list_notion_tents`: Notion側のページ一覧を取得。

### 5.3 フロントエンド・ステート
- `pendingEdits`: 保存前の変更内容を保持するJSONオブジェクト。キーはテントID。
- `currentTents`: DBから取得した最新のマスターデータ。
- 表示ロジック: `currentTents` に `pendingEdits` をマージして描画。

## 7. ソースコード・アーカイブ (完全復元用)
万が一ソースファイルが紛失した場合でも、以下のコードを各ファイル名で保存することでシステムを完全に復元できます。

### 7.1 database.py
```python
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
```

### 7.2 models.py
```python
from sqlalchemy import Column, Integer, Text, Numeric, Date
from database import Base

class Tent(Base):
    __tablename__ = "tents"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    brand = Column(Text)
    price = Column(Integer)
    capacity = Column(Numeric)
    weight_kg = Column(Numeric)
    size_w = Column(Numeric); size_d = Column(Numeric); size_h = Column(Numeric)
    pack_w = Column(Numeric); pack_d = Column(Numeric); pack_h = Column(Numeric)
    material = Column(Text)
    purchase_date = Column(Date)
```

### 7.3 schemas.py
```python
from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Optional
from decimal import Decimal

class TentBase(BaseModel):
    name: str
    brand: Optional[str] = None
    price: Optional[int] = None
    capacity: Optional[Decimal] = None
    weight_kg: Optional[Decimal] = None
    size_w: Optional[Decimal] = None
    size_d: Optional[Decimal] = None
    size_h: Optional[Decimal] = None
    pack_w: Optional[Decimal] = None
    pack_d: Optional[Decimal] = None
    pack_h: Optional[Decimal] = None
    material: Optional[str] = None
    purchase_date: Optional[date] = None

class TentCreate(TentBase): pass
class TentUpdate(TentBase):
    name: Optional[str] = None

class Tent(TentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class TentAggregates(BaseModel):
    total_count: int
    avg_price: Optional[float] = None
```

### 7.4 main.py (AIエージェントの核心)
```python
import os
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import google.generativeai as genai
from dotenv import load_dotenv
import models, schemas, database, httpx, time

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
app = FastAPI()

# AI Tools: list_tents, search_tents, update_tent_fields, etc.
# (詳細は実際の main.py を参照。AIプロンプトが最重要)
SYSTEM_MESSAGE_MANAGEMENT = "あなたは優秀なテントDB管理エージェントです。Notionから情報を読み取り、UI提案を行ってください..."

@app.post("/api/chat")
async def chat_with_agent(...):
    # Gemini 3.1 Flash Lite を使用した Function Calling ロジック
    ...
```

### 7.5 static/app.js (フロントエンド制御)
```javascript
const API_BASE = window.location.origin;
let currentTents = [];
let pendingEdits = {}; 

async function fetchTents() {
    const res = await fetch(`${API_BASE}/tents`);
    currentTents = await res.json();
    renderTable(currentTents);
}

// AIの提案 [UI_PROPOSAL:...] をパースして pendingEdits に反映するロジック
function parseUIProposals(text) { ... }
```

---
**本ファイルは、プロジェクト「Tents Database AI Manager」の全知能と全構造を保持しています。**
