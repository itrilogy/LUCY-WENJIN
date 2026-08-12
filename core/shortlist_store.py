# -*- coding: utf-8 -*-
"""云端备选志愿表（按 session_id 存 SQLite）。"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from core.db import execute, query

DDL = """
CREATE TABLE IF NOT EXISTS user_shortlist (
    session_id TEXT NOT NULL,
    item_key TEXT NOT NULL,
    school TEXT,
    major TEXT,
    rank TEXT,
    score TEXT,
    tier TEXT,
    meta TEXT,
    created_at REAL,
    PRIMARY KEY (session_id, item_key)
)
"""


def ensure_table() -> None:
    execute(DDL)


def new_session_id() -> str:
    return uuid.uuid4().hex


def list_items(session_id: str) -> List[Dict[str, Any]]:
    ensure_table()
    rows = query(
        """
        SELECT item_key as key, school, major, rank, score, tier, meta, created_at
        FROM user_shortlist WHERE session_id=?
        ORDER BY created_at ASC
        """,
        (session_id,),
    )
    out = []
    for r in rows:
        item = dict(r)
        if item.get("meta"):
            try:
                item["meta"] = json.loads(item["meta"])
            except Exception:
                pass
        if item.get("created_at"):
            item["time"] = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(item["created_at"])
            )
        out.append(item)
    return out


def add_item(session_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
    ensure_table()
    key = item.get("key") or f"{item.get('school','')}|{item.get('major','')}"
    meta = item.get("meta")
    meta_s = json.dumps(meta, ensure_ascii=False) if meta is not None else None
    execute(
        """
        INSERT OR REPLACE INTO user_shortlist
        (session_id, item_key, school, major, rank, score, tier, meta, created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            session_id,
            key,
            item.get("school"),
            item.get("major"),
            str(item.get("rank") or ""),
            str(item.get("score") or ""),
            item.get("tier") or "",
            meta_s,
            time.time(),
        ),
    )
    return {"ok": True, "key": key}


def remove_item(session_id: str, key: str) -> None:
    ensure_table()
    execute(
        "DELETE FROM user_shortlist WHERE session_id=? AND item_key=?",
        (session_id, key),
    )


def clear_items(session_id: str) -> None:
    ensure_table()
    execute("DELETE FROM user_shortlist WHERE session_id=?", (session_id,))


def replace_all(session_id: str, items: List[Dict[str, Any]]) -> int:
    clear_items(session_id)
    for it in items:
        add_item(session_id, it)
    return len(items)


def to_csv(session_id: str) -> str:
    items = list_items(session_id)
    lines = ["学校,专业,位次,总分,档位,时间"]
    for x in items:
        tier = {"reach": "冲刺", "match": "稳健", "safe": "保底"}.get(
            x.get("tier") or "", x.get("tier") or ""
        )
        lines.append(
            ",".join(
                [
                    _csv(x.get("school")),
                    _csv(x.get("major")),
                    _csv(x.get("rank")),
                    _csv(x.get("score")),
                    _csv(tier),
                    _csv(x.get("time")),
                ]
            )
        )
    return "\n".join(lines) + "\n"


def _csv(v: Any) -> str:
    s = str(v or "").replace('"', '""')
    if "," in s or '"' in s or "\n" in s:
        return f'"{s}"'
    return s
