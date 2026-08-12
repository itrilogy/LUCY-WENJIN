# -*- coding: utf-8 -*-
"""一分一段表：优先百度官方卡片数据，回退 schoolscore 近似。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.config import PROVINCE_DEFAULT, SCORE_YEAR
from core.db import execute, query

DDL = """
CREATE TABLE IF NOT EXISTS score_segment (
    year TEXT NOT NULL,
    curriculum TEXT NOT NULL,
    score INTEGER NOT NULL,
    rank_min INTEGER NOT NULL,
    rank_max INTEGER,
    count INTEGER,
    source TEXT DEFAULT 'approx',
    surpass TEXT,
    tips TEXT,
    PRIMARY KEY (year, curriculum, score, source)
)
"""

DDL_BATCH = """
CREATE TABLE IF NOT EXISTS score_batchline (
    year TEXT NOT NULL,
    curriculum TEXT NOT NULL,
    batch_name TEXT NOT NULL,
    score INTEGER,
    source TEXT DEFAULT 'baidu',
    PRIMARY KEY (year, curriculum, batch_name)
)
"""


def ensure_table() -> None:
    execute(DDL)
    execute(DDL_BATCH)
    # 兼容旧库：补列
    for col, typ in (("surpass", "TEXT"), ("tips", "TEXT")):
        try:
            execute(f"ALTER TABLE score_segment ADD COLUMN {col} {typ}")
        except Exception:
            pass


def clear_source(year: str, curriculum: str, source: str = "baidu") -> None:
    ensure_table()
    execute(
        "DELETE FROM score_segment WHERE year=? AND curriculum=? AND source=?",
        (year, curriculum, source),
    )
    execute(
        "DELETE FROM score_batchline WHERE year=? AND curriculum=? AND source=?",
        (year, curriculum, source),
    )


def ensure_schema_v2() -> None:
    """确保 PK 含 source，避免 approx 覆盖 baidu。"""
    ensure_table()
    rows = query(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='score_segment'"
    )
    sql = (rows[0]["sql"] or "") if rows else ""
    if "score, source" in sql.replace(" ", "") or "score,source" in sql.replace(" ", ""):
        return
    if "PRIMARY KEY (year, curriculum, score)" not in sql and "PRIMARY KEY(year, curriculum, score)" not in sql.replace(
        " ", ""
    ):
        # 已是其他形式
        if "source)" in sql.replace(" ", ""):
            return
    execute(
        """
        CREATE TABLE IF NOT EXISTS score_segment_v2 (
            year TEXT NOT NULL,
            curriculum TEXT NOT NULL,
            score INTEGER NOT NULL,
            rank_min INTEGER NOT NULL,
            rank_max INTEGER,
            count INTEGER,
            source TEXT DEFAULT 'approx',
            surpass TEXT,
            tips TEXT,
            PRIMARY KEY (year, curriculum, score, source)
        )
        """
    )
    execute(
        """
        INSERT OR IGNORE INTO score_segment_v2
        (year, curriculum, score, rank_min, rank_max, count, source, surpass, tips)
        SELECT year, curriculum, score, rank_min, rank_max, count,
               COALESCE(source,'approx'), COALESCE(surpass,''), COALESCE(tips,'')
        FROM score_segment
        """
    )
    execute("DROP TABLE score_segment")
    execute("ALTER TABLE score_segment_v2 RENAME TO score_segment")


def upsert_baidu_rows(
    year: str,
    curriculum: str,
    rows: List[Dict[str, Any]],
    batchline: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """写入百度一分一段（覆盖同年同科类 baidu 源，不碰 approx）。"""
    ensure_schema_v2()
    clear_source(year, curriculum, "baidu")
    n = 0
    for r in rows:
        execute(
            """
            INSERT OR REPLACE INTO score_segment
            (year, curriculum, score, rank_min, rank_max, count, source, surpass, tips)
            VALUES (?,?,?,?,?,?, 'baidu', ?, ?)
            """,
            (
                year,
                curriculum,
                int(r["score"]),
                int(r["rank_min"]),
                int(r.get("rank_max") or r["rank_min"]),
                int(r.get("count") or 0),
                r.get("surpass") or "",
                r.get("tips") or "",
            ),
        )
        n += 1
    if batchline:
        for b in batchline:
            try:
                sc = int(float(b.get("score") or 0))
            except (TypeError, ValueError):
                continue
            name = b.get("text") or b.get("name") or "批次线"
            execute(
                """
                INSERT OR REPLACE INTO score_batchline
                (year, curriculum, batch_name, score, source)
                VALUES (?,?,?,?, 'baidu')
                """,
                (year, curriculum, name, sc),
            )
    return n


def rebuild_approx_from_schoolscore(
    year: Optional[str] = None, curriculum: Optional[str] = None
) -> int:
    """用 schoolscore 按分数聚合生成近似一分一段（source=approx，不覆盖 baidu）。"""
    ensure_schema_v2()
    year = year or SCORE_YEAR
    curriculums = [curriculum] if curriculum else ["物理类", "历史类", "理科", "文科"]
    total = 0
    for cur in curriculums:
        rows = query(
            """
            SELECT cast(minScore AS int) AS score,
                   cast(minScoreOrder AS int) AS rk
            FROM schoolscore
            WHERE year=? AND curriculum=? AND province=?
              AND minScore!='' AND minScoreOrder!=''
              AND cast(minScore AS int) > 0
            """,
            (year, cur, PROVINCE_DEFAULT),
        )
        if not rows:
            continue
        bucket: Dict[int, List[int]] = {}
        for r in rows:
            sc, rk = r["score"], r["rk"]
            if sc is None or rk is None:
                continue
            bucket.setdefault(int(sc), []).append(int(rk))
        execute(
            "DELETE FROM score_segment WHERE year=? AND curriculum=? AND source='approx'",
            (year, cur),
        )
        for sc, ranks in bucket.items():
            ranks.sort()
            n = len(ranks)
            mid = ranks[n // 2]
            rmin, rmax = ranks[0], ranks[-1]
            execute(
                """
                INSERT OR REPLACE INTO score_segment
                (year, curriculum, score, rank_min, rank_max, count, source)
                VALUES (?,?,?,?,?,?, 'approx')
                """,
                (year, cur, sc, mid, rmax, n),
            )
            total += 1
    return total


def _pick_row(
    year: str, curriculum: str, score: Optional[int] = None, rank: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """优先 baidu 源，再 approx；先在 baidu 子集内找最近分/位次。"""
    ensure_schema_v2()

    def _q(source_first: bool):
        if score is not None:
            if source_first:
                # 仅 baidu
                return query(
                    """
                    SELECT score, rank_min, rank_max, count, source, surpass, tips
                    FROM score_segment
                    WHERE year=? AND curriculum=? AND source='baidu'
                    ORDER BY abs(score - ?) ASC
                    LIMIT 1
                    """,
                    (year, curriculum, score),
                )
            return query(
                """
                SELECT score, rank_min, rank_max, count, source, surpass, tips
                FROM score_segment
                WHERE year=? AND curriculum=?
                ORDER BY
                  CASE source WHEN 'baidu' THEN 0 ELSE 1 END,
                  abs(score - ?) ASC
                LIMIT 1
                """,
                (year, curriculum, score),
            )
        if rank is not None:
            if source_first:
                return query(
                    """
                    SELECT score, rank_min, rank_max, count, source, surpass, tips
                    FROM score_segment
                    WHERE year=? AND curriculum=? AND source='baidu'
                    ORDER BY abs((rank_min + COALESCE(rank_max, rank_min)) / 2.0 - ?) ASC
                    LIMIT 1
                    """,
                    (year, curriculum, rank),
                )
            return query(
                """
                SELECT score, rank_min, rank_max, count, source, surpass, tips
                FROM score_segment
                WHERE year=? AND curriculum=?
                ORDER BY
                  CASE source WHEN 'baidu' THEN 0 ELSE 1 END,
                  abs((rank_min + COALESCE(rank_max, rank_min)) / 2.0 - ?) ASC
                LIMIT 1
                """,
                (year, curriculum, rank),
            )
        return []

    rows = _q(True)
    if not rows:
        rows = _q(False)
    return rows[0] if rows else None


def score_to_rank(
    score: int, year: Optional[str] = None, curriculum: str = "物理类"
) -> Optional[Dict[str, Any]]:
    year = year or SCORE_YEAR
    r = _pick_row(year, curriculum, score=score)
    if not r:
        # 尝试拉百度 / 近似
        try:
            from core.baidu_segment import fetch_segment

            seg = fetch_segment(PROVINCE_DEFAULT, year, curriculum)
            if seg.get("ok"):
                upsert_baidu_rows(year, curriculum, seg["rows"], seg.get("batchline"))
                r = _pick_row(year, curriculum, score=score)
        except Exception:
            pass
    if not r:
        rebuild_approx_from_schoolscore(year, curriculum)
        r = _pick_row(year, curriculum, score=score)
    if not r:
        return None
    # 保守位次取本分最差位次 rank_max（同分最后一名）
    rank_report = r.get("rank_max") or r["rank_min"]
    return {
        "year": year,
        "curriculum": curriculum,
        "score": r["score"],
        "queryScore": score,
        "rank": rank_report,
        "rankMin": r["rank_min"],
        "rankMax": r.get("rank_max") or r["rank_min"],
        "source": r["source"],
        "sampleCount": r["count"],
        "surpass": r.get("surpass") or "",
    }


def rank_to_score(
    rank: int, year: Optional[str] = None, curriculum: str = "物理类"
) -> Optional[Dict[str, Any]]:
    year = year or SCORE_YEAR
    r = _pick_row(year, curriculum, rank=rank)
    if not r:
        try:
            from core.baidu_segment import fetch_segment

            seg = fetch_segment(PROVINCE_DEFAULT, year, curriculum)
            if seg.get("ok"):
                upsert_baidu_rows(year, curriculum, seg["rows"], seg.get("batchline"))
                r = _pick_row(year, curriculum, rank=rank)
        except Exception:
            rebuild_approx_from_schoolscore(year, curriculum)
            r = _pick_row(year, curriculum, rank=rank)
    if not r:
        return None
    return {
        "year": year,
        "curriculum": curriculum,
        "rank": rank,
        "score": r["score"],
        "matchedRankMin": r["rank_min"],
        "matchedRankMax": r.get("rank_max") or r["rank_min"],
        "source": r["source"],
    }


def convert_rank_across_years(
    rank: int,
    from_year: str,
    to_year: str,
    curriculum: str = "物理类",
) -> Optional[Dict[str, Any]]:
    """跨年位次换算：from 年 rank → 分数 → to 年等价位次（同位次优先用百度表）。"""
    # 科类名可能跨制度变化：2023 理科 ↔ 2024 物理类 需调用方指定
    mapped = rank_to_score(rank, from_year, curriculum)
    if not mapped:
        return None
    score = mapped["score"]
    to_map = score_to_rank(score, to_year, curriculum)
    if not to_map:
        return None
    return {
        "fromYear": from_year,
        "toYear": to_year,
        "curriculum": curriculum,
        "fromRank": rank,
        "equivScore": score,
        "toRank": to_map["rank"],
        "toRankMin": to_map.get("rankMin"),
        "toRankMax": to_map.get("rankMax"),
        "source": f"{mapped['source']}+{to_map['source']}",
        "note": "基于一分一段表的位次-分数-位次换算",
    }


def segment_stats(year: Optional[str] = None) -> List[Dict[str, Any]]:
    ensure_table()
    year = year or SCORE_YEAR
    return query(
        """
        SELECT year, curriculum, count(1) as n, min(score) as minScore,
               max(score) as maxScore, source
        FROM score_segment
        WHERE year=?
        GROUP BY year, curriculum, source
        """,
        (year,),
    )


def batch_lines(year: Optional[str] = None, curriculum: str = "物理类") -> List[Dict]:
    ensure_table()
    year = year or SCORE_YEAR
    return query(
        "SELECT batch_name, score, source FROM score_batchline WHERE year=? AND curriculum=?",
        (year, curriculum),
    )


def has_baidu(year: str, curriculum: str) -> bool:
    ensure_table()
    rows = query(
        "SELECT 1 FROM score_segment WHERE year=? AND curriculum=? AND source='baidu' LIMIT 1",
        (year, curriculum),
    )
    return bool(rows)
