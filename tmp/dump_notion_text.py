import os
import httpx
import sys
from dotenv import load_dotenv

# 出力をUTF-8に強制（Windows環境での文字化け対策）
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_API_VERSION = "2022-06-28"
SAMPLE_PAGE_ID = "2489fa68-e7ac-800e-873e-c05c01397bfd" # Ogawa TRES

def dump_all_text(page_id):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_API_VERSION
    }
    
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                return

            data = response.json()
            results = data.get("results", [])
            
            full_text = []
            for block in results:
                btype = block["type"]
                # ほとんどのテキストブロックは rich_text を持っている
                content = block.get(btype, {})
                if "rich_text" in content:
                    text = "".join(t.get("plain_text", "") for t in content["rich_text"])
                    if text:
                        full_text.append(text)
                elif btype == "child_page":
                    full_text.append(f"--- Child Page: {content.get('title')} ---")

            print("\n" + "="*50)
            print(f"COMPLETE PLAIN TEXT FROM NOTION (ID: {page_id})")
            print("="*50 + "\n")
            
            final_output = "\n\n".join(full_text)
            print(final_output)
            print("\n" + "="*50)

    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    dump_all_text(SAMPLE_PAGE_ID)
