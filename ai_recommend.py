#!/usr/bin/env python3
"""DeepSeek AI 志愿分析（多工具 Function Calling + 可选 SSE 流式）"""

from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional, Tuple

import requests

from core.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL
from core.tools import dispatch_tool

RECOMMEND_TOOL = {
    "type": "function",
    "function": {
        "name": "recommend",
        "description": "按分数/位次/选科获取冲稳保志愿推荐（含录取概率估算）",
        "parameters": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "description": "高考分数"},
                "rank": {"type": "integer", "description": "全省位次"},
                "firstSubject": {
                    "type": "string",
                    "enum": ["物理", "历史"],
                    "description": "首选科目",
                },
                "secondSubjects": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["化学", "生物", "政治", "地理"],
                    },
                },
                "freeMajor": {
                    "type": "string",
                    "description": "专业关键词或簇名，如 计算机,医学",
                },
                "freeMajorMode": {
                    "type": "string",
                    "enum": ["optional", "mandatory"],
                },
                "provinces": {"type": "array", "items": {"type": "string"}},
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["985", "211", "双一流", "强基计划"],
                    },
                },
                "tagMode": {"type": "string", "enum": ["or", "and"]},
                "aggressiveness": {"type": "integer"},
                "safety": {"type": "integer"},
                "usePlan": {"type": "boolean"},
                "rankFilterWidth": {"type": "number"},
                "sortBy": {
                    "type": "string",
                    "enum": ["score", "prob"],
                    "description": "score=综合分, prob=录取概率",
                },
            },
            "required": ["score", "rank", "firstSubject"],
        },
    },
}

SEARCH_MAJOR_TOOL = {
    "type": "function",
    "function": {
        "name": "search_major",
        "description": "按专业名模糊搜索各校该专业录取分/位次",
        "parameters": {
            "type": "object",
            "properties": {
                "major": {"type": "string", "description": "专业关键词"},
                "year": {"type": "string", "description": "年份，默认上年"},
                "curriculum": {
                    "type": "string",
                    "description": "物理类/历史类/理科/文科",
                },
                "limit": {"type": "integer", "description": "最多条数，默认30"},
            },
            "required": ["major"],
        },
    },
}

COMPARE_TOOL = {
    "type": "function",
    "function": {
        "name": "compare_schools",
        "description": "对比多所大学的排名、标签、录取线与优势专业",
        "parameters": {
            "type": "object",
            "properties": {
                "schools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "学校全称列表",
                },
                "year": {"type": "string"},
                "curriculum": {"type": "string", "enum": ["物理类", "历史类"]},
            },
            "required": ["schools"],
        },
    },
}

EXPLAIN_TOOL = {
    "type": "function",
    "function": {
        "name": "explain_admission",
        "description": "根据考生位次与专业录取位次估算录取概率区间",
        "parameters": {
            "type": "object",
            "properties": {
                "studentRank": {"type": "integer"},
                "majorRank": {"type": "integer"},
                "planThis": {"type": "number"},
                "planLast": {"type": "number"},
                "isNew": {"type": "boolean"},
            },
            "required": ["studentRank", "majorRank"],
        },
    },
}

ALL_TOOLS = [RECOMMEND_TOOL, SEARCH_MAJOR_TOOL, COMPARE_TOOL, EXPLAIN_TOOL]

SYSTEM_PROMPT = """你是一个高考志愿填报助手（江西 3+1+2）。

## 可用工具
1. recommend — 冲/稳/保推荐（含概率）
2. search_major — 按专业名查录取数据
3. compare_schools — 多校对比
4. explain_admission — 解释录取概率

## 对话流程
逐一询问（每次只问一个）：分数 → 位次 → 物理/历史 → 再选科目 → 专业偏好（可用簇名如计算机/医学）→ 省份/档次（可选）→ 激进/保底（可选）。
信息足够即可调用工具，不要编造数据。

## 输出格式
工具返回后用 Markdown，包含：
- 考生概况
- 推荐表（学校/专业/分位次/概率区间/总分）
- 2-3 条具体建议
概率为启发式估算，请注明「仅供参考，非官方概率」。"""


def call_deepseek(
    messages: List[Dict[str, Any]], stream: bool = False
) -> Any:
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY 未设置"}
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "tools": ALL_TOOLS,
        "tool_choice": "auto",
        "temperature": 0.7,
        "max_tokens": 4096,
        "stream": stream,
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        if stream:
            resp = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=120,
                stream=True,
            )
            return resp
        resp = requests.post(
            DEEPSEEK_API_URL, headers=headers, json=payload, timeout=90
        )
        result = resp.json()
        if "error" in result:
            err = result["error"]
            if isinstance(err, dict):
                return {"error": err.get("message", str(err))}
            return {"error": str(err)}
        return result
    except Exception as e:
        return {"error": str(e)}


