#!/usr/bin/env python3
"""补爬 2025 年专业分数线"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from getdata2025 import *

# 清掉 2025 的旧 skip 标记
db = DBConn()
db.execSql("DELETE FROM crawl_skip WHERE table_name='majorscore' AND year='2025'")

# 找有 schoolscore 2025 但缺 majorscore 2025 的学校
schools = db.execQuery("""
    SELECT DISTINCT s.legalName FROM schoolscore s
    WHERE s.year='2025'
    AND NOT EXISTS (SELECT 1 FROM majorscore m WHERE m.legalName=s.legalName AND m.year='2025')
    ORDER BY s.legalName
""")
print(f"需补爬 {len(schools)} 所学校")

for i, (name,) in enumerate(schools, 1):
    if is_skipped(name, "2025", "物理类", "majorscore") and is_skipped(name, "2025", "历史类", "majorscore"):
        continue
    for cur_label, cur_api in get_curriculum_list("2025"):
        getMajorScore(name, "江西", 2025, cur_api)
    if i % 20 == 0:
        print(f"进度: {i}/{len(schools)}")
print("2025 majorscore 补爬完成！")
