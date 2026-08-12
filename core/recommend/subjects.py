# -*- coding: utf-8 -*-
"""选科匹配：支持 plan 简称（物+不限 / 物+(化+生)）与 majorscore 长文案。"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

SUBJ_SHORT = {
    "物理": "物",
    "化学": "化",
    "生物": "生",
    "历史": "史",
    "地理": "地",
    "政治": "政",
    "思想政治": "政",
}

SHORT_TO_FULL = {
    "物": "物理",
    "化": "化学",
    "生": "生物",
    "史": "历史",
    "地": "地理",
    "政": "政治",
}

_VALID_SHORT = set(SHORT_TO_FULL.keys())


def to_short(name: str) -> str:
    if not name:
        return ""
    name = name.strip()
    if name in SUBJ_SHORT:
        return SUBJ_SHORT[name]
    if name in _VALID_SHORT:
        return name
    # 模糊：包含全称
    for full, short in SUBJ_SHORT.items():
        if full in name:
            return short
    return name[:1] if name else ""


def parse_special_course(sc: str) -> Tuple[Optional[str], List[dict]]:
    """解析 majorscore.specialCourse 长文案。

    返回 (first: '物理'/'历史'/None, conditions)
    conditions: [{'type':'and'|'or'|'any', 'subjects':[...全称...]}]
    """
    if not sc:
        return None, [{"type": "any", "subjects": []}]
    text = sc
    first = None
    for p in ("物理", "历史"):
        if p in text[:20]:
            first = p
            break
    idx = text.find("再选")
    rest = text[idx + 2 :] if idx >= 0 else re.sub(r"^首选(物理|历史)[，,]?", "", text)
    if not rest.strip() or "不限" in rest:
        return first, [{"type": "any", "subjects": []}]
    conditions: List[dict] = []
    parts = rest.split("、")
    for part in parts:
        part = part.strip().replace("（", "(").replace("）", ")")
        part = re.sub(r"\d+科必选", "", part)
        part = part.replace("(", "").replace(")", "").strip()
        if not part or "不限" in part:
            continue
        if "/" in part:
            subs = [x.strip() for x in part.split("/") if x.strip()]
            if subs:
                conditions.append({"type": "or", "subjects": subs})
        elif "，" in part or "," in part:
            subs = [x.strip() for x in re.split(r"[，,]", part) if x.strip()]
            if len(subs) > 1:
                conditions.append({"type": "and", "subjects": subs})
            elif subs:
                conditions.append({"type": "and", "subjects": subs})
        else:
            conditions.append({"type": "and", "subjects": [part]})
    return first, conditions if conditions else [{"type": "any", "subjects": []}]


def match_select_subjects(
    select_subjects: str,
    first_subj: str,
    second_subjs: Sequence[str],
) -> bool:
    """匹配 college_plan.selectSubjects 简称格式。

    支持：
      - 空 / 不限
      - 物+化 / 史+政
      - 物+不限 / 史+不限
      - 物+(化+生) / 史+(政+地)  → 括号内为再选必选组合
      - 物+(化/生)  → 括号内 OR（若出现）
    """
    ss = (select_subjects or "").strip()
    if not ss or ss == "不限":
        return True

    first_short = to_short(first_subj)
    allowed = {first_short} | {to_short(s) for s in second_subjs if s}
    allowed.discard("")

    # 规范化括号
    ss = ss.replace("（", "(").replace("）", ")")

    # 首选 + 再选：用 + 在顶层分割（括号内 + 保留）
    parts = _split_top_level(ss, "+")
    parts = [p.strip() for p in parts if p.strip()]

    for part in parts:
        if part in ("不限", "无", "任意"):
            continue
        if part.startswith("(") and part.endswith(")"):
            inner = part[1:-1].strip()
            if not inner or "不限" in inner:
                continue
            # 括号内：+ 表示 AND，/ 表示 OR
            if "/" in inner and "+" not in inner:
                opts = [to_short(x.strip()) for x in inner.split("/")]
                opts = [o for o in opts if o and o != "不" and o not in ("不限",)]
                if opts and not any(o in allowed for o in opts):
                    return False
            else:
                # AND of subjects (possibly nested simplified as 化+生)
                and_parts = [to_short(x.strip()) for x in _split_top_level(inner, "+")]
                and_parts = [p for p in and_parts if p and p not in ("不限", "不")]
                if not all(p in allowed for p in and_parts):
                    return False
            continue

        # 普通 token：物 / 化 / 史
        tok = to_short(part)
        if not tok or tok in ("不限", "不"):
            continue
        if tok not in allowed:
            return False
    return True


def _split_top_level(s: str, sep: str) -> List[str]:
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def match_subjects_v2(
    sc: str, first_subj: str, second_subjs: Sequence[str]
) -> Tuple[bool, int]:
    """长文案 specialCourse 匹配 + 偏好分（0~10）。"""
    first, conds = parse_special_course(sc)
    if first and first != first_subj:
        return False, 0
    if not conds or (len(conds) == 1 and conds[0]["type"] == "any"):
        return True, 10
    matched_any = False
    prefer_score = 0
    second_list = list(second_subjs)
    for cond in conds:
        if cond["type"] == "and":
            if all(
                any(s in cs or cs in s for cs in cond["subjects"])
                for s in cond["subjects"]
            ) or all(
                any(to_short(s) == to_short(cs) for cs in second_list)
                for s in cond["subjects"]
            ):
                # 要求再选科目都在考生再选中
                ok = True
                for s in cond["subjects"]:
                    if not any(
                        to_short(s) == to_short(ps) or s in ps or ps in s
                        for ps in second_list
                    ):
                        ok = False
                        break
                if not ok:
                    continue
                matched_any = True
                for subj in cond["subjects"]:
                    for idx, ps in enumerate(second_list):
                        if to_short(ps) == to_short(subj) or ps in subj or subj in ps:
                            prefer_score += max(0, 5 - idx)
                            break
        elif cond["type"] == "or":
            if any(
                any(ps in s or s in ps or to_short(ps) == to_short(s) for s in cond["subjects"])
                for ps in second_list
            ):
                matched_any = True
                for ps in second_list:
                    if any(
                        ps in s or s in ps or to_short(ps) == to_short(s)
                        for s in cond["subjects"]
                    ):
                        prefer_score += max(0, 5 - second_list.index(ps))
                        break
    return matched_any, min(10, prefer_score)
