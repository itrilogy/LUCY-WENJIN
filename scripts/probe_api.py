#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度高考 API 轻量契约探针（单校单年，不落库）。"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

import requests

SCHOOL_SCORE = "https://gaokao.baidu.com/gk/gkschool/schoolscore?"
MAJOR_SCORE = (
    "https://gaokao.baidu.com/gk/gkschool/majorscore?"
    "rn=10&subject=&sortType&version=2&needFilter=1&"
)
PLAN = "https://gaokao.baidu.com/gk/gkschool/getrecruitingscheme?"
SCHOOL_LIST = "https://gaokao.baidu.com/gk/gkschool/list?rn=10&pn=1"


def _get(url: str, timeout: int = 20) -> Dict[str, Any]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def probe_school_list() -> Dict[str, Any]:
    data = _get(SCHOOL_LIST)
    ranking = (data.get("data") or {}).get("ranking") or {}
    page = (data.get("data") or {}).get("pageInfo") or {}
    rows = ranking.get("tRow") or []
    sample_keys = list(rows[0].keys()) if rows else []
    return {
        "endpoint": "school_list",
        "ok": data.get("errno", 0) == 0 or bool(rows),
        "total": page.get("total"),
        "sample_keys": sample_keys,
    }


def probe_score(school: str, province: str, year: str, curriculum: str) -> Dict[str, Any]:
    url = (
        f"{SCHOOL_SCORE}curriculum={curriculum}&school={school}"
        f"&province={province}&year={year}"
    )
    data = _get(url)
    lst = (
        ((data.get("data") or {}).get("school_score") or {}).get("dataList") or []
    )
    keys = list(lst[0].keys()) if lst else []
    return {
        "endpoint": "schoolscore",
        "ok": True,
        "count": len(lst),
        "sample_keys": keys,
        "errno": data.get("errno"),
    }


def probe_major(school: str, province: str, year: str, curriculum: str) -> Dict[str, Any]:
    url = (
        f"{MAJOR_SCORE}curriculum={curriculum}&school={school}"
        f"&province={province}&year={year}&pn=1"
    )
    data = _get(url)
    lst = (
        ((data.get("data") or {}).get("major_score") or {}).get("dataList") or []
    )
    keys = list(lst[0].keys()) if lst else []
    return {
        "endpoint": "majorscore",
        "ok": data.get("errno", 0) == 0,
        "count": len(lst),
        "sample_keys": keys,
        "errno": data.get("errno"),
    }


def probe_plan(school: str, province: str, year: str, curriculum: str) -> Dict[str, Any]:
    url = (
        f"{PLAN}curriculum={curriculum}&query={school}"
        f"&province={province}&year={year}&pn=0&rn=20"
    )
    data = _get(url)
    lst = (data.get("data") or {}).get("list") or []
    keys = list(lst[0].keys()) if lst else []
    return {
        "endpoint": "plan",
        "ok": data.get("errno", 0) == 0,
        "count": len(lst),
        "sample_keys": keys,
        "errno": data.get("errno"),
        "selectSubjects_sample": [
            x.get("selectSubjects") for x in lst[:5] if isinstance(x, dict)
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="百度高考 API 契约探针")
    ap.add_argument("--school", default="南昌大学")
    ap.add_argument("--province", default="江西")
    ap.add_argument("--year", default="2025")
    ap.add_argument("--plan-year", default="2026")
    ap.add_argument("--curriculum", default="物理类")
    args = ap.parse_args()

    results = []
    try:
        results.append(probe_school_list())
    except Exception as e:
        results.append({"endpoint": "school_list", "ok": False, "error": str(e)})

    for fn, year in (
        (probe_score, args.year),
        (probe_major, args.year),
        (probe_plan, args.plan_year),
    ):
        try:
            results.append(
                fn(args.school, args.province, year, args.curriculum)
            )
        except Exception as e:
            results.append(
                {"endpoint": fn.__name__, "ok": False, "error": str(e)}
            )

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
