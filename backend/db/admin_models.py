"""
Funciones de DB exclusivas del panel admin.
Acceso de lectura/escritura cross-tenant — nunca exponer al usuario final.
"""
import json
import uuid
from datetime import datetime, timedelta

import aiosqlite

from .models import DB_PATH


# ── Tenants ───────────────────────────────────────────────────────────────────

async def crear_tenant(email: str, nombre_negocio: str = "", plan: str = "starter") -> dict:
    tid = str(uuid.uuid4())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tenants (id, email, nombre_negocio, plan) VALUES (?,?,?,?)",
            (tid, email.lower().strip(), nombre_negocio, plan),
        )
        await db.commit()
    return {"id": tid, "email": email, "nombre_negocio": nombre_negocio, "plan": plan}


async def listar_tenants() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT
                t.id, t.email, t.nombre_negocio, t.plan, t.activo,
                t.created_at, t.last_activity,
                (SELECT COUNT(*) FROM conversations c WHERE c.tenant_id = t.id) AS conv_count,
                (SELECT COUNT(*) FROM users u WHERE u.tenant_id = t.id AND u.activo = 1) AS user_count,
                (SELECT COUNT(*) FROM vp_memoria m WHERE m.tenant_id = t.id) AS memoria_count
            FROM tenants t
            ORDER BY t.created_at DESC
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_tenant(tid: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tenants WHERE id = ?", (tid,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def toggle_tenant(tid: str, activo: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tenants SET activo = ? WHERE id = ?", (1 if activo else 0, tid)
        )
        await db.commit()


# ── Usuarios por tenant ───────────────────────────────────────────────────────

async def listar_users_tenant(tid: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, email, nombre, activo, created_at, last_login "
            "FROM users WHERE tenant_id = ? ORDER BY created_at",
            (tid,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def contar_users_activos(tid: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE tenant_id = ? AND activo = 1", (tid,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ── Invitaciones ──────────────────────────────────────────────────────────────

MAX_USERS_PER_TENANT = 2


async def crear_invitacion(tid: str, email: str) -> dict:
    activos = await contar_users_activos(tid)
    if activos >= MAX_USERS_PER_TENANT:
        raise ValueError(
            f"El tenant ya tiene {MAX_USERS_PER_TENANT} usuarios activos. "
            "Este plan no permite más usuarios."
        )

    import secrets
    codigo = str(secrets.randbelow(900000) + 100000)  # 6 dígitos
    expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    iid = str(uuid.uuid4())

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO invitaciones (id, tenant_id, email, codigo, expires_at) VALUES (?,?,?,?,?)",
            (iid, tid, email.lower().strip(), codigo, expires),
        )
        await db.commit()

    return {"id": iid, "tenant_id": tid, "email": email, "codigo": codigo, "expires_at": expires}


async def listar_invitaciones_tenant(tid: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, email, usado, expires_at, created_at FROM invitaciones "
            "WHERE tenant_id = ? ORDER BY created_at DESC",
            (tid,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ── VP Memoria (prompt secreto) ───────────────────────────────────────────────

async def get_vp_memoria_tenant(tid: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT tipo, aprendizaje, contexto, relevancia, usos, created_at, last_used "
            "FROM vp_memoria WHERE tenant_id = ? "
            "ORDER BY relevancia DESC, usos DESC",
            (tid,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ── Métricas por tenant ───────────────────────────────────────────────────────

async def get_metricas_tenant(tid: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        # Conversaciones totales
        cur = await db.execute(
            "SELECT COUNT(*), MAX(created_at) FROM conversations WHERE tenant_id = ?", (tid,)
        )
        row = await cur.fetchone()
        total_conv = row[0] or 0
        last_conv  = row[1] or ""

        # Conversaciones últimos 7 días
        cur = await db.execute(
            "SELECT COUNT(*) FROM conversations "
            "WHERE tenant_id = ? AND created_at >= datetime('now', '-7 days')",
            (tid,),
        )
        row = await cur.fetchone()
        conv_7d = row[0] or 0

        # Agentes más usados (parseo de eventos JSON)
        cur = await db.execute(
            "SELECT events FROM conversations WHERE tenant_id = ? AND events != '[]'",
            (tid,),
        )
        rows = await cur.fetchall()
        agent_counts: dict[str, int] = {}
        for (events_str,) in rows:
            try:
                for ev in json.loads(events_str):
                    if ev.get("type") == "agent_message":
                        a = ev.get("to", "")
                        if a:
                            agent_counts[a] = agent_counts.get(a, 0) + 1
            except Exception:
                pass

        agentes_top = sorted(agent_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Errores recientes
        cur = await db.execute(
            "SELECT COUNT(*) FROM conversations "
            "WHERE tenant_id = ? AND events LIKE '%\"type\": \"error\"%'",
            (tid,),
        )
        row = await cur.fetchone()
        errores = row[0] or 0

    return {
        "total_conversaciones": total_conv,
        "ultima_conversacion":  last_conv,
        "conversaciones_7d":    conv_7d,
        "agentes_top":          [{"agente": a, "usos": c} for a, c in agentes_top],
        "errores_detectados":   errores,
    }


# ── Feedback ──────────────────────────────────────────────────────────────────

async def init_feedback_table():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT DEFAULT '',
                mensaje TEXT NOT NULL,
                tipo TEXT DEFAULT 'general',
                leido INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()


async def listar_feedback(solo_no_leido: bool = False) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        where = "WHERE leido = 0" if solo_no_leido else ""
        cursor = await db.execute(
            f"SELECT f.*, t.nombre_negocio, t.email FROM feedback f "
            f"LEFT JOIN tenants t ON f.tenant_id = t.id "
            f"{where} ORDER BY f.created_at DESC LIMIT 100"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def marcar_feedback_leido(fid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE feedback SET leido = 1 WHERE id = ?", (fid,))
        await db.commit()
