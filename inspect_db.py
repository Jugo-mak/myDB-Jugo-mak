import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load .env
load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        # テーブル一覧を取得
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        tables = result.fetchall()
        
        print("--- Tables in Supabase database ---")
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            
            # 各テーブルのカラム情報を取得
            col_result = conn.execute(text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """))
            columns = col_result.fetchall()
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (Nullable: {col[2]})")

except Exception as e:
    print(f"Error: {e}")

