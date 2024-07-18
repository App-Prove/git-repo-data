import os
from pathlib import Path
import chardet
import logging
from fastapi import FastAPI, BackgroundTasks
import uvicorn
from utils.databases import store_data_in_db
from utils import analysis
from routers import ws
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filename='app.log', filemode='w')
logger = logging.getLogger(__name__)

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ws.repositories.router)


def main(git_url: str):
    clone_dir = Path("cloned_repo")
    # Step 1: Clone the repository
    analysis.clone_repo(git_url, clone_dir)
    # Step 2: Process the repository to count files and lines
    number_of_files,total_line_count,list_of_programming_languages,ready_for_analysis = analysis.get_simple_repository_analysis(clone_dir)
    logger.debug(f"Number of files : {number_of_files}")
    logger.debug(f"Total line count : {total_line_count}")
    logger.debug(f"Most common programming languages : {list_of_programming_languages}")
    logger.debug(f"Code which may throw error : {ready_for_analysis}")

    # Step 3: Store the data in a SQLite database
    store_data_in_db(url=git_url, files_count=number_of_files, lines_count=total_line_count)

    # logger.info(f"Processed {len(data)} files, representing {total_line_count} lines. Data stored in {db_name}.")
    return

@app.get("/")
def read_root(git_url: str, background_tasks: BackgroundTasks):
    logger.info("Processing repository...")
    background_tasks.add_task(main, git_url)
    return {"message": "Processing repository in the background"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info", reload=bool(os.getenv('DEV',False)), reload_excludes=['cloned_repo/*'])
