import httpx
import json
import sys

# UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

url = "http://localhost:8002/api/chat"
payload = {
    "message": "ID 1, 2, 3の購入日をNotionから抽出してテーブルに入力して",
    "session_id": "test_500_session",
    "history": []
}

try:
    print(f"Sending request to {url}...")
    response = httpx.post(url, json=payload, timeout=120.0)
    
    if response.status_code == 200:
        print("\n--- AI Response ---")
        print(response.json().get("response"))
        print("\n-------------------")
    else:
        print(f"Error Code: {response.status_code}")
        print(f"Error Content: {response.text}")

except Exception as e:
    print(f"Exception: {str(e)}")
