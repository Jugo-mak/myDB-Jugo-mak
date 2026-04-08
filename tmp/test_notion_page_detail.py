import os
import httpx
import json
from dotenv import load_dotenv

# Load .env
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_API_VERSION = "2022-06-28"

# Ogawa TRES page ID from previous run
SAMPLE_PAGE_ID = "2489fa68-e7ac-800e-873e-c05c01397bfd"

def get_page_details(page_id):
    if not NOTION_TOKEN:
        print("Error: NOTION_TOKEN not found in .env")
        return

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_API_VERSION
    }

    print(f"--- Fetching Content for Page ID: {page_id} ---")

    # 1. Fetch Page object itself (Properties)
    page_url = f"https://api.notion.com/v1/pages/{page_id}"
    
    # 2. Fetch Page content (Blocks)
    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    
    try:
        with httpx.Client() as client:
            # Get Page Props
            p_res = client.get(page_url, headers=headers)
            if p_res.status_code == 200:
                p_data = p_res.json()
                # Title property depends on whether it's in a DB or a standalone page
                # For child pages, title is usually in a 'title' property inside 'properties'
                props = p_data.get("properties", {})
                print("Properties Found:", list(props.keys()))
            else:
                print(f"Error fetching page props: {p_res.status_code}")

            # Get Page Content Blocks
            b_res = client.get(blocks_url, headers=headers)
            if b_res.status_code == 200:
                b_data = b_res.json()
                results = b_data.get("results", [])
                print(f"\nFound {len(results)} content blocks:\n")
                
                for b in results:
                    btype = b["type"]
                    content_obj = b.get(btype, {})
                    rich_text = content_obj.get("rich_text", [])
                    text = "".join(t.get("plain_text", "") for t in rich_text)
                    if text.strip():
                        print(f"[{btype}]: {text}")
                    elif btype == "image":
                        print(f"[{btype}]: (image found)")
                    elif btype == "divider":
                        print("---")
            else:
                print(f"Error fetching blocks: {b_res.status_code}")
                
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    get_page_details(SAMPLE_PAGE_ID)
