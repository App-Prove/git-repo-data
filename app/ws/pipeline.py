"""
This file contains the code for the websocket endpoint.
The websocket endpoint is used to create a websocket connection between the client and the server.
The goal is to update the client frontend based on websocket messages created by events on the server.
"""

import json
from pathlib import Path
from fastapi import APIRouter, WebSocket, Depends
from fastapi.responses import HTMLResponse

from utils import analysis
from utils.databases import store_data_in_db

from dependencies import get_token_header
import logging

logger = logging.getLogger(__name__)

CLONE_DIR: Path = "cloned_repo"
DB_NAME: str = "file_data.db"

router = APIRouter(
    prefix="/repositories",
    tags=["repositories"],
    # dependencies=[Depends(get_token_header)],
    # responses={404: {"description": "Not found"}},
)


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send me</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
              var ws = new WebSocket("ws://localhost:8000/repositories/ws/repository_url");
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                };
                function sendMessage(event) {
                    var input = document.getElementById("messageText")
                    ws.send(input.value)
                    input.value = ''
                    event.preventDefault()
                }

        </script>
    </body>
</html>
"""


@router.get("/")
async def get():
    return HTMLResponse(html)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


@router.websocket("/ws/repository_url")
async def ws_repository_analysis(websocket: WebSocket):
    """
    Websocket endpoint for analysing a repository.
    Submit data in realtime to the client, in order to update frontend.
    """
    await websocket.accept()
    # We should create a queue and start processes in threads to avoid blocking the event loop
    while True:
        repository_url = await websocket.receive_text()
        await websocket.send_text(f"Connected to repository: {repository_url}")

        # Step 1: Clone the repository
        await websocket.send_text(f"Cloning repository: {repository_url}")
        analysis.clone_repo(repository_url, CLONE_DIR)
        # Step 2: Process the repository to count files, lines, identify main languages
        simple_repo_analysis = analysis.get_simple_repository_analysis(CLONE_DIR)
        (
            number_of_files,
            total_line_count,
            list_of_programming_languages,
            ready_for_analysis,
        ) = simple_repo_analysis

        logger.debug(f"Number of files : {number_of_files}")
        logger.debug(f"Total line count : {total_line_count}")
        logger.debug(f"Most common programming languages : {list_of_programming_languages}")
        # > Send data to the client
        await websocket.send_json(
            {
                "number_of_files": number_of_files,
                "total_line_count": total_line_count,
                "most_common_programming_languages": list_of_programming_languages,
            }
        )

        await websocket.send_text(str(ready_for_analysis))
        # Step 3: Identify sensitive code (filter unnecessary files with AI)
        relevent_files = analysis.get_relevent_files(ready_for_analysis)
        await websocket.send_text(str(relevent_files))

        logger.debug(f"Files identified as relevent : {relevent_files}")

        # Step 4: Identify changes in the code (check for security issues with AI, and suggest first solutions)
        in_depth_file_analysis = analysis.get_in_depth_file_analysis(json.loads(relevent_files).get("sensitive_files"))
        await websocket.send_text(str(in_depth_file_analysis))

        logger.debug(f"Changes in code : {in_depth_file_analysis}")

        # Step 3: Store the data in a SQLite database
        # store_data_in_db(
        #     DB_NAME, {"file_path": str(repository_url), "line_count": total_line_count}
        # )

        # logger.info(f"Processed {len(data)} files, representing {total_line_count} lines. Data stored in {db_name}.")
