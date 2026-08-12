# -*- coding: utf-8 -*-
"""统一 SQLite 访问（单连接 + 参数化查询）。"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence, Union

from core.config import DB_PATH

_lock = threading.RLock()
_conn: Optional[sqlite3.Connection] = None


def get_db_path() -> Path:
    return Path(DB_PATH)


def get_conn(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """进程内单例连接；爬虫与 Web 共用。"""
    global _conn
    path = str(db_path or DB_PATH)
    with _lock:
        if _conn is None:
            _conn = sqlite3.connect(
                path,
                timeout=30,
                check_same_thread=False,
                isolation_level=None,  # autocommit，兼容爬虫事务
            )
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode=WAL")
            _conn.execute("PRAGMA synchronous=NORMAL")
            _conn.execute("PRAGMA foreign_keys=ON")
        return _conn


def reset_conn() -> None:
    """测试或切换库时关闭单例。"""
    global _conn
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None


def query(sql: str, params: Sequence[Any] = ()) -> list[dict]:
    conn = get_conn()
    with _lock:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def execute(sql: str, params: Sequence[Any] = ()) -> None:
    conn = get_conn()
    with _lock:
        conn.execute(sql, params)


def executemany(sql: str, seq_of_params: Iterable[Sequence[Any]]) -> None:
    conn = get_conn()
    with _lock:
        conn.executemany(sql, list(seq_of_params))


def query_tuples(sql: str, params: Sequence[Any] = ()) -> list[tuple]:
    """返回 tuple 行（兼容旧爬虫代码习惯）。"""
    conn = get_conn()
    with _lock:
        # 临时不用 Row，保证 tuple
        cur = conn.cursor()
        cur.row_factory = None
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
