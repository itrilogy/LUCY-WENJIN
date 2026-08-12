# -*- coding: utf-8 -*-
"""推荐引擎集成测试（依赖本地 gaokao2025.sqlite）。"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DB = os.path.join(ROOT, "gaokao2025.sqlite")


@pytest.fixture(scope="module", autouse=True)
def _db_env():
    if not os.path.exists(DB):
        pytest.skip("缺少 gaokao2025.sqlite")
    os.environ["GAOKAO_DB"] = DB
    # 重置可能已打开的连接
    from core.db import reset_conn

    reset_conn()
    yield
    reset_conn()


def test_recommend_basic():
    from core.recommend import run_recommend

    r = run_recommend(
        {
            "score": 580,
            "rank": 15000,
            "firstSubject": "物理",
            "secondSubjects": ["化学", "生物"],
            "aggressiveness": 50,
            "safety": 50,
            "rankFilterWidth": 3.0,
        }
    )
    assert "error" not in r, r.get("error")
    assert "reach" in r and "match" in r and "safe" in r
    total = len(r["reach"]) + len(r["match"]) + len(r["safe"])
    assert total > 0
    # 含 物+不限 专业应能进结果（选科修复）
    sample = (r["reach"] + r["match"] + r["safe"])[:5]
    for item in sample:
        assert "scores" in item
        assert "total" in item["scores"]


def test_recommend_wu_buxian_not_all_filtered():
    """物理+不限再选 不应被全量过滤。"""
    from core.db import query
    from core.recommend.subjects import match_select_subjects

    n = query(
        "SELECT count(1) c FROM college_plan WHERE year=? AND curriculum=? AND selectSubjects=?",
        ("2026", "物理类", "物+不限"),
    )[0]["c"]
    assert n > 1000
    assert match_select_subjects("物+不限", "物理", ["化学"]) is True


def test_health_import_app():
    from app import app

    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
