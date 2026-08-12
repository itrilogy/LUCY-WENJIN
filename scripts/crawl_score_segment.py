#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从百度 opendata 爬取江西一分一段，写入 score_segment。

用法::

    python3 scripts/crawl_score_segment.py
    python3 scripts/crawl_score_segment.py --year 2025 --category 物理类
    python3 scripts/crawl_score_segment.py --all
    python3 scripts/crawl_score_segment.py --calibrate
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib3

urllib3.disable_warnings()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.baidu_segment import JIANGXI_YEARS, fetch_segment
from core.config import PROVINCE_DEFAULT
from core.rank_table import has_baidu, segment_stats, upsert_baidu_rows
from core.recommend.calibrate import run_calibration


def crawl_one(year: str, category: str, province: str = PROVINCE_DEFAULT) -> int:
    print(f"拉取 {province} {year} {category} …", end=" ", flush=True)
    seg = fetch_segment(province, year, category)
    if not seg.get("ok"):
        print("无数据")
        return 0
    n = upsert_baidu_rows(year, category, seg["rows"], seg.get("batchline"))
    bl = seg.get("batchline") or []
    print(f"✓ {n} 行, 批次线={bl}")
    return n


def crawl_all(province: str = PROVINCE_DEFAULT) -> int:
    total = 0
    for year, cats in JIANGXI_YEARS:
        for cat in cats:
            try:
                total += crawl_one(year, cat, province)
            except Exception as e:
                print(f"✗ {e}")
            time.sleep(0.6)
    return total


def main():
    ap = argparse.ArgumentParser(description="百度一分一段爬取")
    ap.add_argument("--province", default=PROVINCE_DEFAULT)
    ap.add_argument("--year", default="")
    ap.add_argument("--category", default="")
    ap.add_argument("--all", action="store_true", help="爬取江西近年全部")
    ap.add_argument("--calibrate", action="store_true", help="爬完后做概率校准")
    ap.add_argument("--force", action="store_true", help="已有 baidu 数据也重爬")
    args = ap.parse_args()

    if args.all or (not args.year and not args.category):
        total = crawl_all(args.province)
        print(f"合计写入 {total} 行")
    else:
        year = args.year or "2025"
        cat = args.category or "物理类"
        if not args.force and has_baidu(year, cat):
            print(f"已有 baidu 数据 {year} {cat}，使用 --force 重爬")
        else:
            crawl_one(year, cat, args.province)

    print("\n当前表统计:")
    for y in ("2026", "2025", "2024", "2023", "2022", "2021"):
        st = segment_stats(y)
        if st:
            print(f"  {y}: {st}")

    if args.calibrate or args.all:
        print("\n概率校准…")
        for cur in ("物理类", "历史类"):
            try:
                cal = run_calibration(cur)
                lg = cal["logistic"]
                vol = cal["volatility"]
                print(
                    f"  {cur}: k={lg['k']} bias={lg['bias']} "
                    f"σ={vol['sigma']} (n_yoy={vol['n']}, n_fit={lg['n']})"
                )
            except Exception as e:
                print(f"  {cur} 校准失败: {e}")


if __name__ == "__main__":
    main()
