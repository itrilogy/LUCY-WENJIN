# -*- coding: utf-8 -*-
"""百度开放数据 · 一分一段 API（opendata.baidu.com resource_id=50266）

接口契约（社区脚本 School-Robot/YiFenYiDuan 与实测一致）::

    GET https://opendata.baidu.com/api.php
      fromCard=1
      resource_id=50266
      province=江西
      year=2025
      category=物理类
      query=一分一段

返回 tplData.segmentInfo[].segList[] 字段：
  minScore/maxScore, minOrder/maxOrder, num, surpass, tips

说明：此接口属于百度开放数据/高考卡片数据，非 gaokao.baidu.com/gk/* 学校库接口，
但同源生态，项目内作为「官方一分一段」主数据源。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import requests

API_URL = "https://opendata.baidu.com/api.php"
RESOURCE_ID = 50266

# 江西历年科类
JIANGXI_YEARS: List[Tuple[str, List[str]]] = [
    ("2026", ["物理类", "历史类"]),
    ("2025", ["物理类", "历史类"]),
    ("2024", ["物理类", "历史类"]),
    ("2023", ["理科", "文科"]),
    ("2022", ["理科", "文科"]),
    ("2021", ["理科", "文科"]),
]


def fetch_raw(
    province: str, year: str, category: str, timeout: int = 25
) -> Optional[Dict[str, Any]]:
    params = {
        "fromCard": 1,
        "resource_id": RESOURCE_ID,
        "province": province,
        "year": str(year),
        "category": category,
        "query": "一分一段",
    }
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(API_URL, params=params, timeout=timeout, verify=False)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"一分一段请求失败 {province} {year} {category}: {last_err}")


def parse_segment_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """解析 API JSON → {batchline, rows:[{score,rank_min,rank_max,count,surpass,tips}]}"""
    result = data.get("Result") or []
    if not result:
        return {"batchline": [], "rows": [], "ok": False}

    tpl = (
        result[0]
        .get("DisplayData", {})
        .get("resultData", {})
        .get("tplData", {})
    )
    batchline = tpl.get("batchline") or []
    by_score: Dict[int, Dict[str, Any]] = {}

    for block in tpl.get("segmentInfo") or []:
        for s in block.get("segList") or []:
            try:
                sc = int(float(s.get("minScore") or s.get("maxScore") or 0))
            except (TypeError, ValueError):
                continue
            mo, xo = s.get("minOrder"), s.get("maxOrder")
            if mo in (None, "", "-") or xo in (None, "", "-"):
                continue
            try:
                rmin = int(str(mo).replace(",", ""))
                rmax = int(str(xo).replace(",", ""))
            except ValueError:
                continue
            if rmin > rmax:
                rmin, rmax = rmax, rmin
            num = 0
            try:
                num = int(s.get("num") or 0)
            except (TypeError, ValueError):
                pass
            # 同一分数多块重复时保留 num 更大的
            prev = by_score.get(sc)
            if prev is None or num >= (prev.get("count") or 0):
                by_score[sc] = {
                    "score": sc,
                    "rank_min": rmin,
                    "rank_max": rmax,
                    "count": num,
                    "surpass": s.get("surpass") or "",
                    "tips": s.get("tips") or "",
                }

    rows = [by_score[k] for k in sorted(by_score.keys(), reverse=True)]
    return {"batchline": batchline, "rows": rows, "ok": bool(rows), "tpl_keys": list(tpl.keys())}


def fetch_segment(
    province: str = "江西", year: str = "2025", category: str = "物理类"
) -> Dict[str, Any]:
    raw = fetch_raw(province, year, category)
    parsed = parse_segment_response(raw)
    parsed["province"] = province
    parsed["year"] = str(year)
    parsed["category"] = category
    return parsed
