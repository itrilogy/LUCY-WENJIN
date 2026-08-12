# -*- coding: utf-8 -*-
"""概率模型校准。

数据来源：
1. 一分一段（位次密度 → 局部位次波动）
2. majorscore 跨年同校同专业位次变化 → 经验波动 σ
3. 用历史「压线样本」拟合 logistic 斜率 k 与中心偏移

校准结果缓存于内存 + 可选 meta 表。
"""

from __future__ import annotations

import json
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from core.config import SCORE_YEAR
from core.db import execute, query
from core.recommend.scoring import safe_int

_CACHE: Dict[str, Any] = {}

META_DDL = """
CREATE TABLE IF NOT EXISTS model_meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at REAL
)
"""


def _ensure_meta():
    execute(META_DDL)


def save_meta(key: str, value: Any) -> None:
    _ensure_meta()
    execute(
        "INSERT OR REPLACE INTO model_meta(key, value, updated_at) VALUES (?,?,?)",
        (key, json.dumps(value, ensure_ascii=False), time.time()),
    )
    _CACHE[key] = value


def load_meta(key: str, default=None):
    if key in _CACHE:
        return _CACHE[key]
    _ensure_meta()
    rows = query("SELECT value FROM model_meta WHERE key=?", (key,))
    if not rows:
        return default
    try:
        val = json.loads(rows[0]["value"])
        _CACHE[key] = val
        return val
    except Exception:
        return default


def _strip_major(name: str) -> str:
    if not name:
        return name
    for ch in ("（", "("):
        i = name.find(ch)
        if i > 0:
            return name[:i]
    return name


