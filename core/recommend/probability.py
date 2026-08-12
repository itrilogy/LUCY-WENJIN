# -*- coding: utf-8 -*-
"""录取概率模型（可校准）。

- 默认 logistic(k, bias) 由 calibrate.run_calibration 拟合
- 波动 σ 来自 majorscore 跨年相对变化；可按学校覆盖
- 结合一分一段后，位次更可靠，区间更可信
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def estimate_admit_prob(
    student_rank: int,
    major_rank: int,
    plan_this: Optional[float] = None,
    plan_last: Optional[float] = None,
    is_new_major: bool = False,
    rank_volatility: Optional[float] = None,
    k: Optional[float] = None,
    bias: Optional[float] = None,
    school: Optional[str] = None,
    curriculum: str = "物理类",
    use_calibration: bool = True,
) -> Dict[str, Any]:
    """估算录取概率。

    ratio = major_rank / student_rank
    （>1 专业线更差 → 更容易；<1 更难）
    """
    if student_rank <= 0 or major_rank <= 0:
        return {
            "prob": 0.0,
            "low": 0.0,
            "high": 0.0,
            "label": "未知",
            "level": "unknown",
            "pct": "—",
            "rangePct": "—",
            "calibrated": False,
        }

    # 加载校准
    cal_k, cal_b, cal_sig = 6.0, 0.0, 0.10
    calibrated = False
    if use_calibration:
        try:
            from core.recommend.calibrate import get_calibration, school_sigma

            cal = get_calibration(curriculum)
            lg = cal.get("logistic") or {}
            cal_k = float(lg.get("k") or 6.0)
            cal_b = float(lg.get("bias") or 0.0)
            if school:
                cal_sig = school_sigma(school, curriculum, default=0.10)
            else:
                cal_sig = float((cal.get("volatility") or {}).get("sigma") or 0.10)
            calibrated = True
        except Exception:
            pass

    k = float(k if k is not None else cal_k)
    bias = float(bias if bias is not None else cal_b)
    vol = float(rank_volatility if rank_volatility is not None else cal_sig)

    if is_new_major:
        vol = max(vol, 0.14)

    ratio = major_rank / student_rank

    def _sigmoid(x: float) -> float:
        z = k * x + bias
        if z >= 0:
            return 1.0 / (1.0 + math.exp(-z))
        ez = math.exp(z)
        return ez / (1.0 + ez)

    # 计划趋势
    plan_adj = 0.0
    if plan_this and plan_last and plan_last > 0:
        pr = plan_this / plan_last
        if pr > 1.2:
            plan_adj = min(0.12, (pr - 1.0) * 0.15)
        elif pr < 0.8:
            plan_adj = max(-0.12, (pr - 1.0) * 0.15)
    elif plan_this and not plan_last:
        plan_adj = 0.04

    def _p(r: float) -> float:
        return _clamp(_sigmoid(r - 1.0) + plan_adj)

    p_mid = _p(ratio)
    p_low = _p(ratio * (1.0 - vol))
    p_high = _p(ratio * (1.0 + vol))
    if p_low > p_high:
        p_low, p_high = p_high, p_low
    if p_high - p_low < 0.06:
        p_low = _clamp(p_mid - 0.04)
        p_high = _clamp(p_mid + 0.04)

    level, label = _label(p_mid, ratio)
    return {
        "prob": round(p_mid, 3),
        "low": round(p_low, 3),
        "high": round(p_high, 3),
        "label": label,
        "level": level,
        "pct": f"{int(round(p_mid * 100))}%",
        "rangePct": f"{int(round(p_low * 100))}–{int(round(p_high * 100))}%",
        "calibrated": calibrated,
        "params": {"k": k, "bias": bias, "sigma": round(vol, 4)},
    }


def _label(prob: float, ratio: float) -> tuple:
    if ratio < 0.85 or prob < 0.25:
        return "reach", "冲刺"
    if ratio < 1.05 or prob < 0.55:
        return "edge", "边缘"
    if ratio < 1.35 or prob < 0.8:
        return "match", "较稳"
    return "safe", "稳妥"
