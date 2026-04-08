import os
import httpx
from dotenv import load_dotenv
import sys

# Ensure stdout uses UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_API_VERSION = "2022-06-28"
BONNOU_TENT_PARENT_ID = "10c9fa68-e7ac-809a-8512-eca278b82750"

def find_and_show_detail(target_name):
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_API_VERSION
    }

    print(f"Searching for '{target_name}' in Notion...")
    
    found_page_id = None
    has_more = True
    start_cursor = None
    
    with httpx.Client() as client:
        while has_more:
            url = f"https://api.notion.com/v1/blocks/{BONNOU_TENT_PARENT_ID}/children"
            params = {"start_cursor": start_cursor} if start_cursor else {}
            res = client.get(url, headers=headers, params=params)
            if res.status_code != 200:
                print(f"Error listing: {res.status_code}")
                break
            
            data = res.json()
            for b in data.get("results", []):
                if b["type"] == "child_page":
                    title = b["child_page"].get("title", "")
                    if target_name.lower() in title.lower():
                        found_page_id = b["id"]
                        print(f"Found! ID: {found_page_id}, Title: {title}")
                        break
            
            if found_page_id: break
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

        if not found_page_id:
            print("Page not found.")
            return

        # Now fetch ALL content blocks
        print(f"--- Full Content of '{target_name}' ---")
        blocks_url = f"https://api.notion.com/v1/blocks/{found_page_id}/children"
        res = client.get(blocks_url, headers=headers)
        if res.status_code == 200:
            blocks = res.json().get("results", [])
            for b in blocks:
                btype = b["type"]
                content = b.get(btype, {})
                rich_text = content.get("rich_text", [])
                text = "".join(t.get("plain_text", "") for t in rich_text)
                if text:
                    print(f"[{btype}] {text}")
                elif btype == "image":
                    print("[image] (image)")
        else:
            print(f"Error fetching detail: {res.status_code}")

if __name__ == "__main__":
    find_and_show_detail("PICNICAR Aquila")
