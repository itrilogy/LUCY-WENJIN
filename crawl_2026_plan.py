#!/usr/bin/env python3
"""一次性补爬 2026 年招生计划（不改动 getdata2025.py）"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from getdata2025 import *

db = DBConn()
schools = db.execQuery("SELECT college_name FROM college_info ORDER BY id")
print(f"共 {len(schools)} 所学校，开始爬 2026 招生计划...")

count = 0
for idx, (name,) in enumerate(schools, 1):
    for cur_label, cur_api in get_curriculum_list("2026"):
        if is_skipped(name, "2026", cur_api, "college_plan"):
            continue
        rn, pn, flag = 50, 0, True
        while flag:
            plans = getCollegePlanFromUrl(name, "江西", 2026, cur_api, pn, rn)
            if plans is None or len(plans) == 0:
                mark_skipped(name, "2026", cur_api, "college_plan")
                flag = False
            else:
                for p in plans:
                    insertCollegePlan(p, name)
                    count += 1
                print(f"[{idx}/{len(schools)}] {name} 2026 {cur_label} +{len(plans)}条 (累计{count})")
                pn += rn
    if idx % 100 == 0:
        print(f"进度: {idx}/{len(schools)}, 已入库 {count} 条")

print(f"2026 招生计划补爬完成！共入库 {count} 条")
