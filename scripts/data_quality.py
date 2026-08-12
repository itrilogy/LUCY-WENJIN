#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据质量检查：覆盖率、选科枚举、plan/major 对齐、唯一键风险。"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.config import PLAN_YEAR, SCORE_YEAR
from core.db import query


def main():
    report = {"scoreYear": SCORE_YEAR, "planYear": PLAN_YEAR, "checks": []}

    def add(name, ok, detail):
        report["checks"].append({"name": name, "ok": ok, "detail": detail})
        mark = "✓" if ok else "✗"
        print(f"[{mark}] {name}: {detail}")

    # 行数
    counts = {
        t: query(f"SELECT count(1) c FROM {t}")[0]["c"]
        for t in (
            "college_info",
            "schoolscore",
            "majorscore",
            "college_plan",
            "crawl_skip",
        )
    }
    add("row_counts", True, counts)

    # 年份分布
    for table, col in (
        ("schoolscore", "year"),
        ("majorscore", "year"),
        ("college_plan", "year"),
    ):
        dist = query(
            f"SELECT {col} y, curriculum, count(1) n FROM {table} GROUP BY {col}, curriculum ORDER BY {col}"
        )
        add(f"{table}_year_curriculum", True, dist)

    # selectSubjects 枚举
    ss = query(
        f"""
        SELECT selectSubjects, count(1) n FROM college_plan
        WHERE year=? GROUP BY selectSubjects ORDER BY n DESC LIMIT 30
        """,
        (PLAN_YEAR,),
    )
    add("selectSubjects_top", True, ss)
    known_problem = any(
        (r["selectSubjects"] or "").endswith("+不限") or "(" in (r["selectSubjects"] or "")
        for r in ss
    )
    add(
        "selectSubjects_has_buxian_or_paren",
        True,
        "存在 物+不限 / 括号组合，推荐引擎必须正确解析" if known_problem else "无",
    )

    # 覆盖
    plan_schools = query(
        "SELECT count(DISTINCT legalName) c FROM college_plan WHERE year=?",
        (PLAN_YEAR,),
    )[0]["c"]
    score_schools = query(
        "SELECT count(DISTINCT legalName) c FROM schoolscore WHERE year=?",
        (SCORE_YEAR,),
    )[0]["c"]
    orphan = query(
        """
        SELECT count(DISTINCT p.legalName) c FROM college_plan p
        WHERE p.year=? AND NOT EXISTS (
          SELECT 1 FROM schoolscore s WHERE s.legalName=p.legalName AND s.year=?
        )
        """,
        (PLAN_YEAR, SCORE_YEAR),
    )[0]["c"]
    add(
        "coverage_plan_vs_score",
        orphan < plan_schools * 0.2,
        {
            "plan_schools": plan_schools,
            "score_schools": score_schools,
            "plan_without_score": orphan,
        },
    )

    # 空位次
    empty_ms = query(
        "SELECT count(1) c FROM majorscore WHERE year=? AND (minScoreOrder='' OR minScoreOrder IS NULL)",
        (SCORE_YEAR,),
    )[0]["c"]
    total_ms = query(
        "SELECT count(1) c FROM majorscore WHERE year=?", (SCORE_YEAR,)
    )[0]["c"]
    add(
        "empty_major_rank",
        empty_ms / max(total_ms, 1) < 0.15,
        {"empty": empty_ms, "total": total_ms},
    )

    # plan 唯一键不含 curriculum 的冲突风险
    conflicts = query(
        """
        SELECT legalName, major_name, province, year, batch_name, count(DISTINCT curriculum) cc
        FROM college_plan
        GROUP BY legalName, major_name, province, year, batch_name
        HAVING cc > 1
        LIMIT 20
        """
    )
    add(
        "plan_unique_key_curriculum_risk",
        len(conflicts) == 0,
        {"sample": conflicts, "count_shown": len(conflicts)},
    )

    # 抽样对齐率：南昌大学
    school = "南昌大学"
    plans = query(
        "SELECT major_name FROM college_plan WHERE legalName=? AND year=? AND curriculum=?",
        (school, PLAN_YEAR, "物理类"),
    )
    majors = query(
        "SELECT majorName FROM majorscore WHERE legalName=? AND year=? AND curriculum=?",
        (school, SCORE_YEAR, "物理类"),
    )
    ms_set = {m["majorName"] for m in majors}

    def base(n):
        i = n.find("（")
        return n[:i] if i > 0 else n

    ms_base = {base(m["majorName"]) for m in majors}
    exact = sum(1 for p in plans if p["major_name"] in ms_set)
    fuzzy = sum(
        1
        for p in plans
        if p["major_name"] in ms_set
        or base(p["major_name"]) in ms_base
        or any(
            m["majorName"].startswith(p["major_name"])
            or p["major_name"].startswith(m["majorName"])
            for m in majors
        )
    )
    add(
        "name_match_nanchang",
        True,
        {
            "plans": len(plans),
            "majors": len(majors),
            "exact": exact,
            "fuzzy": fuzzy,
            "exact_rate": round(exact / max(len(plans), 1), 3),
            "fuzzy_rate": round(fuzzy / max(len(plans), 1), 3),
        },
    )

    out = os.path.join(ROOT, "scripts", "data_quality_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已写入 {out}")
    failed = [c for c in report["checks"] if not c["ok"]]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
