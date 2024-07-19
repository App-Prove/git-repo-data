import os
import sqlite3
import logging
from supabase import Client, create_client

logger = logging.getLogger(__name__)

url: str = os.environ.get("SUPABASE_URL",'')
key: str = os.environ.get("SUPABASE_KEY",'')

assert url != '', "No SUPABASE_URL detected"
assert key != '', "No SUPABASE_KEY detected"

supabase: Client = create_client(url, key)


def store_data_in_sqlite_db(db_name: str, data: dict):
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


# Function to store data in a supabase database
def store_data_in_db(*, url: str, files_count: int, lines_count: int):
    logger.error(f"Storing data in database: {url}, {files_count}, {lines_count}")
    response = (
        supabase.table("offers")
        .update({"files_count": files_count, "lines_count": lines_count})
        .eq("url", url)
        .execute()
    )
    logger.error(f"Response from database: {response}")