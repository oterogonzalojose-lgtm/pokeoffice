"""
Router admin — todos los endpoints bajo /admin/*.
Protegido con JWT firmado con ADMIN_SECRET.
Nunca exponer estos endpoints al usuario final.
"""
import os
from datetime import datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from db.admin_models import (
    crear_tenant, listar_tenants, get_tenant, toggle_tenant,
    listar_users_tenant, crear_invitacion, listar_invitaciones_tenant,
    get_vp_memoria_tenant, get_metricas_tenant,
    listar_feedback, marcar_feedback_leido,
    listar_solicitudes, atender_solicitud,
    listar_platform_events, actualizar_estado_event,
)

router   = APIRouter(prefix="/api/admin", tags=["admin"])
_bearer  = HTTPBearer()

ADMIN_SECRET   = os.getenv("ADMIN_SECRET", "cambiar-en-produccion")
JWT_ALGORITHM  = "HS256"
# ── Auth ──────────────────────────────────────────────────────────────────────

def _make_token() -> str:
    return jwt.encode({"role": "admin"}, ADMIN_SECRET, algorithm=JWT_ALGORITHM)


def _require_admin(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    try:
        payload = jwt.decode(creds.credentials, ADMIN_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "admin":
            raise ValueError
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def admin_login(req: LoginRequest):
    expected = os.getenv("ADMIN_PASSWORD", "")
    if not expected or req.password != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta")
    return {"token": _make_token()}


# ── Tenants ───────────────────────────────────────────────────────────────────

class TenantRequest(BaseModel):
    email:          str
    nombre_negocio: str = ""
    plan:           str = "starter"


@router.get("/tenants", dependencies=[Depends(_require_admin)])
async def get_tenants():
    return await listar_tenants()


@router.post("/tenants", dependencies=[Depends(_require_admin)])
async def post_tenant(req: TenantRequest):
    return await crear_tenant(req.email, req.nombre_negocio, req.plan)


@router.get("/tenants/{tid}", dependencies=[Depends(_require_admin)])
async def get_tenant_detail(tid: str):
    t = await get_tenant(tid)
    if not t:
        raise HTTPException(404, "Tenant no encontrado")
    users    = await listar_users_tenant(tid)
    invites  = await listar_invitaciones_tenant(tid)
    metricas = await get_metricas_tenant(tid)
    return {**t, "users": users, "invitaciones": invites, "metricas": metricas}


@router.patch("/tenants/{tid}/toggle", dependencies=[Depends(_require_admin)])
async def patch_toggle_tenant(tid: str, activo: bool):
    await toggle_tenant(tid, activo)
    return {"ok": True}


# ── VP Memoria (prompt secreto) ───────────────────────────────────────────────

@router.get("/tenants/{tid}/memoria", dependencies=[Depends(_require_admin)])
async def get_memoria(tid: str):
    return await get_vp_memoria_tenant(tid)


# ── Invitaciones ──────────────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str


@router.post("/tenants/{tid}/invite", dependencies=[Depends(_require_admin)])
async def post_invite(tid: str, req: InviteRequest):
    t = await get_tenant(tid)
    if not t:
        raise HTTPException(404, "Tenant no encontrado")
    try:
        inv = await crear_invitacion(tid, req.email)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return inv


# ── Feedback ──────────────────────────────────────────────────────────────────

@router.get("/feedback", dependencies=[Depends(_require_admin)])
async def get_feedback(solo_no_leido: bool = False):
    return await listar_feedback(solo_no_leido)


@router.patch("/feedback/{fid}/leer", dependencies=[Depends(_require_admin)])
async def patch_feedback_leido(fid: int):
    await marcar_feedback_leido(fid)
    return {"ok": True}


# ── Solicitudes de registro ───────────────────────────────────────────────────

@router.get("/solicitudes", dependencies=[Depends(_require_admin)])
async def get_solicitudes(solo_pendientes: bool = True):
    return await listar_solicitudes(solo_pendientes)


@router.patch("/solicitudes/{sid}/atender", dependencies=[Depends(_require_admin)])
async def patch_atender_solicitud(sid: int):
    await atender_solicitud(sid)
    return {"ok": True}


# ── Vincular planilla existente desde admin ───────────────────────────────────

class VincularAdminRequest(BaseModel):
    spreadsheet_id: str

@router.post("/tenants/{tid}/vincular-planilla", dependencies=[Depends(_require_admin)])
async def vincular_planilla_tenant(tid: str, req: VincularAdminRequest):
    t = await get_tenant(tid)
    if not t:
        raise HTTPException(404, "Tenant no encontrado")
    sid = req.spreadsheet_id.strip()
    if "spreadsheets/d/" in sid:
        sid = sid.split("spreadsheets/d/")[1].split("/")[0].split("?")[0]
    try:
        from mcp.sheets_client import configurar_planilla_existente
        from db.admin_models import set_tenant_spreadsheet_id
        nombre = t.get("nombre_negocio") or t["email"]
        configurar_planilla_existente(sid, nombre)
        await set_tenant_spreadsheet_id(tid, sid)
        return {"ok": True, "spreadsheet_id": sid,
                "url": f"https://docs.google.com/spreadsheets/d/{sid}"}
    except Exception as e:
        raise HTTPException(500, f"Error al vincular planilla: {e}")


# ── Platform Events (Master DEV) ─────────────────────────────────────────────

ESTADOS_VALIDOS = {"pendiente", "en_desarrollo", "implementado", "descartado"}

@router.get("/platform-events", dependencies=[Depends(_require_admin)])
async def get_platform_events(tipo: str = "", estado: str = ""):
    return await listar_platform_events(tipo=tipo, estado=estado)


@router.patch("/platform-events/{eid}/estado", dependencies=[Depends(_require_admin)])
async def patch_platform_event_estado(eid: int, estado: str):
    if estado not in ESTADOS_VALIDOS:
        raise HTTPException(400, f"Estado inválido. Opciones: {ESTADOS_VALIDOS}")
    await actualizar_estado_event(eid, estado)
    return {"ok": True}


# ── Crear planilla maestra desde admin ───────────────────────────────────────

@router.post("/tenants/{tid}/crear-planilla", dependencies=[Depends(_require_admin)])
async def crear_planilla_tenant(tid: str):
    t = await get_tenant(tid)
    if not t:
        raise HTTPException(404, "Tenant no encontrado")
    try:
        from mcp.sheets_client import crear_planilla_maestra
        from db.admin_models import set_tenant_spreadsheet_id
        nombre = t.get("nombre_negocio") or t["email"]
        sid    = crear_planilla_maestra(nombre, email_cliente=t["email"])
        await set_tenant_spreadsheet_id(tid, sid)
        return {"ok": True, "spreadsheet_id": sid,
                "url": f"https://docs.google.com/spreadsheets/d/{sid}"}
    except Exception as e:
        raise HTTPException(500, f"Error al crear planilla: {e}")


# ── Diagnóstico del sistema ───────────────────────────────────────────────────

@router.get("/diagnostico")
async def get_diagnostico(pw: str = ""):
    """
    Endpoint de diagnóstico para debugging en producción.
    Muestra estado real de DB, Sheets y memoria por tenant.
    """
    expected = os.getenv("ADMIN_PASSWORD", "")
    if not expected or pw != expected:
        raise HTTPException(status_code=401, detail="Password incorrecta")

    from db.models import DB_PATH
    import aiosqlite

    resultado = {
        "db_path": str(DB_PATH),
        "db_exists": DB_PATH.exists(),
        "env": {
            "DATA_DIR": os.getenv("DATA_DIR", "no seteado"),
            "ANTHROPIC_API_KEY": "ok" if os.getenv("ANTHROPIC_API_KEY") else "FALTA",
            "GOOGLE_SERVICE_ACCOUNT_JSON": "ok" if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") else "FALTA",
            "ADMIN_SECRET": os.getenv("ADMIN_SECRET", "")[:4] + "..." if os.getenv("ADMIN_SECRET") else "FALTA",
        },
        "tenants": [],
        "platform_events_total": 0,
        "bg_tasks_activos": 0,
    }

    # Estado de tasks en background
    try:
        from agents.vp import _bg_tasks
        resultado["bg_tasks_activos"] = len(_bg_tasks)
    except Exception:
        pass

    # Conteo de platform_events
    try:
        events = await listar_platform_events()
        resultado["platform_events_total"] = len(events)
        resultado["platform_events_recientes"] = events[:5]
    except Exception as e:
        resultado["platform_events_error"] = str(e)

    # Info por tenant — usar get_tenant (SELECT *) para incluir spreadsheet_id
    try:
        tenants = await listar_tenants()
        for t in tenants:
            tid = t["id"]
            # listar_tenants() no incluye spreadsheet_id en su SELECT — leer con get_tenant
            t_full = await get_tenant(tid) or {}
            info: dict = {
                "id": tid,
                "email": t.get("email"),
                "nombre_negocio": t.get("nombre_negocio"),
                "activo": t.get("activo"),
                "spreadsheet_id_db": t_full.get("spreadsheet_id"),
                "memoria_count": t.get("memoria_count", 0),
                "conv_count": t.get("conv_count", 0),
                "sheets_ok": None,
                "sheets_error": None,
            }

            # Probar conexión a sheets si tiene ID configurado
            sid = t_full.get("spreadsheet_id") or ""
            if sid:
                try:
                    from mcp.sheets_client import _sheets
                    meta = _sheets().spreadsheets().get(spreadsheetId=sid).execute()
                    info["sheets_ok"] = True
                    info["sheets_titulo"] = meta.get("properties", {}).get("title", "")
                except Exception as se:
                    info["sheets_ok"] = False
                    info["sheets_error"] = str(se)[:200]

            # Últimas memorias
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    cur = await db.execute(
                        "SELECT tipo, aprendizaje, user_email, created_at "
                        "FROM vp_memoria WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 3",
                        (tid,),
                    )
                    info["ultimas_memorias"] = [dict(r) for r in await cur.fetchall()]
            except Exception:
                info["ultimas_memorias"] = []

            resultado["tenants"].append(info)
    except Exception as e:
        resultado["tenants_error"] = str(e)

    return resultado
