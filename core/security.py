# -*- coding: utf-8 -*-
"""简易 API Token 校验 + 内存限流。"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from functools import wraps
from typing import Callable, Deque, Dict

from flask import jsonify, request

from core.config import API_TOKEN, RATE_LIMIT_PER_MIN

_hits: Dict[str, Deque[float]] = defaultdict(deque)


def client_ip() -> str:
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "unknown"


def check_token() -> bool:
    if not API_TOKEN:
        return True
    token = request.headers.get("X-API-Token") or request.args.get("token") or ""
    if not token and request.is_json:
        body = request.get_json(silent=True) or {}
        token = str(body.get("token") or "")
    return token == API_TOKEN


def check_rate_limit() -> bool:
    if RATE_LIMIT_PER_MIN <= 0:
        return True
    ip = client_ip()
    now = time.time()
    window = 60.0
    q = _hits[ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= RATE_LIMIT_PER_MIN:
        return False
    q.append(now)
    return True


def protect(fn: Callable):
    """装饰器：Token + 限流。"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not check_token():
            return jsonify({"error": "未授权：需要有效 API Token"}), 401
        if not check_rate_limit():
            return jsonify({"error": "请求过于频繁，请稍后再试"}), 429
        return fn(*args, **kwargs)

    return wrapper
