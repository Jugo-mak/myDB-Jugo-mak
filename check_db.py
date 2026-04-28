import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
engine = create_engine(url)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name, brand FROM tents LIMIT 3"))
        rows = result.fetchall()
        if not rows:
            print("No data found in 'tents' table.")
        for row in rows:
            print(f"ID: {row[0]}, Name: {row[1]}, Brand: {row[2]}")
except Exception as e:
    print(f"Error reading table: {e}")
