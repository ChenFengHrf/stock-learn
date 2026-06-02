from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .knowledge import connect


def init_memory(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        create table if not exists memories (
            id integer primary key,
            user_id text not null,
            kind text not null,
            topic text not null,
            content text not null,
            importance integer not null default 3,
            created_at text not null,
            updated_at text not null
        );
        create index if not exists idx_memories_user_topic on memories(user_id, topic);
        """
    )
    conn.commit()


def save_memory(
    db_path: Path,
    *,
    user_id: str,
    kind: str,
    topic: str,
    content: str,
    importance: int = 3,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        init_memory(conn)
        cursor = conn.execute(
            """
            insert into memories (
                user_id, kind, topic, content, importance, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, kind, topic, content, importance, now, now),
        )
        conn.commit()
        return int(cursor.lastrowid)


def search_memories(db_path: Path, *, user_id: str, query: str = "", limit: int = 8) -> list[dict]:
    if not db_path.exists():
        return []

    with connect(db_path) as conn:
        init_memory(conn)
        if query:
            like = f"%{query}%"
            rows = conn.execute(
                """
                select id, kind, topic, content, importance, updated_at
                from memories
                where user_id = ? and (topic like ? or content like ? or kind like ?)
                order by importance desc, updated_at desc
                limit ?
                """,
                (user_id, like, like, like, limit),
            )
        else:
            rows = conn.execute(
                """
                select id, kind, topic, content, importance, updated_at
                from memories
                where user_id = ?
                order by importance desc, updated_at desc
                limit ?
                """,
                (user_id, limit),
            )

        return [dict(row) for row in rows]


def format_memories(rows: list[dict]) -> str:
    if not rows:
        return "没有找到相关长期记忆。"
    return "\n".join(
        f"- #{row['id']} [{row['kind']}] {row['topic']}: {row['content']}"
        for row in rows
    )

