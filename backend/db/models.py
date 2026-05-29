import os
import aiosqlite
import json
from pathlib import Path

_DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent)))
DB_PATH = _DATA_DIR / "pokeoffice.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                texto TEXT NOT NULL,
                tipo TEXT DEFAULT 'recordatorio',
                fecha TEXT DEFAULT (strftime('%d/%m/%Y %H:%M', 'now', 'localtime')),
                completado INTEGER DEFAULT 0,
                origen TEXT DEFAULT 'manual',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vp_memoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                aprendizaje TEXT NOT NULL,
                contexto TEXT DEFAULT '',
                relevancia INTEGER DEFAULT 5,
                usos INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                last_used TEXT
            )
        """)
        await db.commit()


# ── Configuración del negocio ─────────────────────────────────────────────────

async def get_config(clave: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
        row = await cursor.fetchone()
        return row[0] if row else default


async def set_config(clave: str, valor: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO configuracion (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor, updated_at=datetime('now')",
            (clave, valor),
        )
        await db.commit()


async def get_all_config() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT clave, valor FROM configuracion")
        rows = await cursor.fetchall()
        return {r["clave"]: r["valor"] for r in rows}


# ── Memoria del VP (privada) ──────────────────────────────────────────────────

async def guardar_aprendizaje(tipo: str, aprendizaje: str, contexto: str = "",
                               relevancia: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        # Evitar duplicados exactos
        cursor = await db.execute(
            "SELECT id FROM vp_memoria WHERE aprendizaje = ?", (aprendizaje,)
        )
        if await cursor.fetchone():
            return  # ya existe
        await db.execute(
            "INSERT INTO vp_memoria (tipo, aprendizaje, contexto, relevancia) VALUES (?,?,?,?)",
            (tipo, aprendizaje, contexto, relevancia),
        )
        await db.commit()


async def obtener_memoria(limit: int = 30) -> list[dict]:
    """Devuelve los aprendizajes más relevantes, ordenados por relevancia y uso."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT tipo, aprendizaje, usos FROM vp_memoria "
            "ORDER BY relevancia DESC, usos DESC, created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def marcar_usado(aprendizaje: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE vp_memoria SET usos = usos + 1, last_used = datetime('now') "
            "WHERE aprendizaje = ?", (aprendizaje,)
        )
        await db.commit()


# ── Recordatorios ─────────────────────────────────────────────────────────────

async def listar_recordatorios() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM recordatorios ORDER BY completado ASC, created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def crear_recordatorio(texto: str, tipo: str = "recordatorio",
                              origen: str = "manual") -> dict:
    from datetime import datetime
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO recordatorios (texto, tipo, fecha, origen) VALUES (?, ?, ?, ?)",
            (texto, tipo, fecha, origen),
        )
        await db.commit()
        rid = cursor.lastrowid
    return {"id": rid, "texto": texto, "tipo": tipo, "fecha": fecha,
            "completado": False, "origen": origen}


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


async def save_conversation(user_message: str, vp_response: str, events: list) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO conversations (user_message, vp_response, events) VALUES (?, ?, ?)",
            (user_message, vp_response, json.dumps(events, ensure_ascii=False)),
        )
        await db.commit()
        return cursor.lastrowid


async def get_history(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, user_message, vp_response, created_at FROM conversations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
