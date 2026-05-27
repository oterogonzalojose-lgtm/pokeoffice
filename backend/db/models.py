import aiosqlite
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "pokeoffice.db"


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
