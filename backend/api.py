import os
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import jwt as _jwt

load_dotenv()

log = logging.getLogger("pokeoffice")

from db.models import (
    init_db, save_conversation, get_history,
    listar_recordatorios, crear_recordatorio,
    toggle_recordatorio, eliminar_recordatorio,
    get_config, set_config, get_all_config,
)
from db.admin_models import init_feedback_table
from agents.vp import run_vp
from routers.admin import router as admin_router
from routers.auth  import router as auth_router, JWT_SECRET, JWT_ALGORITHM
from mcp.sheets_client import (
    load_config, crear_planilla_maestra, actualizar_formulas_planilla,
    listar_stock, get_dashboard_data,
)


# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        payload = json.dumps(data, ensure_ascii=False)
        for ws in list(self.active):
            try:
                await ws.send_text(payload)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


# ── Scheduler jobs ────────────────────────────────────────────────────────────

async def job_briefing_diario():
    """Se ejecuta a las 9am. Genera un post-it de briefing del día."""
    log.info("Scheduler: briefing diario")
    try:
        fecha_hoy = datetime.now().strftime("%A %d/%m/%Y").capitalize()
        texto     = f"☀️ Briefing del día — {fecha_hoy}\nRevisá agenda, turnos y stock."
        rec = await crear_recordatorio(texto, tipo="recordatorio", origen="scheduler")
        await manager.broadcast({"type": "recordatorio_nuevo", "recordatorio": rec})
    except Exception as e:
        log.error("job_briefing_diario: %s", e)


async def job_alerta_stock():
    """Diario: verifica productos con stock bajo (≤5 unidades)."""
    log.info("Scheduler: alerta stock")
    try:
        productos = listar_stock()
        bajos = [
            p for p in productos
            if int(str(p.get("unidades", "0")).strip() or "0") <= 5
               and p.get("codigo", "").strip()
        ]
        if not bajos:
            return
        lista = "\n".join(
            f"• {p['descripcion'] or p['codigo']} — {p['unidades']} u."
            for p in bajos[:8]
        )
        texto = f"📦 Stock bajo en {len(bajos)} producto(s):\n{lista}"
        rec = await crear_recordatorio(texto, tipo="stock", origen="scheduler")
        await manager.broadcast({"type": "recordatorio_nuevo", "recordatorio": rec})
    except Exception as e:
        log.error("job_alerta_stock: %s", e)


async def iniciar_scheduler():
    """Loop asíncrono que ejecuta los jobs en horario."""
    import asyncio
    while True:
        now = datetime.now()
        # Briefing a las 9:00
        if now.hour == 9 and now.minute == 0:
            await job_briefing_diario()
        # Stock check a las 8:00 y 14:00
        if now.hour in (8, 14) and now.minute == 0:
            await job_alerta_stock()
        await asyncio.sleep(60)   # revisar cada minuto


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_feedback_table()
    scheduler_task = asyncio.create_task(iniciar_scheduler())
    yield
    scheduler_task.cancel()


app = FastAPI(title="Pokeoffice API", lifespan=lifespan)
app.include_router(admin_router)
app.include_router(auth_router)

# ── Rutas y prefijos que no requieren auth de usuario ─────────────────────────
_PUBLIC_EXACT    = {"/health", "/ws", "/auth/solicitar", "/auth/verificar"}
_PUBLIC_PREFIXES = ("/api/admin", "/assets", "/sprites", "/auth/")


@app.middleware("http")
async def user_auth_middleware(request: Request, call_next):
    path   = request.url.path
    method = request.method

    # Rutas públicas exactas o por prefijo
    if path in _PUBLIC_EXACT or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return await call_next(request)

    # Navegación del browser (Accept: text/html) → sirve el SPA sin auth
    if "text/html" in request.headers.get("accept", ""):
        return await call_next(request)

    # Upgrade de WebSocket → pasa directo (el handler valida el token)
    if request.headers.get("upgrade", "").lower() == "websocket":
        return await call_next(request)

    # Verificar JWT de usuario
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return JSONResponse({"detail": "No autenticado"}, status_code=401)

    try:
        payload = _jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "user":
            raise ValueError("Not a user token")
    except Exception:
        return JSONResponse({"detail": "Token inválido o expirado"}, status_code=401)

    # Verificar que el tenant siga existiendo en la DB (puede haber sido eliminado)
    from db.admin_models import get_tenant
    tenant = await get_tenant(payload.get("tenant_id", ""))
    if not tenant:
        return JSONResponse({"detail": "Cuenta no encontrada"}, status_code=401)

    request.state.user = payload

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ── Mensajes al VP ────────────────────────────────────────────────────────────

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


# ── Historial ─────────────────────────────────────────────────────────────────

@app.get("/history")
async def history(limit: int = 20):
    return await get_history(limit)


# ── Agentes ───────────────────────────────────────────────────────────────────

@app.get("/agents")
async def agents_info():
    return [
        {"id": "vp",               "name": "VP / Jefe de Gabinete",  "color": "#4A90D9"},
        {"id": "atencion_cliente", "name": "Recepcionista",           "color": "#27AE60"},
        {"id": "contador",         "name": "Contador",                "color": "#F39C12"},
        {"id": "proveedores",      "name": "Gest. Proveedores",       "color": "#8E44AD"},
        {"id": "marketing",        "name": "Marketing & Diseño",      "color": "#E91E63"},
        {"id": "programador",      "name": "Programador",             "color": "#607D8B"},
    ]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/admin/diag-google", dependencies=[])
