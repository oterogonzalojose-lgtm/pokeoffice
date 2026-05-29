"""
Router de autenticación de usuarios.
Endpoints públicos: /auth/solicitar, /auth/verificar
Requiere auth:      /auth/me
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

import aiosqlite
from db.models import DB_PATH
from db.admin_models import crear_solicitud

router   = APIRouter(prefix="/auth", tags=["auth"])
_bearer  = HTTPBearer(auto_error=False)

JWT_SECRET    = os.getenv("ADMIN_SECRET", "cambiar-en-produccion")
JWT_ALGORITHM = "HS256"
TOKEN_DAYS    = 30


# ── Utilidades JWT ────────────────────────────────────────────────────────────

def make_user_token(user_id: str, tenant_id: str, email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)
    return jwt.encode(
        {"role": "user", "user_id": user_id, "tenant_id": tenant_id, "email": email, "exp": exp},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )


def decode_user_token(token: str) -> dict:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("role") != "user":
        raise ValueError("Not a user token")
    return payload


def get_current_user(request: Request) -> dict | None:
    """Dependencia para rutas protegidas. Lanza 401 si no hay token válido."""
    return getattr(request.state, "user", None)


# ── Solicitar acceso (registro) ───────────────────────────────────────────────

class SolicitudRequest(BaseModel):
    email:   str
    nombre:  str = ""
    mensaje: str = ""


@router.post("/solicitar")
async def solicitar_acceso(req: SolicitudRequest):
    if not req.email or "@" not in req.email:
        raise HTTPException(400, "Email inválido")
    await crear_solicitud(req.email, req.nombre, req.mensaje)
    return {
        "ok": True,
        "mensaje": "Tu solicitud fue recibida. El equipo de Pokeoffice te enviará tu código de acceso en breve.",
    }


# ── Verificar código e iniciar sesión ─────────────────────────────────────────

class VerificarRequest(BaseModel):
    email:  str
    codigo: str


@router.post("/verificar")
async def verificar_codigo(req: VerificarRequest):
    email = req.email.lower().strip()
    codigo = req.codigo.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Buscar invitación válida
        cursor = await db.execute(
            """SELECT i.*, t.nombre_negocio FROM invitaciones i
               JOIN tenants t ON i.tenant_id = t.id
               WHERE i.email = ? AND i.codigo = ? AND i.usado = 0
               AND datetime(i.expires_at) > datetime('now')""",
            (email, codigo),
        )
        inv = await cursor.fetchone()
        if not inv:
            raise HTTPException(401, "Código inválido o vencido. Solicitá uno nuevo al equipo de Pokeoffice.")

        inv = dict(inv)
        tenant_id = inv["tenant_id"]

        # Verificar que el tenant esté activo
        cursor = await db.execute("SELECT activo FROM tenants WHERE id = ?", (tenant_id,))
        tenant = await cursor.fetchone()
        if not tenant or not tenant[0]:
            raise HTTPException(403, "Tu cuenta está inactiva. Contactá al soporte.")

        # Obtener o crear el usuario
        cursor = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = await cursor.fetchone()

        if user:
            user = dict(user)
            user_id = user["id"]
            await db.execute(
                "UPDATE users SET last_login = datetime('now') WHERE id = ?", (user_id,)
            )
        else:
            user_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO users (id, tenant_id, email, activo) VALUES (?,?,?,1)",
                (user_id, tenant_id, email),
            )

        # Marcar invitación como usada
        await db.execute("UPDATE invitaciones SET usado = 1 WHERE id = ?", (inv["id"],))
        # Actualizar last_activity del tenant
        await db.execute(
            "UPDATE tenants SET last_activity = datetime('now') WHERE id = ?", (tenant_id,)
        )
        await db.commit()

    token = make_user_token(user_id, tenant_id, email)
    return {
        "token": token,
        "user":  {"user_id": user_id, "tenant_id": tenant_id, "email": email},
    }


# ── Me (usuario actual) ───────────────────────────────────────────────────────

@router.get("/me")
async def me(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(401, "No autenticado")
    return user
