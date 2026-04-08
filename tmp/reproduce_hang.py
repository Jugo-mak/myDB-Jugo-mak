import httpx
import json
import sys

# UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

url = "http://localhost:8002/api/chat"
payload = {
    "message": "NotionからID65のテントの名前だけ見せて",
    "session_id": "debug_hang_session",
    "history": []
}

try:
    print(f"Sending request to {url}...")
    # Use a long timeout to see if it eventually finishes or just hangs
    response = httpx.post(url, json=payload, timeout=60.0)
    
    if response.status_code == 200:
        print("\n--- AI Response ---")
        print(response.json().get("response"))
        print("\n-------------------")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"Exception: {str(e)}")
