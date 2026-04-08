import httpx
import json
import sys

# UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

url = "http://localhost:8002/api/chat"
payload = {
    "message": "ID 70のテントについて、Notionから購入日だけ取得して提案してください",
    "session_id": "test_session_granular",
    "history": []
}

try:
    print(f"Sending request to {url}...")
    response = httpx.post(url, json=payload, timeout=30.0)
    
    if response.status_code == 200:
        print("\n--- AI Response ---")
        print(response.json().get("response"))
        print("\n-------------------")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Exception: {str(e)}")
