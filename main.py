import os
import sqlite3
import chardet
from git import Repo
from fastapi import FastAPI, BackgroundTasks
import uvicorn
from pathlib import Path
from analysis.files_analyser import get_important_extensions,get_file_analysis
from typing import Tuple,List

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

#url: str = os.environ.get("SUPABASE_URL")
#key: str = os.environ.get("SUPABASE_KEY")
#supabase: Client = create_client(url, key)

app = FastAPI()

def clone_repo(repo_url, clone_dir):
    if not os.path.exists(clone_dir):
        os.makedirs(clone_dir)
    # Remove all files in the directory
    for root, dirs, files in os.walk(clone_dir, topdown=False, followlinks=True):
        for file in files:
            logger.info(f"Removing file {file}")
            os.remove(os.path.join(root, file))
        for dir in dirs:
            print(f"Removing dir /{dir}")
            os.rmdir(os.path.join(root, dir))
    # Clone the repository
    Repo.clone_from(repo_url, clone_dir)


def process_repo(clone_dir : str | Path) -> Tuple[List[str],int]:
    
    if type(clone_dir) == str:
        clone_dir = Path(clone_dir)
    list_files = list(clone_dir.rglob("*.*"))

    selected_extensions,_project_type = get_important_extensions(list_files)
    selected_files = filter(lambda x : x.suffix in selected_extensions,list_files)
    list_response = []
    total_line_count = 0
    for response,line_count in get_file_analysis(selected_files):
        try:
            list_response.append(response.choices[0].message.content)
            total_line_count += line_count
        except:
            pass
    return list_response,total_line_count

def store_data_in_db(db_name, data):
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

def main(git_url: str):
    clone_dir = "cloned_repo"
    db_name = "file_data.db"
    # Step 1: Clone the repository
    clone_repo(git_url, clone_dir)
    # Step 2: Process the repository to count files and lines
    data,total_line_count = process_repo(clone_dir)
    # Step 3: Store the data in a SQLite database
    store_data_in_db(db_name, data)

    logger.info(f"Processed {len(data)} files, representing {total_line_count} lines. Data stored in {db_name}.")
    return data

@app.get("/")
def read_root(git_url: str, background_tasks: BackgroundTasks):
    logger.info("Processing repository...")
    background_tasks.add_task(main, git_url)
    return {"message": "Processing repository in the background"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")
