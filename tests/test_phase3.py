# -*- coding: utf-8 -*-
"""Phase 3：概率、专业簇、分位次、工具、云端备选。"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DB = os.path.join(ROOT, "gaokao2025.sqlite")


@pytest.fixture(scope="module", autouse=True)
def _env():
    if not os.path.exists(DB) or os.path.getsize(DB) < 100000:
        pytest.skip("缺少包含完整数据的 gaokao2025.sqlite")
    os.environ["GAOKAO_DB"] = DB
    from core.db import reset_conn

    reset_conn()
    yield
    reset_conn()


def test_estimate_admit_prob():
    from core.recommend.probability import estimate_admit_prob

    hard = estimate_admit_prob(20000, 5000)  # 专业远好于考生
    easy = estimate_admit_prob(5000, 20000)
    assert hard["prob"] < easy["prob"]
    assert 0 <= hard["low"] <= hard["prob"] <= hard["high"] <= 1
    assert hard["pct"].endswith("%")


def test_expand_keywords_cluster():
    from core.recommend.clusters import expand_keywords

    exp = expand_keywords(["计算机"])
    assert "软件工程" in exp
    assert "人工智能" in exp


def test_recommend_has_admit():
    from core.recommend import run_recommend

    r = run_recommend(
        {
            "score": 580,
            "rank": 15000,
            "firstSubject": "物理",
            "secondSubjects": ["化学", "生物"],
            "freeMajor": "计算机",
            "useCluster": True,
        }
    )
    assert "error" not in r
    items = r["reach"] + r["match"] + r["safe"]
    assert items
    assert "admit" in items[0]
    assert "prob" in items[0]["admit"]
    assert r.get("keywordsExpanded")


def test_rank_table_rebuild():
    from core.rank_table import rebuild_approx_from_schoolscore, score_to_rank

    n = rebuild_approx_from_schoolscore("2025", "物理类")
    assert n > 50
    m = score_to_rank(580, "2025", "物理类")
    assert m and m["rank"] > 0


def test_tools_search_and_compare():
    from core.tools import compare_schools, search_major

    s = search_major("计算机", year="2025", curriculum="物理类", limit=5)
    assert s["count"] >= 1
    c = compare_schools(["南昌大学", "江西师范大学"], year="2025")
    assert len(c["schools"]) == 2


def test_shortlist_store():
    from core.shortlist_store import add_item, list_items, new_session_id, to_csv

    sid = new_session_id()
    add_item(
        sid,
        {
            "school": "测试大学",
            "major": "测试专业",
            "rank": "1000",
            "score": "80",
            "tier": "match",
        },
    )
    items = list_items(sid)
    assert len(items) == 1
    csv = to_csv(sid)
    assert "测试大学" in csv


def test_api_quality_and_shortlist():
    from app import app

    c = app.test_client()
    q = c.get("/api/quality")
    assert q.status_code == 200
    assert "counts" in q.get_json()

    r = c.post(
        "/api/shortlist",
        json={"item": {"school": "A", "major": "B", "rank": "1", "score": "9", "tier": "safe"}},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["sessionId"]
    assert len(data["items"]) >= 1

    cl = c.get("/api/clusters")
    assert cl.status_code == 200
    assert "计算机" in cl.get_json()
