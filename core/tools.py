# -*- coding: utf-8 -*-
"""AI / 内部可调用的查询工具。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.config import SCORE_YEAR
from core.db import query
from core.recommend import run_recommend
from core.recommend.probability import estimate_admit_prob
from core.recommend.scoring import safe_int


def search_major(
    major: str,
    year: Optional[str] = None,
    curriculum: Optional[str] = None,
    limit: int = 30,
) -> Dict[str, Any]:
    year = year or SCORE_YEAR
    sql = """
        SELECT year, legalName, majorName, specialCourse, minScore, minScoreOrder, batchName
        FROM majorscore
        WHERE majorName LIKE ? AND year=? AND minScoreOrder!=''
    """
    params: list = [f"%{major}%", year]
    if curriculum:
        sql += " AND curriculum=?"
        params.append(curriculum)
    sql += " ORDER BY cast(minScoreOrder AS int) ASC LIMIT ?"
    params.append(limit)
    rows = query(sql, params)
    return {"major": major, "year": year, "count": len(rows), "rows": rows}


def compare_schools(
    schools: List[str],
    year: Optional[str] = None,
    curriculum: str = "物理类",
) -> Dict[str, Any]:
    year = year or SCORE_YEAR
    result = []
    for name in schools[:8]:
        info = query(
            "SELECT college_name, uniqueRank, province, tag, school_type, nature "
            "FROM college_info WHERE college_name=?",
            (name,),
        )
        scores = query(
            """
            SELECT minScore, minScoreOrder, batchName, enrollType
            FROM schoolscore
            WHERE legalName=? AND year=? AND curriculum=? AND minScoreOrder!=''
            ORDER BY cast(minScoreOrder AS int) ASC LIMIT 5
            """,
            (name, year, curriculum),
        )
        majors = query(
            """
            SELECT majorName, minScore, minScoreOrder
            FROM majorscore
            WHERE legalName=? AND year=? AND curriculum=? AND minScoreOrder!=''
            ORDER BY cast(minScoreOrder AS int) ASC LIMIT 8
            """,
            (name, year, curriculum),
        )
        result.append(
            {
                "school": name,
                "info": info[0] if info else None,
                "scores": scores,
                "topMajors": majors,
            }
        )
    return {"year": year, "curriculum": curriculum, "schools": result}


def explain_admission(
    student_rank: int,
    major_rank: int,
    plan_this: Optional[float] = None,
    plan_last: Optional[float] = None,
    is_new: bool = False,
) -> Dict[str, Any]:
    adm = estimate_admit_prob(
        student_rank,
        major_rank,
        plan_this=plan_this,
        plan_last=plan_last,
        is_new_major=is_new,
    )
    return {
        "studentRank": student_rank,
        "majorRank": major_rank,
        "ratio": round(major_rank / student_rank, 4) if student_rank else None,
        "admit": adm,
        "disclaimer": "启发式估算，非官方录取概率",
    }


def tool_recommend(args: Dict[str, Any]) -> Dict[str, Any]:
    return run_recommend(args)


TOOL_HANDLERS = {
    "recommend": tool_recommend,
    "search_major": lambda a: search_major(
        a.get("major") or a.get("keyword") or "",
        a.get("year"),
        a.get("curriculum"),
        int(a.get("limit") or 30),
    ),
    "compare_schools": lambda a: compare_schools(
        list(a.get("schools") or []),
        a.get("year"),
        a.get("curriculum") or "物理类",
    ),
    "explain_admission": lambda a: explain_admission(
        int(a.get("studentRank") or a.get("rank") or 0),
        int(a.get("majorRank") or 0),
        a.get("planThis"),
        a.get("planLast"),
        bool(a.get("isNew")),
    ),
}


def dispatch_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    fn = TOOL_HANDLERS.get(name)
    if not fn:
        return {"error": f"未知工具: {name}"}
    try:
        return fn(args)
    except Exception as e:
        return {"error": str(e)}
