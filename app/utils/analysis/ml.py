import os
import logging
from openai import OpenAI
from typing import List


logger = logging.getLogger(__name__)


class ChatGPTApi:
    """Class that is used to call chatgpt, you need to have your openai API key as an environemnt variable named OPENAI_API_KEY"""

    def __init__(self) -> None:
        assert (
            os.getenv("OPENAI_API_KEY") is not None
        ), "No API key detected, please setup your API key as an environement variable under the name OPENAI_API_KEY"
        self.client = OpenAI()

    def call(self, *, message):
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "json_object"},
            messages=message,
        )
        logger.debug(response)
        return response.choices[0].message.content

    def identify_sensitive_files(self, files: List[dict]):
        """Identify sensitive files using GPT"""

        message = [
            {
                "role": "system",
                "content": (
                    f"You will be provided with a list of files paths"
                    "Your task is to identify which files are most likely to contain sensitive code, base your expectations on the path of the file."
                    "Output is formatted as JSON with key sensitiveFiles containing a list of objects with keys:"
                    "path, which is the path of the file containing sensitive code"
                    "language, which is the programming language of the file"
                    "understand that a main file is a file that is likely to contain the main logic of the application"
                    "those types of files are usually the most sensitive ones."
                ),
            },
            {
                "role": "user",
                "content": "[{'path': 'cloned_repo/main.py', 'language': 'Python'}]",
            },
            {
                "role": "assistant",
                "content": '{ "sensitiveFiles": [ { "path": "cloned_repo/main.py", "language": "Python" } ] }',
            },
            {
                "role": "user",
                "content": str(files),
            },
        ]
        return self.call(message=message)

    def in_depth_analysis(self, code: str, language: str = "python"):
        """Analyse code in depth using GPT"""
        if code is None or code == "":
            return None
        message = [
            {
                "role": "system",
                "content": (
                    f"You will be provided with a piece of {language} code"
                    "Your task is to check code security."
                    "If you find a possible security issue, you should provide a comment and a code suggestion to fix the issue (it must be code replacing existing one). "
                    "Output is formatted as JSON with key issues containing a list of objects with keys:"
                    "lineNumber, which is starting line where the issue occurs"
                    "comment, which is a short description of the issue"
                    "suggestion, which is a possible solution to the issue"
                    "each entry of the list corresponds to a different issue in the code."
                ),
            },
            # {
            #     "role": "user",
            #     "content": (
            #         "1. import os\n"
            #         "2. import sqlite3\n"
            #         "3. import chardet\n"
            #         "4. from git import Repo\n"
            #         "5. from fastapi import FastAPI, BackgroundTasks\n"
            #         "6. import uvicorn\n"
            #         "7. from supabase import create_client, Client\n"
            #         "8. from dotenv import load_dotenv\n"
            #         "9. \n"
            #         "10. load_dotenv()\n"
            #         '11. url: str = os.environ.get("SUPABASE_URL")\n'
            #         '12. key: str = os.environ.get("SUPABASE_KEY")\n'
            #         "13. supabase: Client = create_client(url, key)\n"
            #         "14. \n"
            #         "15. # Create a FastAPI app\n"
            #         "16. app = FastAPI()\n"
            #         "17. \n"
            #         "18. # Function to clone a Git repository\n"
            #         "19. def clone_repo(repo_url, clone_dir):\n"
            #         "20.     if not os.path.exists(clone_dir):\n"
            #         "21.         os.makedirs(clone_dir)\n"
            #         "22.     # Remove all files in the directory\n"
            #         "23.     for root, dirs, files in os.walk(clone_dir, topdown=False, followlinks=True):\n"
            #         "24.         for file in files:\n"
            #         '25.             print(f"Removing file {file}")\n'
            #         "26.             os.remove(os.path.join(root, file))\n"
            #         "27.         for dir in dirs:\n"
            #         "28. \n"
            #         '29.             print(f"Removing dir /{dir}")\n'
            #         "30.             os.rmdir(os.path.join(root, dir))\n"
            #         "31.     # Clone the repository\n"
            #         '32.     Repo.clone_from(f"https://github.com/{repo_url}", clone_dir)\n'
            #         "33. \n"
            #         "34. # Function to count lines in a file\n"
            #         "35. def count_lines(file_path):\n"
            #         "36.     try:\n"
            #         '37.         with open(file_path, "rb") as file:\n'
            #         "38.             #TODO: Call GPT to identify not handled errors\n"
            #         "39.             raw_data = file.read()\n"
            #         "40.             result = chardet.detect(raw_data)\n"
            #         '41.             encoding = result["encoding"]\n'
            #         "42.             text = raw_data.decode(str(encoding))\n"
            #         "43.             lines = text.splitlines()\n"
            #         "44.             return len(lines)\n"
            #         "45.     except Exception as e:\n"
            #         '46.         print(f"Error reading {file_path}: {e}")\n'
            #         "47.         return 0\n"
            #         "48. \n"
            #         "49. # Function to process the repository and collect data\n"
            #         "50. def process_repo(clone_dir):\n"
            #         "51.     data = []\n"
            #         "52.     for root, _, files in os.walk(clone_dir):\n"
            #         "53.         # files_paths = [os.path.join(root, file) for file in files]\n"
            #         "54.         # identify_project_type(files_paths)\n"
            #         "55.         #TODO: Project: Python\n"
            #         "56.         #TODO: Important extension: .py\n"
            #         "57.         #TODO: Analysis of .py files\n"
            #         "58.         #TODO: File sensible: main.py\n"
            #         "59.         for file in files:\n"
            #         "60.             file_path = os.path.join(root, file)\n"
            #         "61.             if ('.git' in file_path):\n"
            #         "62.                 continue\n"
            #         "63.             line_count = count_lines(file_path)\n"
            #         "64.             data.append((file_path, line_count))\n"
            #         "65.     return data\n"
            #         "66. \n"
            #         "67. # Function to store data in a SQLite database\n"
            #         "68. def store_data_in_db(*,url:str,files_count: int,lines_count: int):  \n"
            #         "69.     response = (\n"
            #         '70.     supabase.table("offers")\n'
            #         '71.     .update({"files_count": files_count, "lines_count": lines_count})\n'
            #         '72.     .eq("url", url)\n'
            #         "73.     .execute()\n"
            #         "74. )\n"
            #         "75.     print(response)\n"
            #         "76. \n"
            #         "77. # Main function\n"
            #         "78. def main(git_url: str):\n"
            #         '79.     clone_dir = "cloned_repo"\n'
            #         '80.     db_name = "file_data.db"\n'
            #         "81. \n"
            #         "82.     # Step 1: Clone the repository\n"
            #         "83.     clone_repo(git_url, clone_dir)\n"
            #         "84. \n"
            #         "85.     # Step 2: Process the repository to count files and lines\n"
            #         "86.     data = process_repo(clone_dir)\n"
            #         "87.     lines_count = 0\n"
            #         "88.     for file in data:\n"
            #         "89.         lines_count += file[1]\n"
            #         "90.     files_count = len(data)\n"
            #         "91.     # Step 3: Store the data in a SQLite database\n"
            #         "92.     store_data_in_db(url=git_url,files_count=files_count,lines_count=lines_count)\n"
            #         "93. \n"
            #         '94.     print(f"Processed {len(data)} files, representing {lines_count} lines. Data stored in {db_name}.")\n'
            #         "95.     return data\n96. \n"
            #         '97. @app.get("/")\n'
            #         "98. def read_root(git_url: str, background_tasks: BackgroundTasks):\n"
            #         '99.     print("Processing repository...")\n'
            #         "100.     background_tasks.add_task(main, git_url)\n"
            #         '101.     return {"message": "Processing repository in the background"}\n'
            #         "102. \n"
            #         '103. if __name__ == "__main__":\n'
            #         '104.     uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")',
            #     ),
            # },
            # {
            #     "role": "assistant",
            #     "content": (
            #         '{'
            #         '    "issues": ['
            #                 '{'
            #                 '    "line_number": 21,'
            #                     '"comment": "Using os.makedirs to create directories insecurely",'
            #                     '"suggestion": "Use os.makedirs with exist_ok=True to safely create directories"'
            #                 '},'
            #                 '{'
            #                     '"line_number": 31,'
            #                     '"comment": "Using os.rmdir to remove directories insecurely",'
            #                     '"suggestion": "Use shutil.rmtree to safely remove directories"'
            #                 '},'
            #             ']'
            #         '}'
            #     )
            # },
            {
                "role": "user",
                "content": code,
            },
        ]
        return self.call(message=message)
