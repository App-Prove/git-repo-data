import os
import sqlite3

from supabase import Client, create_client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

assert url is not None, "No SUPABASE_URL detected"
assert key is not None, "No SUPABASE_KEY detected"

supabase: Client = create_client(url, key)


def store_data_in_db(db_name: str, data: dict):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS file_data
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       file_path TEXT, 
                       line_count INTEGER)"""
    )

    cursor.executemany(
        "INSERT INTO file_data (file_path, line_count) VALUES (?, ?)", data
    )
    conn.commit()
    conn.close()
