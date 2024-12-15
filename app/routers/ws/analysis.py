"""
This file contains the code for the websocket endpoint.
The websocket endpoint is used to create a websocket connection between the client and the server.
The goal is to update the client frontend based on websocket messages created by events on the server.
"""

import asyncio
import logging
from pathlib import Path
from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from datetime import datetime
from dotenv import load_dotenv

from app import utils

logger = logging.getLogger(__name__)

CLONE_DIR: Path = Path("cloned_repo")
DB_NAME: str = "file_data.db"

router = APIRouter(
    prefix="/ws/analysis",
    tags=["analysis"],
    # dependencies=[Depends(get_token_header)],
    # responses={404: {"description": "Not found"}},
)

load_dotenv()


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
            var ws = new WebSocket("ws://localhost:8000/ws/analysis");
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


class ProgressTracker:
    def __init__(self, total_files: int = 0, batch_size: int = 10):
        self.total_files = total_files
        self.processed_files = 0
        self.batch_size = batch_size
        self.last_sent_percentage = 0

    def should_send_update(self, files_processed: int = 1) -> tuple[bool, int]:
        """Returns (should_send, current_percentage)"""
        self.processed_files += files_processed
        if self.total_files == 0:
            return False, 0

        current_percentage = min(
            100, int((self.processed_files / self.total_files) * 100)
        )
        should_send = (
            self.processed_files % self.batch_size == 0
            or current_percentage >= 100
            or current_percentage - self.last_sent_percentage >= 5
        )

        if should_send:
            self.last_sent_percentage = current_percentage
        return should_send, current_percentage


@router.websocket("/analysis")
async def ws_repository_analysis(websocket: WebSocket):
    """
    Websocket endpoint for analysing a repository.
    """
    await websocket.accept()
    websocket_api = utils.WebSocketAPI(websocket)

    while True:
        data = await websocket.receive_json()

        # Step 1: Connecting
        await websocket_api.send(
            status="inProgress",
            step_name="connecting",
            progress=0,
            message="Connecting to our services",
            time=datetime.now().isoformat(),
        )

        # Validate input data
        try:
            repository_url = data["repositoryURL"]
        except KeyError:
            await websocket_api.send(
                status="error",
                step_name="connecting",
                progress=100,
                message="Missing required data",
                time=datetime.now().isoformat(),
            )
            continue

        # Send success message directly
        await websocket_api.send(
            status="success",
            step_name="connecting",
            progress=100,
            message=f"Service ready for: {repository_url}",
            time=datetime.now().isoformat(),
        )

        # Step 2: Cloning
        await websocket_api.send(
            status="inProgress",
            step_name="cloning",
            message="Started cloning repository",
        )

        formatted_url = utils.format_github_url(repository_url)
        repo_name = (
            formatted_url[2]
            if isinstance(formatted_url, tuple)
            else formatted_url.split("/")[-1]
        )
        CLONE_DIR = Path(repo_name)

        try:
            utils.clone_repo(repository_url, CLONE_DIR)

            # Get initial file count for progress tracking
            total_files = sum(1 for _ in CLONE_DIR.rglob("*") if _.is_file())
            progress_tracker = ProgressTracker(total_files)

            await websocket_api.send(
                status="success",
                step_name="cloning",
                message=f"Successfully cloned repository with {total_files} files",
            )
        except Exception as error:
            await websocket_api.send(
                status="error", step_name="cloning", message=f"Cloning failed: {error}"
            )
            continue

        # Step 3: Identifying
        await websocket_api.send(
            status="inProgress",
            step_name="identifying",
            message="Started repository scan",
        )

        # Repository scan with progress tracking
        files_processed = 0
        programming_languages = {}
        total_line_count = 0
        ready_for_analysis = []
        progress_tracker = ProgressTracker(total_files)

        for file_path in CLONE_DIR.rglob("*"):
            if file_path.is_file():
                try:
                    # Process each file
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.readlines()
                        total_line_count += len(content)

                        # Detect language based on file extension
                        ext = file_path.suffix.lower()
                        if ext in [".py", ".js", ".ts", ".java", ".cpp", ".go", ".rs"]:
                            lang = ext[1:]  # Remove the dot
                            programming_languages[lang] = (
                                programming_languages.get(lang, 0) + 1
                            )
                            ready_for_analysis.append(file_path)

                    files_processed += 1
                    should_send, progress = progress_tracker.should_send_update()

                    if should_send:
                        await websocket_api.send(
                            status="inProgress",
                            step_name="identifying",
                            message=f"Processed {files_processed}/{total_files} files",
                            type="repositoryScan",
                            data={
                                "numberOfFiles": total_files,
                                "totalLineCount": total_line_count,
                                "mostCommonProgrammingLanguages": sorted(
                                    programming_languages.items(),
                                    key=lambda x: x[1],
                                    reverse=True,
                                )[:5],
                            },
                        )
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    continue

        # Final progress update for repository scan
        await websocket_api.send(
            status="inProgress",
            step_name="identifying",
            message="Repository scan complete",
            type="repositoryScan",
            data={
                "numberOfFiles": total_files,
                "totalLineCount": total_line_count,
                "mostCommonProgrammingLanguages": sorted(
                    programming_languages.items(), key=lambda x: x[1], reverse=True
                )[:5],
            },
        )

        # Reset progress tracker for sensitive files analysis
        progress_tracker = ProgressTracker(len(ready_for_analysis))

        # Process sensitive files with progress tracking
        sensitive_files = []
        for file_path in ready_for_analysis:
            is_sensitive = utils.is_sensitive_file(file_path)
            if is_sensitive:
                sensitive_files.append(
                    {
                        "path": str(file_path.relative_to(CLONE_DIR)),
                        "language": file_path.suffix[1:],
                    }
                )

            should_send, progress = progress_tracker.should_send_update()
            if should_send:
                await websocket_api.send(
                    status="inProgress",
                    step_name="identifying",
                    message=f"Analyzing files for sensitivity ({progress}%)",
                    type="sensitiveFiles",
                    data={"sensitiveFiles": sensitive_files},
                )

        # Final sensitive files update
        await websocket_api.send(
            status="success",
            step_name="identifying",
            message="Identified sensitive files for in-depth analysis",
            type="sensitiveFiles",
            data={"sensitiveFiles": sensitive_files},
        )

        # Reset progress tracker for in-depth analysis
        progress_tracker = ProgressTracker(
            len(sensitive_files), batch_size=5
        )  # Smaller batch size for detailed analysis

        # In-depth analysis with progress tracking
        in_depth_results = []
        for file_info in sensitive_files:
            file_analysis = utils.analyze_file_in_depth(CLONE_DIR / file_info["path"])
            in_depth_results.append(file_analysis)

            should_send, progress = progress_tracker.should_send_update()
            if should_send:
                await websocket_api.send(
                    status="inProgress",
                    step_name="reviewing",
                    message=f"Performing in-depth analysis ({progress}%)",
                    type="inDepthAnalysis",
                    data={"results": in_depth_results},
                )

        # Final in-depth analysis update
        await websocket_api.send(
            status="success",
            step_name="reviewing",
            message="In-depth analysis finished",
            type="inDepthAnalysis",
            data={"results": in_depth_results},
        )

        # Store analysis data and cleanup
        await utils.store_analysis_data(
            {
                "url": repository_url,
                "files_count": total_files,
                "lines_count": total_line_count,
                "languages": programming_languages,
                "sensitive_files": sensitive_files,
                "in_depth_results": in_depth_results,
            }
        )

        utils.clean_dir(CLONE_DIR)
        await websocket.close()
        return
