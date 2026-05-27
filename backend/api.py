import os
import json
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from db.models import init_db, save_conversation, get_history
from agents.vp import run_vp
from mcp.sheets_client import load_config, get_spreadsheet_url, crear_planilla_maestra


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        payload = json.dumps(data, ensure_ascii=False)
        for ws in list(self.active):
            try:
                await ws.send_text(payload)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Pokeoffice API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive: client pings
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ── REST ───────────────────────────────────────────────────────────────────────

class MessageRequest(BaseModel):
    message: str


@app.post("/message")
async def send_message(req: MessageRequest):
    events: list[dict] = []

    async def capture_and_broadcast(event: dict):
        events.append(event)
        await manager.broadcast(event)

    result = await run_vp(req.message, broadcast=capture_and_broadcast)
    await save_conversation(req.message, result, events)
    return {"response": result}


@app.get("/history")
async def history(limit: int = 20):
    return await get_history(limit)


@app.get("/agents")
async def agents_info():
    return [
        {"id": "vp",               "name": "VP / Jefe de Gabinete",   "color": "#4A90D9", "x": 400, "y": 260},
        {"id": "atencion_cliente", "name": "Recepcionista",            "color": "#27AE60", "x": 110, "y": 160},
        {"id": "contador",         "name": "Contador",                 "color": "#F39C12", "x": 230, "y": 160},
        {"id": "proveedores",      "name": "Gest. Proveedores",        "color": "#8E44AD", "x": 350, "y": 160},
        {"id": "rrhh",             "name": "RRHH / Legal",             "color": "#E74C3C", "x": 470, "y": 160},
        {"id": "marketing",        "name": "Marketing",                "color": "#E91E63", "x": 590, "y": 160},
    ]


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Planilla Maestra ───────────────────────────────────────────────────────────

@app.get("/planilla")
async def planilla_info():
    cfg = load_config()
    sid = cfg.get("spreadsheet_id")
    if not sid:
        return {"configured": False, "message": "Planilla no configurada. Ejecutá scripts/crear_planilla.py"}
    return {
        "configured": True,
        "spreadsheet_id": sid,
        "url": f"https://docs.google.com/spreadsheets/d/{sid}",
        "business_name": cfg.get("business_name", ""),
    }


class SetupRequest(BaseModel):
    nombre_negocio: str


@app.post("/planilla/setup")
async def setup_planilla(req: SetupRequest):
    try:
        sid = crear_planilla_maestra(req.nombre_negocio)
        return {
            "ok": True,
            "spreadsheet_id": sid,
            "url": f"https://docs.google.com/spreadsheets/d/{sid}",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
