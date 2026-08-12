# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recommend.scoring import (
    calc_major_score,
    calc_plan_score,
    calc_rank_score,
    calc_tag_score,
    safe_int,
)


def test_rank_score_peak():
    assert calc_rank_score(1.0, 0.1, 3.0) == 40
    assert calc_rank_score(0.5, 0.1, 3.0) == 0  # 超出 width


def test_tag_or_and():
    assert calc_tag_score("985,双一流", ["985"], "or") == 10
    assert calc_tag_score("211", ["985", "211"], "or") == 8
    assert calc_tag_score("985,211", ["985", "211"], "and") == 15
    assert calc_tag_score("985", ["985", "211"], "and") == -1


def test_major_mandatory():
    s = calc_major_score(
        {"keyword_hit": False, "subject_matched": True, "major_ratio": 1.0},
        "计算机",
        "mandatory",
        0.1,
    )
    assert s == -1


def test_plan_score():
    assert calc_plan_score(None) == 0
    assert calc_plan_score(1) == 0  # log2(1)*3 = 0
    assert calc_plan_score(2) > 0
    assert calc_plan_score(1000) <= 15


def test_safe_int():
    assert safe_int("12,345") == 12345
    assert safe_int("x") == 999999
