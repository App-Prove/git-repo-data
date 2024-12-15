from fastapi import FastAPI
from routers.ws.analysis import router as ws_router

app = FastAPI()
app.include_router(ws_router)
