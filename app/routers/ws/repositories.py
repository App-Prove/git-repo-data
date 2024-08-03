"""
This file contains the code for the websocket endpoint.
The websocket endpoint is used to create a websocket connection between the client and the server.
The goal is to update the client frontend based on websocket messages created by events on the server.
"""

import asyncio
import json
import jwt
import os
from pathlib import Path
from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer

from utils.websocket import WebSocketAPI
from utils.analysis.files_analyser import format_github_url
from utils import analysis
from utils.databases import store_data_in_db

from dependencies import get_token_header
import logging

logger = logging.getLogger(__name__)

CLONE_DIR: Path = Path("cloned_repo")
DB_NAME: str = "file_data.db"

router = APIRouter(
    prefix="/ws/repositories",
    tags=["repositories"],
    # dependencies=[Depends(get_token_header)],
    # responses={404: {"description": "Not found"}},
)
from dotenv import load_dotenv

load_dotenv()
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


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
            var ws = new WebSocket("ws://localhost:8000/ws/repositories/analysis");
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


@router.websocket("/message")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_json({"success": f"Message text was: {data}"})


@router.websocket("/test")
async def ws_testing_endpoint(websocket: WebSocket):
    """
    Websocket endpoint for testing purposes.
    """
    await websocket.accept()
    try:
        for i in range(10):
            message = f"Message {i}"
            await websocket.send_json({"success": message})
            await asyncio.sleep(1)  # Yield control back to the event loop messages
    except WebSocketDisconnect:
        print("Client disconnected")


@router.websocket("/analysis")
async def ws_repository_analysis(websocket: WebSocket):
    """
    Websocket endpoint for analysing a repository.
    Submit data in realtime to the client, in order to update frontend.
    """
    await websocket.accept()
    websocket_api = WebSocketAPI(websocket)
    # We should create a queue and start processes in threads to avoid blocking the event loop
    while True:
        data = await websocket.receive_json()
        await websocket_api.send(
            status="inProgress",
            step_name="connecting",
            message="Connecting to our services",
        )
        try:
            repository_url = data["repositoryURL"]
            audit_type = data["auditType"]
        except KeyError:
            await websocket_api.send(
                status="error",
                step_name="connecting",
                message="You should create an offer first",
            )
            continue
        try:
            token = data["token"]
        except KeyError:
            await websocket_api.send(
                status="error",
                step_name="connecting",
                message="You should authenticate first",
            )
            continue
        # Secure connection using supabase JWT token
        try:
            logger.error(f"Token : {token}" f"JWT_SECRET : {JWT_SECRET}")
            payload = jwt.decode(
                token, JWT_SECRET, algorithms=["HS256"], audience="authenticated"
            )
            logger.debug(f"Decoded payload : {payload}")
            user_id = payload.get("sub")
            # Check user_id correspond to the user who created the offer for selected repo
        except Exception as error:
            await websocket_api.send(
                status="error",
                step_name="connecting",
                message=f"An error has occured while decoding the token : {error}",
            )
            continue

        # If we don't sleep, websocket is too fast and the client can't keep up
        await websocket_api.send(
            status="success",
            step_name="connecting",
            message=f"Service ready for: {repository_url}",
        )

        # Make sure URL is in the right format
        formatted_repository_url = format_github_url(repository_url)

        # Step 1: Clone the repository
        await websocket_api.send(
            status="inProgress",
            step_name="cloning",
            message="Started cloning repository",
        )
        CLONE_DIR = Path(formatted_repository_url.split("/")[-1])
        try:
            analysis.clone_repo(formatted_repository_url, CLONE_DIR)
        except Exception as error:
            await websocket_api.send(
                status="error",
                step_name="cloning",
                message=f"An error has occured while cloning",
            )
            continue
        await websocket_api.send(
            step_name="cloning",
            status="success",
            message=f"Successfully cloned repository",
        )

        await websocket_api.send(
            status="inProgress",
            step_name="identifying",
            message="Started simple repository scan",
        )
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
        logger.debug(
            f"Most common programming languages : {list_of_programming_languages}"
        )
        await websocket_api.send(
            step_name="identifying",
            status="inProgress",
            message="Repository scan complete",
            type="repositoryScan",
            data={
                "numberOfFiles": number_of_files,
                "totalLineCount": total_line_count,
                "mostCommonProgrammingLanguages": list_of_programming_languages,
            },
        )

        await websocket_api.send(
            step_name="identifying",
            status="inProgress",
            message="Identified files relatives to project",
            type="relativeFiles",
            data={"relativeFiles": ready_for_analysis},
        )
        

        # Step 3: Identify sensitive code (filter unnecessary files with AI)
        sensitive_files = analysis.get_sensitive_files(ready_for_analysis)
        await websocket_api.send(
            status="success",
            step_name='identifying',
            message="Identified sensitive files for in depth analysis",
            type="sensitiveFiles",
            data=sensitive_files,
        )
        logger.debug(f"Files identified as relevent : {sensitive_files}")

        # Step 4: Identify changes in the code (check for security issues with AI, and suggest first solutions)
        in_depth_file_analysis = analysis.get_in_depth_file_analysis(
            list_files=sensitive_files.get("sensitiveFiles", []), audit_type=audit_type
        )
        await websocket_api.send(
            step_name="reviewing",
            status="success",
            message="In depth analysis finished",
            type="inDepthAnalysis",
            data=in_depth_file_analysis,
        )

        # Step 5: Store the data in supabase database
        store_data_in_db(
            url=data["repositoryURL"],
            files_count=number_of_files,
            lines_count=total_line_count,
        )

        logger.debug(f"Changes in code : {in_depth_file_analysis}")

        # Remove the cloned repository
        analysis.clean_dir(CLONE_DIR)

        await websocket.close()
        # Step 3: Store the data in a SQLite database
        # store_data_in_db(
        #     DB_NAME, {"file_path": str(repository_url), "line_count": total_line_count}
        # )

        # logger.info(f"Processed {len(data)} files, representing {total_line_count} lines. Data stored in {db_name}.")
        return
