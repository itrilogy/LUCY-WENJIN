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


def init_schema(conn: sqlite3.Connection) -> None:
    """确认核心表与索引结构存在（具备新环境自愈能力）。"""
    ddl_statements = [
        """CREATE TABLE IF NOT EXISTS college_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            logourl TEXT, college_name TEXT, rankTypeShow TEXT,
            rankType TEXT, rank TEXT, globalRank TEXT, uniqueRank TEXT,
            province TEXT, city TEXT, location TEXT, school_type TEXT,
            education TEXT, nature TEXT, batch TEXT, score_city TEXT,
            score_list TEXT, tag TEXT, logo BLOB
        )""",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_college_info_name ON college_info(college_name)",
        """CREATE TABLE IF NOT EXISTS college_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id TEXT, name TEXT, detail TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS schoolscore (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legalName TEXT, province TEXT, year TEXT, curriculum TEXT,
            batchName TEXT, enrollType TEXT, minScore TEXT,
            minScoreOrder TEXT, minCha TEXT, enrollNum TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_schoolscore_lookup ON schoolscore(legalName, province, year, curriculum)",
        """CREATE TABLE IF NOT EXISTS majorscore (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legalName TEXT, majorName TEXT, province TEXT, year TEXT,
            curriculum TEXT, batchName TEXT, tags TEXT, minScore TEXT,
            minScoreOrder TEXT, simpleMajorName TEXT, majorNameDesc TEXT,
            simplifySpecialCourse TEXT, specialCourse TEXT, majorGroup TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_majorscore_lookup ON majorscore(legalName, majorName, year, curriculum)",
        """CREATE TABLE IF NOT EXISTS college_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legalName TEXT, major_name TEXT, province TEXT,
            curriculum TEXT, category TEXT, year TEXT, batch_name TEXT,
            enroll_num TEXT, tuition TEXT, lengthOfSchooling TEXT,
            selectSubjects TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_college_plan_lookup ON college_plan(legalName, major_name, year, curriculum)",
        """CREATE TABLE IF NOT EXISTS crawl_skip (
            school_name TEXT,
            year TEXT,
            curriculum TEXT,
            table_name TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (school_name, year, curriculum, table_name)
        )""",
        """CREATE TABLE IF NOT EXISTS shortlist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            school TEXT NOT NULL,
            major TEXT NOT NULL,
            rank TEXT,
            score TEXT,
            tier TEXT,
            prob TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, school, major)
        )""",
        """CREATE TABLE IF NOT EXISTS official_rank_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province TEXT NOT NULL,
            year TEXT NOT NULL,
            curriculum TEXT NOT NULL,
            score INTEGER NOT NULL,
            rank_segment INTEGER NOT NULL,
            rank_accum INTEGER NOT NULL,
            source TEXT DEFAULT 'baidu',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(province, year, curriculum, score)
        )""",
        """CREATE TABLE IF NOT EXISTS prob_calibration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            province TEXT NOT NULL,
            curriculum TEXT NOT NULL,
            k REAL NOT NULL,
            bias REAL NOT NULL,
            sigma REAL NOT NULL,
            n_samples INTEGER NOT NULL,
            fit_samples INTEGER NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(province, curriculum)
        )""",
    ]
    for ddl in ddl_statements:
        conn.execute(ddl)


def get_conn(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """进程内单例连接；爬虫与 Web 共用。初次连接自动初始化 DDL 与数据恢复。"""
    global _conn
    p = Path(db_path or DB_PATH)
    with _lock:
        if _conn is None:
            # 若 SQLite 文件不存在或为空，但存在同名 .gz 压缩包，自动解压还原
            gz_path = p.with_name(p.name + ".gz")
            if (not p.exists() or p.stat().st_size == 0) and gz_path.exists():
                import gzip
                import shutil
                tmp_extract = p.with_suffix(".tmp_restore")
                try:
                    with gzip.open(gz_path, "rb") as f_in, open(tmp_extract, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    tmp_extract.replace(p)
                except Exception as exc:
                    if tmp_extract.exists():
                        tmp_extract.unlink()
                    raise RuntimeError(f"自动解压数据库压缩包 {gz_path} 失败: {exc}") from exc

            _conn = sqlite3.connect(
                str(p),
                timeout=30,
                check_same_thread=False,
                isolation_level=None,  # autocommit，兼容爬虫事务
            )
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode=WAL")
            _conn.execute("PRAGMA synchronous=NORMAL")
            _conn.execute("PRAGMA foreign_keys=ON")
            init_schema(_conn)
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