def compute_yoy_volatility(
    year_a: str, year_b: str, curriculum: str = "物理类"
) -> Dict[str, Any]:
    """同校同专业 base 名跨年位次相对变化，估计全局 σ。"""
    a = query(
        """
        SELECT legalName, majorName, minScoreOrder
        FROM majorscore
        WHERE year=? AND curriculum=? AND minScoreOrder!='' AND minScore!=''
        """,
        (year_a, curriculum),
    )
    b = query(
        """
        SELECT legalName, majorName, minScoreOrder
        FROM majorscore
        WHERE year=? AND curriculum=? AND minScoreOrder!='' AND minScore!=''
        """,
        (year_b, curriculum),
    )
    idx_b: Dict[Tuple[str, str], int] = {}
    for r in b:
        key = (r["legalName"], _strip_major(r["majorName"]))
        rk = safe_int(r["minScoreOrder"], -1)
        if rk > 0:
            # 取最好位次
            if key not in idx_b or rk < idx_b[key]:
                idx_b[key] = rk

    rel_changes: List[float] = []
    school_vol: Dict[str, List[float]] = {}
    for r in a:
        key = (r["legalName"], _strip_major(r["majorName"]))
        ra = safe_int(r["minScoreOrder"], -1)
        rb = idx_b.get(key)
        if ra <= 0 or not rb or rb <= 0:
            continue
        # 相对变化
        rel = abs(rb - ra) / max(ra, rb)
        if rel > 2.0:  # 异常跳变忽略
            continue
        rel_changes.append(rel)
        school_vol.setdefault(r["legalName"], []).append(rel)

    if not rel_changes:
        return {
            "sigma": 0.10,
            "n": 0,
            "yearA": year_a,
            "yearB": year_b,
            "curriculum": curriculum,
        }

    # 中位数更稳
    rel_changes.sort()
    mid = rel_changes[len(rel_changes) // 2]
    mean = sum(rel_changes) / len(rel_changes)
    # 学校级
    school_sigma = {}
    for sch, vals in school_vol.items():
        if len(vals) < 2:
            continue
        vals = sorted(vals)
        school_sigma[sch] = round(vals[len(vals) // 2], 4)

    return {
        "sigma": round(max(0.05, min(0.25, mid)), 4),
        "sigmaMean": round(mean, 4),
        "n": len(rel_changes),
        "yearA": year_a,
        "yearB": year_b,
        "curriculum": curriculum,
        "schoolSigma": school_sigma,
        "p75": round(rel_changes[int(len(rel_changes) * 0.75)], 4),
    }


def fit_logistic_k(
    year: str = None, curriculum: str = "物理类", sigma: float = 0.10
) -> Dict[str, Any]:
    """用「考生位次 vs 专业位次」构造伪标签拟合 k。

    思想：在一分一段覆盖的分数上，取专业位次分布；
    对每个专业，模拟考生位次 = major_rank * (1 + δ)，δ∈[-2σ,2σ]，
    标签 y = 1 if student_rank >= major_rank else 0（位次越大越容易）。
    最小化 logistic 交叉熵，一维搜索 k。
    """
    year = year or SCORE_YEAR
    majors = query(
        """
        SELECT cast(minScoreOrder AS int) AS rk
        FROM majorscore
        WHERE year=? AND curriculum=? AND minScoreOrder!=''
          AND cast(minScoreOrder AS int) > 100
          AND cast(minScoreOrder AS int) < 200000
        ORDER BY RANDOM()
        LIMIT 8000
        """,
        (year, curriculum),
    )
    ranks = [m["rk"] for m in majors if m["rk"]]
    if len(ranks) < 100:
        return {"k": 6.0, "bias": 0.0, "n": len(ranks), "method": "default"}

    # 构造样本
    # 位次越小越好：考生位次 <= 专业线 → 更易录取
    # ratio = major_rank/student_rank，>1 表示考生优于专业线 → 易录
    samples: List[Tuple[float, int]] = []  # (ratio-1, label)
    for mr in ranks:
        for scale in (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5):
            # scale<0 → 考生位次更好(数值更小)
            sr = max(1, int(mr * (1 + scale * sigma)))
            ratio = mr / sr
            label = 1 if sr <= mr else 0  # 考生不差于专业线 → 录取
            samples.append((ratio - 1.0, label))

    def nll(k: float, bias: float = 0.0) -> float:
        loss = 0.0
        for x, y in samples:
            z = k * x + bias
            # stable sigmoid
            if z >= 0:
                p = 1 / (1 + math.exp(-z))
            else:
                ez = math.exp(z)
                p = ez / (1 + ez)
            p = min(1 - 1e-7, max(1e-7, p))
            loss -= y * math.log(p) + (1 - y) * math.log(1 - p)
        # 正则：偏向温和斜率 k≈6，避免过拟合导致 0/100% 极化
        loss = loss / len(samples) + 0.002 * (k - 6.0) ** 2 + 0.01 * bias ** 2
        return loss

    best_k, best_loss = 6.0, nll(6.0)
    for k in [x * 0.5 for x in range(4, 31)]:  # 2.0 .. 15.0
        loss = nll(k)
        if loss < best_loss:
            best_k, best_loss = k, loss

    # 微调 bias
    best_b, best_loss_b = 0.0, best_loss
    for b in [i * 0.05 for i in range(-16, 17)]:
        loss = nll(best_k, b)
        if loss < best_loss_b:
            best_b, best_loss_b = b, loss

    return {
        "k": round(best_k, 3),
        "bias": round(best_b, 3),
        "n": len(samples),
        "nll": round(best_loss_b, 5),
        "year": year,
        "curriculum": curriculum,
        "sigma": sigma,
        "method": "pseudo_label_grid_l2",
    }


def run_calibration(
    curriculum: str = "物理类",
    score_year: Optional[str] = None,
    prev_year: Optional[str] = None,
) -> Dict[str, Any]:
    score_year = score_year or SCORE_YEAR
    prev_year = prev_year or str(int(score_year) - 1)

    # 科类：上年可能是理科
    yoy = compute_yoy_volatility(prev_year, score_year, curriculum)
    if yoy["n"] < 50 and curriculum == "物理类":
        yoy2 = compute_yoy_volatility(prev_year, score_year, "理科")
        if yoy2["n"] > yoy["n"]:
            yoy = yoy2

    fit = fit_logistic_k(score_year, curriculum, sigma=yoy["sigma"])
    result = {
        "curriculum": curriculum,
        "scoreYear": score_year,
        "prevYear": prev_year,
        "volatility": yoy,
        "logistic": fit,
        "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_meta(f"prob_calib:{curriculum}", result)
    save_meta("prob_calib:latest", result)
    return result


def get_calibration(curriculum: str = "物理类") -> Dict[str, Any]:
    cal = load_meta(f"prob_calib:{curriculum}")
    if cal:
        return cal
    # 惰性校准
    try:
        return run_calibration(curriculum)
    except Exception:
        return {
            "logistic": {"k": 6.0, "bias": 0.0},
            "volatility": {"sigma": 0.10, "schoolSigma": {}},
        }


def school_sigma(school: str, curriculum: str = "物理类", default: float = 0.10) -> float:
    cal = get_calibration(curriculum)
    ss = (cal.get("volatility") or {}).get("schoolSigma") or {}
    if school in ss:
        return float(ss[school])
    return float((cal.get("volatility") or {}).get("sigma") or default)
