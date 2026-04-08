import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    print("Error: DATABASE_URL not found in .env")
    exit(1)

print(f"Connecting to: {url.split('@')[-1]}") # Use only hostname for safety

try:
    engine = create_engine(url)
    with engine.connect() as conn:
        print("Successfully connected to Supabase.")
        
        # テーブルの内容を5件取得してみる
        res = conn.execute(text("SELECT id, name, brand, purchase_date FROM tents LIMIT 5")).fetchall()
        
        if not res:
            print("The 'tents' table exists but is currently empty.")
        else:
            print(f"Found {len(res)} rows in 'tents' table:")
            for row in res:
                print(f" - ID: {row[0]}, Name: {row[1]}, Brand: {row[2]}, Purchase Date: {row[3]}")
                
except Exception as e:
    print(f"FAILED to connect: {str(e)}")
