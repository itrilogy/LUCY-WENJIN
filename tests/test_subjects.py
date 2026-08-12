# -*- coding: utf-8 -*-
"""选科匹配黄金用例。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recommend.subjects import match_select_subjects, parse_special_course


def test_unlimited():
    assert match_select_subjects("不限", "物理", ["化学"]) is True
    assert match_select_subjects("", "物理", []) is True


def test_wu_buxian():
    """高频：物+不限 应通过（旧实现会因「不限」token 失败）。"""
    assert match_select_subjects("物+不限", "物理", ["化学", "生物"]) is True
    assert match_select_subjects("物+不限", "物理", []) is True
    assert match_select_subjects("史+不限", "历史", ["政治"]) is True
    assert match_select_subjects("物+不限", "历史", ["政治"]) is False


def test_wu_hua():
    assert match_select_subjects("物+化", "物理", ["化学"]) is True
    assert match_select_subjects("物+化", "物理", ["生物"]) is False
    assert match_select_subjects("物+化", "历史", ["化学"]) is False


def test_paren_and():
    assert match_select_subjects("物+(化+生)", "物理", ["化学", "生物"]) is True
    assert match_select_subjects("物+(化+生)", "物理", ["化学"]) is False
    assert match_select_subjects("史+(政+地)", "历史", ["政治", "地理"]) is True


def test_shi_zheng():
    assert match_select_subjects("史+政", "历史", ["政治"]) is True
    assert match_select_subjects("史+政", "历史", ["地理"]) is False


def test_parse_special_course_buxian():
    first, conds = parse_special_course("首选物理，再选不限")
    assert first == "物理"
    assert conds[0]["type"] == "any"
