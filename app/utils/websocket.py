import asyncio
import datetime
import logging
from typing import Literal, Optional, Union, Any

logger = logging.getLogger(__name__)

class WebSocketAPI:
    def __init__(self, websocket):
        self.websocket = websocket

    async def send(self, 
                   *,
                   status: Literal['success', 'pending', 'inProgress', 'error'], 
                   message: str,
                   step_name: Literal['connecting', 'cloning', 'identifying', 'reviewing'],
                   type: Optional[Literal['relativeFiles', 'repositoryScan', 'sensitiveFiles', 'inDepthAnalysis']] = None,
                   data: Optional[dict] = None,
                   progress: Optional[int] = None,
                   time: Optional[str] = None):
        """
        Send a message through the websocket with standardized format.
        
        Args:
            status: Current status of the operation
            message: Message to send
            step_name: Name of the current step
            type: Type of the message (optional)
            data: Additional data to send (optional)
            progress: Progress percentage (0-100) (optional)
            time: ISO formatted timestamp (optional)
        """
        logger.debug(f"Sending message: {message}")
        logger.debug(f"Type: {type}")
        logger.debug(f"Data: {data}")
        
        payload: dict[str, Any] = {
            "time": time or datetime.datetime.now().isoformat(),
            "status": status,
            "message": message,
            "stepName": step_name
        }
        
        if type is not None:
            payload["type"] = type
        if data is not None:
            payload["data"] = data
        if progress is not None:
            payload["progress"] = progress

        await self.send_json(payload)
        await self.yield_control()

    async def send_json(self, data: dict[str, Any]):
        await self.websocket.send_json(data)

    async def yield_control(self):
        await asyncio.sleep(0)  # Yield control back to the event loop
