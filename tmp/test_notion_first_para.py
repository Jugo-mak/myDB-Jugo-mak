import os
import httpx
from dotenv import load_dotenv
import sys

# Ensure stdout uses UTF-8 to prevent mangling in some environments
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Load .env
load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_API_VERSION = "2022-06-28"

SAMPLE_PAGE_ID = "2489fa68-e7ac-800e-873e-c05c01397bfd"

def get_first_paragraph(page_id):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_API_VERSION
    }

    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    
    try:
        with httpx.Client() as client:
            res = client.get(blocks_url, headers=headers)
            if res.status_code == 200:
                results = res.json().get("results", [])
                paragraphs = [b for b in results if b["type"] == "paragraph"]
                
                if paragraphs:
                    b = paragraphs[0]
                    rich_text = b.get("paragraph", {}).get("rich_text", [])
                    text = "".join(t.get("plain_text", "") for t in rich_text)
                    print(f"--- First Paragraph of '{page_id}' ---")
                    print(text)
                else:
                    print("No paragraphs found.")
            else:
                print(f"Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    get_first_paragraph(SAMPLE_PAGE_ID)
