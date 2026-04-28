import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
print(f"Testing connection to: {url}")

try:
    engine = create_engine(url)
    with engine.connect() as conn:
        print("Successfully connected!")
except Exception as e:
    print(f"Connection failed: {e}")
