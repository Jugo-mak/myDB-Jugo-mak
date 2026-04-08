import os
import httpx
from dotenv import load_dotenv

# Load .env
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_API_VERSION = "2022-06-28"
# Parent page for tents
BONNOU_TENT_PARENT_ID = "10c9fa68-e7ac-809a-8512-eca278b82750"

def test_notion_connection():
    if not NOTION_TOKEN:
        print("Error: NOTION_TOKEN not found in .env")
        return

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_API_VERSION
    }

    url = f"https://api.notion.com/v1/blocks/{BONNOU_TENT_PARENT_ID}/children"
    
    print(f"Fetching Notion children for block ID: {BONNOU_TENT_PARENT_ID}...")
    
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"Successfully fetched {len(results)} blocks.")
                
                # Check for child pages
                child_pages = [b for b in results if b["type"] == "child_page"]
                print(f"Found {len(child_pages)} child pages.")
                
                for idx, page in enumerate(child_pages):
                    title = page["child_page"].get("title", "Untitled")
                    page_id = page["id"]
                    print(f"[{idx+1}] ID: {page_id}, Title: {title}")
                    
            else:
                print(f"Error: Notion API returned {response.status_code}")
                print(f"Response: {response.text}")
                
    except Exception as e:
        print(f"Exception occurred: {str(e)}")

if __name__ == "__main__":
    test_notion_connection()
