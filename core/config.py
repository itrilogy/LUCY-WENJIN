# -*- coding: utf-8 -*-
"""统一配置：路径、年份、安全与服务参数。"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(env_path: Path) -> None:
    """轻量加载 .env 文件，已存在的环境变量优先不覆写。"""
    if not env_path.is_file():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


_load_env_file(ROOT_DIR / ".env")

# 数据库：环境变量优先，否则项目根目录下默认文件
DB_PATH = Path(os.environ.get("GAOKAO_DB", str(ROOT_DIR / "gaokao2025.sqlite")))

# 数据年份：可覆盖，默认「当年 plan + 上年 score」
_NOW = datetime.now().year
PLAN_YEAR = str(os.environ.get("GAOKAO_PLAN_YEAR", _NOW))
SCORE_YEAR = str(os.environ.get("GAOKAO_SCORE_YEAR", int(PLAN_YEAR) - 1))
LAST_PLAN_YEAR = str(int(PLAN_YEAR) - 1)

PROVINCE_DEFAULT = os.environ.get("GAOKAO_PROVINCE", "江西")

# Flask
HOST = os.environ.get("GAOKAO_HOST", "0.0.0.0")
PORT = int(os.environ.get("GAOKAO_PORT", "5080"))
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("GAOKAO_SECRET_KEY", "dev-only-change-me")

# 简易鉴权：设置后请求头 X-API-Token 或 ?token= 需匹配；空字符串关闭
API_TOKEN = os.environ.get("GAOKAO_API_TOKEN", "").strip()

# 限流：每 IP 每分钟最大请求数（0=关闭）
RATE_LIMIT_PER_MIN = int(os.environ.get("GAOKAO_RATE_LIMIT", "60"))

# AI
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.environ.get(
    "DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions"
)

# 推荐默认参数
DEFAULT_AGGRESSIVENESS = 50
DEFAULT_SAFETY = 50
DEFAULT_RANK_FILTER_WIDTH = 3.0

# 标签分（OR 模式累加上限 25，与实现一致）
TAG_POINTS = {"985": 10, "211": 8, "双一流": 5, "强基计划": 2}
TAG_AND_SCORE = 15
TAG_OR_CAP = 25
