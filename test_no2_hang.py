# -*- coding: utf-8 -*-
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Import tools directly
import sys
sys.path.append(r'c:\Users\makta\source\myproject\myDB')
from main import list_notion_tents, get_notion_tent_detail, update_tent_fields

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(
    model_name='models/gemini-3.1-flash-lite-preview',
    tools=[list_notion_tents, get_notion_tent_detail, update_tent_fields]
)

chat = model.start_chat(enable_automatic_function_calling=True)

print(">>> RUNNING: NotionからNo.2 のサイズのデータだけ抽出して、インナーは無視")
response = chat.send_message("NotionからNo.2 (PICNICAR Aquila)のサイズのデータ（WxDxHなど）だけ抽出して update_tent_fields で更新して。インナーテントは無視。")

print(">>> FINAL RESPONSE:")
print(response.text)
