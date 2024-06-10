import os
import sqlite3
import chardet
from git import Repo
from fastapi import FastAPI, BackgroundTasks
import uvicorn
from supabase import create_client, Client

#url: str = os.environ.get("SUPABASE_URL")
#key: str = os.environ.get("SUPABASE_KEY")
#supabase: Client = create_client(url, key)

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
    Repo.clone_from(repo_url, clone_dir)


# Function to count lines in a file
def count_lines(file_path):
    try:
        with open(file_path, "rb") as file:
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
        for file in files:
            file_path = os.path.join(root, file)
            line_count = count_lines(file_path)
            data.append((file_path, line_count))
    return data


# Function to store data in a SQLite database
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


# Main function
def main(git_url: str):
    clone_dir = "cloned_repo"
    db_name = "file_data.db"

    # Step 1: Clone the repository
    clone_repo(git_url, clone_dir)

    # Step 2: Process the repository to count files and lines
    data = process_repo(clone_dir)

    # Step 3: Store the data in a SQLite database
    store_data_in_db(db_name, data)

    print(f"Processed {len(data)} files. Data stored in {db_name}.")
    return data


@app.get("/")
def read_root(git_url: str, background_tasks: BackgroundTasks):
    print("Processing repository...")
    background_tasks.add_task(main, git_url)
    return {"message": "Processing repository in the background"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
