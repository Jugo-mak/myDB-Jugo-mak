import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
print(f"Testing API Key: {api_key[:10]}...")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')

try:
    response = model.generate_content("Hi, are you working?")
    print("Success!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