def _slim(name: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    if "error" in rec:
        return rec
    if name == "recommend":
        out = {
            k: rec[k]
            for k in (
                "year",
                "planYear",
                "curriculum",
                "aggressiveness",
                "safety",
                "rankFilterWidth",
                "probModel",
                "keywordsUser",
            )
            if k in rec
        }
        for tier in ("reach", "match", "safe"):
            items = rec.get(tier) or []
            slim_items = []
            for it in items[:12]:
                slim_items.append(
                    {
                        "school": it.get("school"),
                        "majorName": it.get("majorName"),
                        "majorScore": it.get("majorScore"),
                        "majorRank": it.get("majorRank"),
                        "ratio": it.get("ratio"),
                        "admit": it.get("admit"),
                        "scores": it.get("scores"),
                        "planThisYear": it.get("planThisYear"),
                        "planLastYear": it.get("planLastYear"),
                    }
                )
            out[tier] = slim_items
            out[f"{tier}Total"] = len(items)
        return out
    if name == "search_major":
        rows = rec.get("rows") or []
        return {**rec, "rows": rows[:20]}
    if name == "compare_schools":
        return rec
    return rec


def process_chat(
    history: List[Dict[str, Any]], user_message: str
) -> Tuple[str, List[Dict[str, Any]]]:
    if not history:
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
    history = list(history)
    history.append({"role": "user", "content": user_message})

    for _ in range(6):
        result = call_deepseek(history, stream=False)
        if isinstance(result, dict) and "error" in result:
            return result["error"], history
        choice = result["choices"][0]
        msg = choice["message"]

        if msg.get("tool_calls"):
            history.append(msg)
            for tc in msg["tool_calls"]:
                fname = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                raw = dispatch_tool(fname, args)
                history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(
                            _slim(fname, raw), ensure_ascii=False
                        ),
                    }
                )
        else:
            history.append(msg)
            return msg.get("content") or "", history

    return "处理超时，请重试", history


def process_chat_stream(
    history: List[Dict[str, Any]], user_message: str
) -> Generator[Dict[str, Any], None, None]:
    """SSE 事件生成器。

    事件类型:
      status / tool / delta / done / error
    """
    if not history:
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
    history = list(history)
    history.append({"role": "user", "content": user_message})
    yield {"type": "status", "message": "思考中…"}

    for _ in range(6):
        # 工具轮次用非流式，最终回答用流式
        result = call_deepseek(history, stream=False)
        if isinstance(result, dict) and "error" in result:
            yield {"type": "error", "message": result["error"]}
            return
        choice = result["choices"][0]
        msg = choice["message"]

        if msg.get("tool_calls"):
            history.append(msg)
            for tc in msg["tool_calls"]:
                fname = tc["function"]["name"]
                yield {"type": "tool", "name": fname, "message": f"调用 {fname}…"}
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                raw = dispatch_tool(fname, args)
                history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(
                            _slim(fname, raw), ensure_ascii=False
                        ),
                    }
                )
            continue

        # 最终文本：再请求一次流式（带 tools 关闭更稳：用无 tools 的续写）
        yield {"type": "status", "message": "生成回答…"}
        # 直接使用已拿到的 content（非流式已完整）；若要真流式再调一次
        content = msg.get("content") or ""
        if content:
            # 模拟分片，前端体验接近流式；若有 key 则尝试真流式
            if DEEPSEEK_API_KEY:
                stream_resp = _stream_final(history)
                if stream_resp is not None:
                    full = []
                    try:
                        for piece in stream_resp:
                            full.append(piece)
                            yield {"type": "delta", "text": piece}
                        text = "".join(full)
                        history.append({"role": "assistant", "content": text})
                        yield {"type": "done", "reply": text, "history": history}
                        return
                    except Exception as e:
                        yield {"type": "error", "message": str(e)}
                        return
            # fallback 整段
            history.append(msg)
            yield {"type": "delta", "text": content}
            yield {"type": "done", "reply": content, "history": history}
            return

        history.append(msg)
        yield {"type": "done", "reply": content, "history": history}
        return

    yield {"type": "error", "message": "处理超时，请重试"}


def _stream_final(history: List[Dict[str, Any]]) -> Optional[Generator[str, None, None]]:
    """对最终回复做流式输出（不再带 tools，避免中途 tool_call）。"""
    if not DEEPSEEK_API_KEY:
        return None

    def gen():
        payload = {
            "model": "deepseek-chat",
            "messages": history,
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        with requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=120,
            stream=True,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0].get("delta") or {}
                        piece = delta.get("content") or ""
                        if piece:
                            yield piece
                    except Exception:
                        continue

    return gen()
