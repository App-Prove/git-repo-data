import asyncio
import datetime
import logging
from typing import Literal, Optional

logger = logging.getLogger(__name__)

class WebSocketAPI:
    def __init__(self, websocket):
        self.websocket = websocket

    async def send(self, 
                   *,
                   status: Literal['success','pending', 'analyzing','error'], 
                   message,
                   step_name:Literal['connecting','cloning','identifying','reviewing'],
                   type:Optional[Literal['relativeFiles','repositoryScan','sensitiveFiles','inDepthAnalysis']]=None,
                   data=None):
        logger.debug(f"Sending success message: {message}")
        logger.debug(f"Type: {type}")
        logger.debug(f"Data: {data}")
        payload = {"time":datetime.datetime.now().isoformat(),"status": status, "message": message, "stepName": step_name}
        if type is not None:
            payload["type"] = type
        if data is not None:
            payload["data"] = data
        await self.send_json(payload)
        await self.yield_control()

    async def send_json(self, data):
        await self.websocket.send_json(data)

    async def yield_control(self):
        await asyncio.sleep(0)  # Yield control back to the event loop
