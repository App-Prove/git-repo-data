import os
import sqlite3
import chardet
from git import Repo
from fastapi import FastAPI, BackgroundTasks
import uvicorn
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Create a FastAPI app
app = FastAPI()

# Function to clone a Git repository
def clone_repo(repo_url, clone_dir):
    if not os.path.exists(clone_dir):
        os.makedirs(clone_dir)
    # Remove all files in the directory
    for root, dirs, files in os.walk(clone_dir, topdown=False, followlinks=True):
        for file in files:
            print(f"Removing file {file}")
            os.remove(os.path.join(root, file))
        for dir in dirs:

            print(f"Removing dir /{dir}")
            os.rmdir(os.path.join(root, dir))
    # Clone the repository
    Repo.clone_from(f"https://github.com/{repo_url}", clone_dir)

# Function to count lines in a file
def count_lines(file_path):
    try:
        with open(file_path, "rb") as file:
            #TODO: Call GPT to identify not handled errors
            raw_data = file.read()
            result = chardet.detect(raw_data)
            encoding = result["encoding"]
            text = raw_data.decode(str(encoding))
            lines = text.splitlines()
            return len(lines)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

# Function to process the repository and collect data
def process_repo(clone_dir):
    data = []
    for root, _, files in os.walk(clone_dir):
        # files_paths = [os.path.join(root, file) for file in files]
        # identify_project_type(files_paths)
        #TODO: Project: Python
        #TODO: Important extension: .py
        #TODO: Analysis of .py files
        #TODO: File sensible: main.py
        for file in files:
            file_path = os.path.join(root, file)
            if ('.git' in file_path):
                continue
            line_count = count_lines(file_path)
            data.append((file_path, line_count))
    return data

# Function to store data in a SQLite database
def store_data_in_db(*,url:str,files_count: int,lines_count: int):  
    response = (
    supabase.table("offers")
    .update({"files_count": files_count, "lines_count": lines_count})
    .eq("url", url)
    .execute()
)
    print(response)

# Main function
def main(git_url: str):
    clone_dir = "cloned_repo"
    db_name = "file_data.db"

    # Step 1: Clone the repository
    clone_repo(git_url, clone_dir)

    # Step 2: Process the repository to count files and lines
    data = process_repo(clone_dir)
    lines_count = 0
    for file in data:
        lines_count += file[1]
    files_count = len(data)
    # Step 3: Store the data in a SQLite database
    store_data_in_db(url=git_url,files_count=files_count,lines_count=lines_count)

    print(f"Processed {len(data)} files, representing {lines_count} lines. Data stored in {db_name}.")
    return data

@app.get("/")
def read_root(git_url: str, background_tasks: BackgroundTasks):
    print("Processing repository...")
    background_tasks.add_task(main, git_url)
    return {"message": "Processing repository in the background"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")