async def diag_google():
    """Diagnóstico de credenciales Google — solo para debugging, remover en prod."""
    results = {}
    try:
        from mcp.sheets_client import _creds, _drive
        creds = _creds()
        results["auth"] = "ok"
        results["service_account_email"] = getattr(creds, "service_account_email", "n/a")
    except Exception as e:
        results["auth"] = f"ERROR: {e}"
        return results
    try:
        drv = _drive()
        files = drv.files().list(pageSize=1, fields="files(id,name)").execute()
        results["drive_list"] = "ok"
        results["drive_files_count"] = len(files.get("files", []))
    except Exception as e:
        results["drive_list"] = f"ERROR: {e}"
    try:
        from mcp.sheets_client import _sheets
        svc = _sheets()
        test = svc.spreadsheets().create(
            body={"properties": {"title": "_test_diag_delete_me"}},
            fields="spreadsheetId"
        ).execute()
        results["sheets_create"] = "ok"
        results["test_spreadsheet_id"] = test["spreadsheetId"]
        # Eliminar inmediatamente
        drv = _drive()
        drv.files().delete(fileId=test["spreadsheetId"]).execute()
        results["sheets_delete"] = "ok"
    except Exception as e:
        results["sheets_create"] = f"ERROR: {e}"
    return results


# ── Planilla ──────────────────────────────────────────────────────────────────

@app.get("/planilla")
async def planilla_info(request: Request):
    from db.admin_models import get_tenant
    user = getattr(request.state, "user", {})
    tenant = await get_tenant(user.get("tenant_id", ""))
    sid = tenant.get("spreadsheet_id") if tenant else None
    if not sid:
        return {"configured": False}
    return {
        "configured": True,
        "spreadsheet_id": sid,
        "url": f"https://docs.google.com/spreadsheets/d/{sid}",
        "business_name": tenant.get("nombre_negocio", ""),
    }


class SetupRequest(BaseModel):
    nombre_negocio: str


@app.post("/planilla/setup")
async def setup_planilla(req: SetupRequest, request: Request):
    from db.admin_models import set_tenant_spreadsheet_id
    user = getattr(request.state, "user", {})
    tenant_id   = user.get("tenant_id", "")
    email_owner = user.get("email", "")
    try:
        sid = crear_planilla_maestra(req.nombre_negocio, email_cliente=email_owner or None)
        if tenant_id:
            await set_tenant_spreadsheet_id(tenant_id, sid)
        return {"ok": True, "spreadsheet_id": sid,
                "url": f"https://docs.google.com/spreadsheets/d/{sid}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/planilla/actualizar-formulas")
async def fix_formulas():
    try:
        result = actualizar_formulas_planilla()
        return {"ok": True, "message": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Recordatorios / Post-its ──────────────────────────────────────────────────

@app.get("/recordatorios")
async def get_recordatorios():
    return await listar_recordatorios()


class RecordatorioRequest(BaseModel):
    texto:      str
    tipo:       str = "recordatorio"
    fecha:      str = ""
    completado: bool = False
    origen:     str = "manual"


@app.post("/recordatorios")
async def post_recordatorio(req: RecordatorioRequest):
    rec = await crear_recordatorio(req.texto, req.tipo, req.origen)
    # Broadcast para que todos los clientes conectados vean el nuevo post-it
    await manager.broadcast({"type": "recordatorio_nuevo", "recordatorio": rec})
    return rec


@app.patch("/recordatorios/{rid}/toggle")
async def patch_toggle(rid: int):
    completado = await toggle_recordatorio(rid)
    return {"id": rid, "completado": completado}


@app.delete("/recordatorios/{rid}")
async def delete_recordatorio(rid: int):
    await eliminar_recordatorio(rid)
    return {"ok": True}


# ── Scheduler manual (para testing) ──────────────────────────────────────────

@app.post("/scheduler/briefing")
async def trigger_briefing():
    """Dispara el briefing diario manualmente."""
    await job_briefing_diario()
    return {"ok": True}


@app.post("/scheduler/stock")
async def trigger_stock():
    """Dispara el chequeo de stock manualmente."""
    await job_alerta_stock()
    return {"ok": True}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/config")
async def get_configuracion():
    return await get_all_config()


class ConfigRequest(BaseModel):
    clave: str
    valor: str


@app.post("/config")
async def set_configuracion(req: ConfigRequest):
    await set_config(req.clave, req.valor)
    return {"ok": True}


class OnboardingRequest(BaseModel):
    nombre_negocio:  str
    nombre_jefe:     str
    tipo_negocio:    str
    moneda:          str = "ARS"
    sector:          str = ""
    descripcion:     str = ""


@app.post("/config/onboarding")
async def completar_onboarding(req: OnboardingRequest):
    """Guarda toda la configuración inicial del negocio de una sola vez."""
    campos = req.model_dump()
    for clave, valor in campos.items():
        if valor:
            await set_config(clave, valor)
    await set_config("onboarding_completado", "true")
    return {"ok": True}


@app.get("/dashboard")
async def dashboard():
    """KPIs financieros + stock bajo + últimos movimientos para el dashboard."""
    try:
        data = get_dashboard_data()
        return data
    except Exception as e:
        log.error("dashboard: %s", e)
        return {"error": str(e), "finanzas": {}, "movimientos": [], "stock_bajo": []}


# ── Frontend estático (debe ir al final, después de todas las rutas API) ──────

_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    # Assets compilados por Vite (JS, CSS)
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")
    # Sprites y archivos públicos
    sprites_dir = _FRONTEND_DIST / "sprites"
    if sprites_dir.exists():
        app.mount("/sprites", StaticFiles(directory=sprites_dir), name="sprites")

    # SPA catch-all: cualquier ruta que no sea API devuelve index.html
    # Esto permite /admin, /dashboard, etc. en el frontend
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse(_FRONTEND_DIST / "index.html")
