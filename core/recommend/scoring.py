# -*- coding: utf-8 -*-
"""推荐评分项。"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence

from core.config import TAG_AND_SCORE, TAG_OR_CAP, TAG_POINTS


def calc_rank_score(ratio: float, drift: float, width: float = 3.0) -> float:
    """位次匹配分 0~40。"""
    if ratio < 1 - drift * width or ratio > 1 + drift * width:
        return 0.0
    base = 40 * (1 - abs(ratio - 1) / drift) if drift > 0 else 40
    return max(0.0, min(40.0, base))


def calc_tag_score(
    tag_str: Optional[str], tags_filter: Sequence[str], tag_mode: str
) -> float:
    """标签分：OR 0~25；AND 满足得 15，不满足返回 -1。"""
    if not tags_filter:
        return 0.0
    tag_str = tag_str or ""
    if tag_mode == "and":
        if all(t in tag_str for t in tags_filter):
            return float(TAG_AND_SCORE)
        return -1.0
    score = sum(TAG_POINTS.get(t, 0) for t in tags_filter if t in tag_str)
    return float(min(TAG_OR_CAP, score))


def calc_major_score(
    matched: Dict[str, Any],
    keyword: str,
    keyword_mode: str,
    drift: float,
    ratio: float = 0.0,
) -> float:
    """专业匹配分 0~20；强制未命中返回 -1。"""
    if not matched:
        return 0.0
    if keyword:
        if keyword_mode == "mandatory" and not matched.get("keyword_hit"):
            return -1.0
        if matched.get("keyword_hit"):
            r = matched.get("major_ratio", ratio)
            if abs(r - 1) <= drift:
                return 20.0
            if abs(r - 1) <= drift * 2:
                return 12.0
            return 5.0
    return 8.0 if matched.get("subject_matched") else 0.0


def calc_plan_score(plan_count: Optional[float]) -> float:
    """计划分 0~15。"""
    if plan_count is None or plan_count <= 0:
        return 0.0
    return min(15.0, math.log2(max(plan_count, 1)) * 3)


def safe_int(r: Any, default: int = 999999) -> int:
    try:
        return int(float(str(r).replace(",", "")))
    except Exception:
        return default
