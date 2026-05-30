import os
import aiosqlite
import json
from pathlib import Path

_DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent)))
DB_PATH = _DATA_DIR / "pokeoffice.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # ── Tablas de plataforma (multi-tenant) ───────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                nombre_negocio TEXT DEFAULT '',
                email TEXT UNIQUE NOT NULL,
                plan TEXT DEFAULT 'starter',
                activo INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                last_activity TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                email TEXT UNIQUE NOT NULL,
                nombre TEXT DEFAULT '',
                activo INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                last_login TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invitaciones (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                email TEXT NOT NULL,
                codigo TEXT NOT NULL,
                usado INTEGER DEFAULT 0,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # ── Tablas operativas con tenant_id ───────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL DEFAULT '',
                user_message TEXT NOT NULL,
                vp_response TEXT,
                events TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS agent_configs (
                agent_id TEXT PRIMARY KEY,
                display_name TEXT,
                custom_instructions TEXT DEFAULT '',
                enabled INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS recordatorios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL DEFAULT '',
                texto TEXT NOT NULL,
                tipo TEXT DEFAULT 'recordatorio',
                fecha TEXT DEFAULT (strftime('%d/%m/%Y %H:%M', 'now', 'localtime')),
                completado INTEGER DEFAULT 0,
                origen TEXT DEFAULT 'manual',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # configuracion con clave compuesta (clave, tenant_id)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT NOT NULL,
                tenant_id TEXT NOT NULL DEFAULT '',
                valor TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (clave, tenant_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vp_memoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL DEFAULT '',
                tipo TEXT NOT NULL,
                aprendizaje TEXT NOT NULL,
                contexto TEXT DEFAULT '',
                relevancia INTEGER DEFAULT 5,
                usos INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                last_used TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS solicitudes_registro (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                nombre TEXT DEFAULT '',
                mensaje TEXT DEFAULT '',
                atendida INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── Migraciones ───────────────────────────────────────────────────────

        # tenants: spreadsheet_id
        try:
            await db.execute("ALTER TABLE tenants ADD COLUMN spreadsheet_id TEXT DEFAULT NULL")
        except Exception:
            pass

        # configuracion: migrar de PK simple (clave) a compuesta (clave, tenant_id)
        cursor = await db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='configuracion'"
        )
        row = await cursor.fetchone()
        if row and 'tenant_id' not in (row[0] or ''):
            await db.execute("ALTER TABLE configuracion RENAME TO _configuracion_old")
            await db.execute("""
                CREATE TABLE configuracion (
                    clave TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT '',
                    valor TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (clave, tenant_id)
                )
            """)
            await db.execute(
                "INSERT INTO configuracion (clave, tenant_id, valor, updated_at) "
                "SELECT clave, '', valor, updated_at FROM _configuracion_old"
            )
            await db.execute("DROP TABLE _configuracion_old")

        await db.commit()


# ── Configuración del negocio ─────────────────────────────────────────────────

async def get_config(clave: str, tenant_id: str = "", default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT valor FROM configuracion WHERE clave = ? AND tenant_id = ?",
            (clave, tenant_id),
        )
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_config(clave: str, valor: str, tenant_id: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO configuracion (clave, tenant_id, valor) VALUES (?, ?, ?) "
            "ON CONFLICT(clave, tenant_id) DO UPDATE SET valor=excluded.valor, updated_at=datetime('now')",
            (clave, tenant_id, valor),
        )
        await db.commit()


async def get_all_config(tenant_id: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT clave, valor FROM configuracion WHERE tenant_id = ?", (tenant_id,)
        )
        rows = await cursor.fetchall()
        return {r["clave"]: r["valor"] for r in rows}


# ── Memoria del VP (privada, por tenant) ──────────────────────────────────────

async def guardar_aprendizaje(tipo: str, aprendizaje: str, contexto: str = "",
                               relevancia: int = 5, tenant_id: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM vp_memoria WHERE aprendizaje = ? AND tenant_id = ?",
            (aprendizaje, tenant_id),
        )
        if await cursor.fetchone():
            return
        await db.execute(
            "INSERT INTO vp_memoria (tenant_id, tipo, aprendizaje, contexto, relevancia) "
            "VALUES (?,?,?,?,?)",
            (tenant_id, tipo, aprendizaje, contexto, relevancia),
        )
        await db.commit()


async def obtener_memoria(limit: int = 30, tenant_id: str = "") -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT tipo, aprendizaje, usos FROM vp_memoria "
            "WHERE tenant_id = ? "
            "ORDER BY relevancia DESC, usos DESC, created_at DESC LIMIT ?",
            (tenant_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def marcar_usado(aprendizaje: str, tenant_id: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE vp_memoria SET usos = usos + 1, last_used = datetime('now') "
            "WHERE aprendizaje = ? AND tenant_id = ?", (aprendizaje, tenant_id)
        )
        await db.commit()


# ── Recordatorios ─────────────────────────────────────────────────────────────

async def listar_recordatorios(tenant_id: str = "") -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM recordatorios WHERE tenant_id = ? "
            "ORDER BY completado ASC, created_at DESC",
            (tenant_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def crear_recordatorio(texto: str, tipo: str = "recordatorio",
                              origen: str = "manual", tenant_id: str = "") -> dict:
    from datetime import datetime
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO recordatorios (tenant_id, texto, tipo, fecha, origen) "
            "VALUES (?, ?, ?, ?, ?)",
            (tenant_id, texto, tipo, fecha, origen),
        )
        await db.commit()
        rid = cursor.lastrowid
    return {"id": rid, "tenant_id": tenant_id, "texto": texto, "tipo": tipo,
            "fecha": fecha, "completado": False, "origen": origen}


async def toggle_recordatorio(rid: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE recordatorios SET completado = NOT completado WHERE id = ?", (rid,)
        )
        await db.commit()
        cursor = await db.execute("SELECT completado FROM recordatorios WHERE id = ?", (rid,))
        row = await cursor.fetchone()
        return bool(row[0]) if row else False


async def eliminar_recordatorio(rid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM recordatorios WHERE id = ?", (rid,))
        await db.commit()


async def save_conversation(user_message: str, vp_response: str, events: list,
                             tenant_id: str = "") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO conversations (tenant_id, user_message, vp_response, events) "
            "VALUES (?, ?, ?, ?)",
            (tenant_id, user_message, vp_response, json.dumps(events, ensure_ascii=False)),
        )
        await db.commit()
        return cursor.lastrowid


async def get_history(limit: int = 20, tenant_id: str = "") -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, user_message, vp_response, created_at FROM conversations "
            "WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
