import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def test_model(name):
    print(f"Testing model: {name}")
    try:
        model = genai.GenerativeModel(name)
        response = model.generate_content("hi")
        print(f"  SUCCESS: {response.text[:20]}...")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

print("--- FACT CHECK: QUOTA STATUS ---")
flash_ok = test_model("models/gemini-3.1-flash-lite-preview")
print("--------------------------------")

if flash_ok:
    print("models/gemini-3.1-flash-lite-preview is AVAILABLE.")
else:
    print("models/gemini-3.1-flash-lite-preview seems to be unavailable or erroring.")
