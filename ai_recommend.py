#!/usr/bin/env python3
"""DeepSeek AI 志愿分析引擎（Function Calling）"""

import os, json, requests

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

RECOMMEND_TOOL = {
    "type": "function",
    "function": {
        "name": "recommend",
        "description": "获取高考志愿推荐结果（按分数/位次/选科推荐院校和专业）",
        "parameters": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "description": "高考分数"},
                "rank": {"type": "integer", "description": "全省位次"},
                "firstSubject": {"type": "string", "enum": ["物理", "历史"], "description": "首选科目"},
                "secondSubjects": {
                    "type": "array", "items": {"type": "string", "enum": ["化学", "生物", "政治", "地理"]},
                    "description": "再选科目列表（按偏好顺序）"
                },
                "freeMajor": {"type": "string", "description": "专业关键词，多个用逗号分隔（如 计算机,人工智能）"},
                "freeMajorMode": {"type": "string", "enum": ["optional", "mandatory"],
                    "description": "optional=可选的仅加权, mandatory=至少命中一个关键词才展示"},
                "provinces": {
                    "type": "array", "items": {"type": "string"},
                    "description": "大学所在省份过滤（如 北京,上海）"
                },
                "tags": {"type": "array", "items": {"type": "string", "enum": ["985", "211", "双一流", "强基计划"]}},
                "tagMode": {"type": "string", "enum": ["or", "and"], "description": "or=任一标签匹配, and=全部标签匹配"},
                "aggressiveness": {"type": "integer", "description": "冲刺激进度 0-100，越大越敢冲好学校"},
                "safety": {"type": "integer", "description": "保底程度 0-100，越大保底学校越多"},
                "usePlan": {"type": "boolean", "description": "是否参考招生计划数"}
            },
            "required": ["score", "rank", "firstSubject"]
        }
    }
}

SYSTEM_PROMPT = """你是一个高考志愿填报助手。

## 工作流程

逐一询问以下信息，每次只问一个问题，等用户回答后再问下一个：

1. 高考分数是多少？
2. 全省位次是多少？
3. 选物理类还是历史类？
4. 再选科目有哪些？（化学/生物/政治/地理，可多选）
5. 有偏好的专业方向吗？（如"计算机,人工智能"，多个用逗号，可选）
6. 倾向于哪些省份的大学？（如北京、上海等，可选）
7. 对学校档次有要求吗？（985/211/双一流/强基，可多选）
8. （可选追问）想更激进冲好学校，还是更保守求稳？

语气亲切，用表情符号，每次只问一个。用户说"没有"或"不需要"则跳过。

收集完成后调用 recommend 函数获取结果。收到返回后按 Markdown 输出：

### 📊 考生概况
- 分数/位次/科类/选科/专业偏好/省份筛选

### ⚡ 冲刺院校
| 学校 | 专业 | 分数/位次 | 总分 | 计划(今/去) |
按总分降序排列，解释为什么是冲刺。

### ✅ 稳健院校
| 学校 | 专业 | 分数/位次 | 总分 | 计划(今/去) |
按总分降序排列。

### 🛡️ 保底院校
| 学校 | 专业 | 分数/位次 | 总分 | 计划(今/去) |
按总分降序排列。

### 💡 建议
基于位次比和各评分项给出 2-3 条具体建议。注意新专业标记 ⚠️ 的分数为均值估算。

注意：只展示 recommend 返回的真实数据，不要编造。"""


def call_deepseek(messages):
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY 未设置"}
    try:
        resp = requests.post(DEEPSEEK_API_URL, headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }, json={
            "model": "deepseek-chat",
            "messages": messages,
            "tools": [RECOMMEND_TOOL],
            "tool_choice": "auto",
            "temperature": 0.7,
            "max_tokens": 4096
        }, timeout=60)
        result = resp.json()
        if "error" in result:
            return {"error": result["error"]["message"]}
        return result
    except Exception as e:
        return {"error": str(e)}


def call_recommend_api(args):
    try:
        r = requests.post("http://127.0.0.1:5080/api/recommend", json=args, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": f"推荐服务调用失败: {e}"}


def process_chat(history, user_message):
    if not history:
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
    history.append({"role": "user", "content": user_message})

    for _ in range(5):
        result = call_deepseek(history)
        if "error" in result:
            return result["error"], history
        choice = result["choices"][0]
        msg = choice["message"]

        if msg.get("tool_calls"):
            history.append(msg)
            for tc in msg["tool_calls"]:
                if tc["function"]["name"] == "recommend":
                    args = json.loads(tc["function"]["arguments"])
                    rec = call_recommend_api(args)
                    history.append({"role": "tool", "tool_call_id": tc["id"],
                                    "content": json.dumps(rec, ensure_ascii=False)})
        else:
            history.append(msg)
            return msg["content"], history

    return "处理超时，请重试", history
