import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model_name = "models/gemini-3.1-flash-lite-preview"
print(f"Testing model: {model_name}")

try:
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("What are your rate limits?")
    print("SUCCESS")
    print(f"Response snippet: {response.text[:100]}...")
except Exception as e:
    print(f"FAILED: {e}")
