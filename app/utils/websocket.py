import asyncio
import logging

logger = logging.getLogger(__name__)

class WebSocketAPI:
    def __init__(self, websocket):
        self.websocket = websocket

    async def send_success(self, *, message,type=None, data=None):
        logger.debug(f"Sending success message: {message}")
        logger.debug(f"Type: {type}")
        logger.debug(f"Data: {data}")
        payload = {"status": "success", "message": message}
        if type is not None:
            payload["type"] = type
        if data is not None:
            payload["data"] = data
        await self.send_json(payload)
        await self.yield_control()

    async def send_analyzing(self, *, message):
        await self.send_json({"status": "analyzing", "message": message})
        await self.yield_control()

    async def send_pending(self, *, message):
        await self.send_json({"status": "pending", "message": message})
        await self.yield_control()

    async def send_error(self, *, message):
        await self.send_json({"status": "error", "message": message})
        await self.yield_control()

    async def send_json(self, data):
        await self.websocket.send_json(data)

    async def yield_control(self):
        await asyncio.sleep(0)  # Yield control back to the event loop
