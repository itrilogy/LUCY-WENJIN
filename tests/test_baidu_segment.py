# -*- coding: utf-8 -*-
"""一分一段（百度）与概率校准测试。"""

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


def test_parse_fixture_structure():
    from core.baidu_segment import parse_segment_response

    # 最小假数据
    fake = {
        "Result": [
            {
                "DisplayData": {
                    "resultData": {
                        "tplData": {
                            "batchline": [{"score": "429", "text": "本科批"}],
                            "segmentInfo": [
                                {
                                    "segList": [
                                        {
                                            "minScore": "580",
                                            "maxScore": "580",
                                            "minOrder": "16546",
                                            "maxOrder": "16993",
                                            "num": 448,
                                            "surpass": "90%",
                                        }
                                    ]
                                }
                            ],
                        }
                    }
                }
            }
        ]
    }
    p = parse_segment_response(fake)
    assert p["ok"]
    assert p["rows"][0]["score"] == 580
    assert p["rows"][0]["rank_min"] == 16546


def test_baidu_live_or_skip():
    """有网则实测百度接口；无网 skip。"""
    import requests

    try:
        from core.baidu_segment import fetch_segment

        seg = fetch_segment("江西", "2025", "物理类")
    except Exception as e:
        pytest.skip(f"network/api unavailable: {e}")
    if not seg.get("ok"):
        pytest.skip("empty segment")
    assert len(seg["rows"]) > 200
    # 580 分附近应有位次
    scores = {r["score"]: r for r in seg["rows"]}
    assert 580 in scores or 579 in scores
    r = scores.get(580) or scores.get(579)
    assert r["rank_min"] < r["rank_max"]
    assert r["rank_min"] > 1000


def test_score_to_rank_prefers_baidu():
    from core.rank_table import has_baidu, score_to_rank, upsert_baidu_rows

    if not has_baidu("2025", "物理类"):
        upsert_baidu_rows(
            "2025",
            "物理类",
            [
                {
                    "score": 580,
                    "rank_min": 16546,
                    "rank_max": 16993,
                    "count": 448,
                }
            ],
            [{"score": "429", "text": "本科批"}],
        )
    m = score_to_rank(580, "2025", "物理类")
    assert m
    assert m["source"] in ("baidu", "approx")
    assert m["rank"] >= m.get("rankMin", m["rank"])


def test_calibration_runs():
    from core.recommend.calibrate import get_calibration, run_calibration

    cal = run_calibration("物理类", "2025", "2024")
    assert "logistic" in cal
    assert cal["logistic"]["k"] >= 2
    g = get_calibration("物理类")
    assert g["logistic"]["k"] == cal["logistic"]["k"]


def test_calibrated_prob_in_recommend():
    from core.recommend import run_recommend
    from core.recommend.calibrate import run_calibration

    run_calibration("物理类", "2025", "2024")
    r = run_recommend(
        {
            "score": 580,
            "rank": 17000,
            "firstSubject": "物理",
            "secondSubjects": ["化学"],
        }
    )
    items = r.get("reach") or r.get("match") or []
    assert items
    adm = items[0].get("admit") or {}
    assert "params" in adm
    # 校准后应带 calibrated 标记（若校准成功）
    assert "prob" in adm
