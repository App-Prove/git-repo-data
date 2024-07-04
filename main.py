import os
import sqlite3
import chardet
from git import Repo
from fastapi import FastAPI, BackgroundTasks
import uvicorn
from pathlib import Path
from analysis.files_analyser import get_important_programming_language,get_file_analysis
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
            logger.debug(f"Removing file {file}")
            os.remove(os.path.join(root, file))
        for dir in dirs:
            logger.debug(f"Removing dir {dir}")
            os.rmdir(os.path.join(root, dir))
    # Clone the repository
    Repo.clone_from(repo_url, clone_dir)


def process_repo(clone_dir : str | Path) -> Tuple[int, int, List[str], List[str]]:
    """Analyse the repository
    
    - Get the list of files
    - Count number of files
    - Count number of lines
    - Identify most common extensions
    - Filter files with selected extensions
    - Analyse each file with GPT to locate sensitive code
    
    returns number_of_files, total_line_count, most_common_programming_languages, code_which_may_throw_error
    """
    if type(clone_dir) == str:
        clone_dir = Path(clone_dir)
    list_files = list(clone_dir.rglob("*.*"))
    number_of_files = len(list_files)

    important_programming_language = get_important_programming_language(list_files)
    list_of_important_extensions = important_programming_language['extension'].to_list()
    list_of_programming_languages = important_programming_language['name'].to_list()
    logger.debug(f"Selected extensions : {list_of_important_extensions}")
    # Filter files with selected extensions
    selected_files = list(filter(lambda x : x.suffix in list_of_important_extensions,list_files))
    # Ensure relevent files are selected using AI
    # selected_files = get_relevent_files(selected_files)
    logger.debug(f"Selected files : {selected_files}")
    # Change list to dict with filepath and programming language as keys
    ready_for_analysis = [{"path":str(file),"language":important_programming_language[important_programming_language['extension'] == file.suffix]['name'].values[0]} for file in selected_files]
    list_response = []
    total_line_count = 0
    for response,line_count in get_file_analysis(ready_for_analysis):
        logger.debug('Analyzing file')
        try:
            list_response.append(response.choices[0].message.content)
            total_line_count += line_count
        except Exception as error:
            logger.error(f"An error has occured line 70 : {error}")
    return number_of_files,total_line_count,list_of_programming_languages,list_response

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
    number_of_files,total_line_count,list_of_programming_languages,list_response = process_repo(clone_dir)
    logger.debug(f"Number of files : {number_of_files}")
    logger.debug(f"Total line count : {total_line_count}")
    logger.debug(f"Most common programming languages : {list_of_programming_languages}")
    logger.debug(f"Code which may throw error : {list_response}")
    # Step 3: Store the data in a SQLite database
    # store_data_in_db(db_name, data)

    # logger.info(f"Processed {len(data)} files, representing {total_line_count} lines. Data stored in {db_name}.")
    return

@app.get("/")
def read_root(git_url: str, background_tasks: BackgroundTasks):
    logger.info("Processing repository...")
    background_tasks.add_task(main, git_url)
    return {"message": "Processing repository in the background"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")
