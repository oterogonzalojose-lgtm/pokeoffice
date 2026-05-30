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
