# -*- coding: utf-8 -*-
"""志愿推荐引擎 v3：批量预加载 + 选科修正 + 可配置年份。"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence

from core.config import (
    DEFAULT_AGGRESSIVENESS,
    DEFAULT_RANK_FILTER_WIDTH,
    DEFAULT_SAFETY,
    LAST_PLAN_YEAR,
    PLAN_YEAR,
    SCORE_YEAR,
)
from core.db import query
from core.recommend.clusters import expand_keywords, match_major_keywords
from core.recommend.probability import estimate_admit_prob
from core.recommend.scoring import (
    calc_major_score,
    calc_plan_score,
    calc_rank_score,
    calc_tag_score,
    safe_int,
)
from core.recommend.subjects import match_select_subjects


def strip_major_suffix(name: str) -> str:
    if not name:
        return name
    idx = name.find("（")
    if idx < 0:
        idx = name.find("(")
    return name[:idx] if idx > 0 else name


def run_recommend(data: Dict[str, Any]) -> Dict[str, Any]:
    """执行推荐，返回 dict；错误时含 error 键。"""
    score = int(data.get("score") or 0)
    rank = int(data.get("rank") or 0)
    if score <= 0 or rank <= 0:
        return {"error": "请提供有效的分数和位次"}

    first_subj = data.get("firstSubject") or "物理"
    second_subjs: List[str] = list(data.get("secondSubjects") or [])
    keywords_raw = data.get("freeMajor") or ""
    keywords_user = [k.strip() for k in re.split(r"[,，]", keywords_raw) if k.strip()]
    use_cluster = data.get("useCluster", True)
    if isinstance(use_cluster, str):
        use_cluster = use_cluster.lower() not in ("0", "false", "no")
    keywords = expand_keywords(keywords_user) if use_cluster else list(keywords_user)
    keyword_mode = data.get("freeMajorMode") or "optional"
    tag_mode = data.get("tagMode") or "or"
    tags_filter = list(data.get("tags") or [])
    provinces_filter = list(data.get("provinces") or [])
    use_plan = data.get("usePlan", True)
    if isinstance(use_plan, str):
        use_plan = use_plan.lower() not in ("0", "false", "no")
    aggr = float(data.get("aggressiveness", DEFAULT_AGGRESSIVENESS))
    safety = float(data.get("safety", DEFAULT_SAFETY))
    rank_filter_width = float(data.get("rankFilterWidth", DEFAULT_RANK_FILTER_WIDTH))

    curriculum = "物理类" if first_subj == "物理" else "历史类"
    drift = 0.05 + aggr / 100 * 0.15

    score_year = str(data.get("scoreYear") or SCORE_YEAR)
    plan_year = str(data.get("planYear") or PLAN_YEAR)
    last_year = str(data.get("lastPlanYear") or LAST_PLAN_YEAR)

    schools_sql = """
        SELECT c.college_name, c.uniqueRank, c.province, c.tag,
               MIN(s.minScoreOrder) as minScoreOrder,
               MIN(s.minScore) as minScore
        FROM college_info c
        JOIN schoolscore s ON c.college_name = s.legalName
        WHERE s.year=? AND s.curriculum=? AND s.minScoreOrder!=''
    """
    schools_params: List[Any] = [score_year, curriculum]
    if provinces_filter:
        placeholders = ",".join(["?"] * len(provinces_filter))
        schools_sql += f" AND c.province IN ({placeholders})"
        schools_params.extend(provinces_filter)
    schools_sql += " GROUP BY c.college_name ORDER BY cast(c.uniqueRank AS int)"
    schools = query(schools_sql, schools_params)

    if not schools:
        return {"error": f"无 {score_year} 年 {curriculum} 录取数据"}

    if tags_filter and tag_mode == "and":
        schools = [
            s for s in schools if all(t in (s.get("tag") or "") for t in tags_filter)
        ]

    all_plans = query(
        """
        SELECT legalName, major_name, selectSubjects, enroll_num
        FROM college_plan WHERE year=? AND curriculum=?
        """,
        (plan_year, curriculum),
    )
    all_ms = query(
        """
        SELECT legalName, majorName, minScore, minScoreOrder
        FROM majorscore WHERE year=? AND curriculum=?
        AND minScore!='' AND minScoreOrder!=''
        """,
        (score_year, curriculum),
    )
    last_plans = query(
        """
        SELECT legalName, major_name, enroll_num
        FROM college_plan WHERE year=? AND curriculum=?
        """,
        (last_year, curriculum),
    )
    school_avg_ms = query(
        """
        SELECT legalName,
               avg(cast(minScore AS int)) as avgScore,
               avg(cast(minScoreOrder AS int)) as avgRank
        FROM majorscore WHERE year=? AND curriculum=?
        AND minScore!='' AND minScoreOrder!=''
        GROUP BY legalName
        """,
        (score_year, curriculum),
    )
    school_avg_plan = query(
        """
        SELECT legalName, avg(cast(enroll_num AS int)) as avgPlan
        FROM college_plan WHERE year=?
        GROUP BY legalName
        """,
        (plan_year,),
    )

    ms_idx: dict = defaultdict(lambda: defaultdict(list))
    for m in all_ms:
        base = strip_major_suffix(m["majorName"])
        ms_idx[m["legalName"]][base].append(m)
        ms_idx[m["legalName"]][m["majorName"]].append(m)

    plans_idx: dict = defaultdict(list)
    for p in all_plans:
        school = p["legalName"]
        pname = p["major_name"]
        matched = None
        school_ms = ms_idx.get(school, {})
        if pname in school_ms:
            matched = school_ms[pname]
        else:
            base = strip_major_suffix(pname)
            if base in school_ms:
                matched = school_ms[base]
            else:
                for ms_name, ms_list in school_ms.items():
                    if ms_name.startswith(pname) or pname.startswith(ms_name):
                        matched = ms_list
                        break
        if matched:
            best = min(
                matched,
                key=lambda m: safe_int(m["minScoreOrder"]),
            )
            p["minScore"] = best["minScore"]
            p["minScoreOrder"] = best["minScoreOrder"]
        else:
            p["minScore"] = None
            p["minScoreOrder"] = None
        plans_idx[school].append(p)

    last_plan_idx = {
        (lp["legalName"], lp["major_name"]): lp["enroll_num"] for lp in last_plans
    }
    avg_ms_idx = {a["legalName"]: a for a in school_avg_ms}
    avg_plan_idx = {a["legalName"]: a for a in school_avg_plan}

    result: Dict[str, Any] = {
        "year": score_year,
        "planYear": plan_year,
        "curriculum": curriculum,
        "aggressiveness": aggr,
        "safety": safety,
        "rankFilterWidth": rank_filter_width,
        "reach": [],
        "match": [],
        "safe": [],
    }

    for s in schools:
        tag_score = calc_tag_score(s.get("tag", ""), tags_filter, tag_mode)
        if tag_score < 0:
            continue

        for pm in plans_idx.get(s["college_name"], []):
            if not match_select_subjects(
                pm.get("selectSubjects") or "", first_subj, second_subjs
            ):
                continue

            ms_ref_score = pm.get("minScore")
            ms_ref_rank = pm.get("minScoreOrder")
            if ms_ref_score is not None:
                ref_score = ms_ref_score
                ref_rank = ms_ref_rank
                is_new = False
            else:
                avg_rec = avg_ms_idx.get(s["college_name"])
                if avg_rec and avg_rec["avgScore"] is not None:
                    ref_score = str(int(round(avg_rec["avgScore"])))
                    ref_rank = str(int(round(avg_rec["avgRank"])))
                    is_new = True
                else:
                    ref_score = s.get("minScore", "")
                    ref_rank = s.get("minScoreOrder", "")
                    is_new = True

            keyword_hit = match_major_keywords(pm["major_name"] or "", keywords)
            if keyword_mode == "mandatory" and keywords and not keyword_hit:
                continue

            enroll_this = pm.get("enroll_num")
            enroll_last = last_plan_idx.get((s["college_name"], pm["major_name"]))

            major_rank_val = safe_int(ref_rank)
            major_ratio = (
                major_rank_val / rank if rank > 0 and ref_rank else 0.0
            )

            plan_count = None
            plan_trend = 0
            last_n = None
            if use_plan:
                try:
                    plan_count = int(float(enroll_this)) if enroll_this else None
                except Exception:
                    plan_count = None
                if plan_count is not None:
                    try:
                        last_n = int(float(enroll_last)) if enroll_last else None
                        if last_n is not None and last_n > 0:
                            ratio = plan_count / last_n
                            if ratio > 1.2:
                                plan_trend = 2
                            elif ratio < 0.8:
                                plan_trend = -2
                        elif last_n is None:
                            plan_trend = 2
                    except Exception:
                        pass
                else:
                    avg_rec = avg_plan_idx.get(s["college_name"])
                    if avg_rec and avg_rec["avgPlan"] is not None:
                        plan_count = int(round(avg_rec["avgPlan"]))

            rank_score = calc_rank_score(major_ratio, drift, rank_filter_width)
            lo = 1 - drift * rank_filter_width
            hi = 1 + drift * rank_filter_width
            if rank_score == 0 and (major_ratio < lo or major_ratio > hi):
                continue

            major_score = calc_major_score(
                {
                    "keyword_hit": keyword_hit,
                    "major_ratio": major_ratio,
                    "subject_matched": True,
                },
                " ".join(keywords_user) if keywords_user else "",
                keyword_mode,
                drift,
                major_ratio,
            )
            if major_score < 0:
                continue

            plan_score = calc_plan_score(plan_count) + plan_trend
            total = rank_score + tag_score + major_score + max(0.0, plan_score)

            admit = estimate_admit_prob(
                rank,
                major_rank_val,
                plan_this=float(plan_count) if plan_count else None,
                plan_last=float(last_n) if last_n else None,
                is_new_major=is_new,
                school=s["college_name"],
                curriculum=curriculum,
                use_calibration=True,
            )

            item = {
                "school": s["college_name"],
                "uniqueRank": s["uniqueRank"] or "-",
                "province": s["province"],
                "tag": s["tag"],
                "majorName": pm["major_name"] + (" ⚠️" if is_new else ""),
                "majorScore": ref_score,
                "majorRank": ref_rank,
                "ratio": round(major_ratio, 4),
                "planCount": plan_count,
                "planThisYear": enroll_this if enroll_this else "-",
                "planLastYear": enroll_last if enroll_last else "-",
                "selectSubjects": pm.get("selectSubjects") or "",
                "keywordHit": keyword_hit,
                "admit": admit,
                "scores": {
                    "rankScore": round(rank_score, 1),
                    "tagScore": round(tag_score, 1),
                    "majorScore": round(major_score, 1),
                    "planScore": round(plan_score, 1),
                    "total": round(total, 1),
                },
            }

            safe_factor = 1.0 + safety / 100 * 4.0
            match_upper = rank * (1.0 + safety / 100 * 2.0)
            safe_upper = rank * safe_factor

            if major_rank_val < rank:
                tier_key = "reach"
            elif major_rank_val < match_upper:
                tier_key = "match"
            elif major_rank_val < safe_upper:
                tier_key = "safe"
            else:
                continue
            result[tier_key].append(item)

    sort_by = (data.get("sortBy") or "score").lower()
    for k in ("reach", "match", "safe"):
        if sort_by == "prob":
            result[k] = sorted(
                result[k],
                key=lambda x: (
                    -float((x.get("admit") or {}).get("prob") or 0),
                    -x["scores"]["total"],
                ),
            )[:30]
        else:
            result[k] = sorted(result[k], key=lambda x: -x["scores"]["total"])[:30]

    result["keywordsExpanded"] = keywords if keywords_user else []
    result["keywordsUser"] = keywords_user
    result["probModel"] = "logistic_v1"
    return result
