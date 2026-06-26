#!/usr/bin/env python3
"""高考志愿填报助手 - Web UI (江西版2025)"""

import sqlite3, os, math, json
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from ai_recommend import process_chat

app = Flask(__name__)
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gaokao2025.sqlite")
CURRENT_YEAR = datetime.now().year  # 2026

def query(sql, params=()):
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.cursor().execute(sql, params).fetchall()]
    conn.close()
    return rows

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/filters")
def api_filters():
    return jsonify({
        "provinces": [r["province"] for r in query("SELECT DISTINCT province FROM college_info WHERE province!='' ORDER BY province")],
        "types": [r["school_type"] for r in query("SELECT DISTINCT school_type FROM college_info WHERE school_type!='' ORDER BY school_type")],
        "natures": [r["nature"] for r in query("SELECT DISTINCT nature FROM college_info WHERE nature!='' ORDER BY nature")],
        "years": [r["year"] for r in query("SELECT DISTINCT year FROM majorscore ORDER BY year DESC")],
        "planYears": [r["year"] for r in query("SELECT DISTINCT year FROM college_plan ORDER BY year DESC")],
    })

# ─── 大学搜索（省份/类型/办学 多选） ───
@app.route("/api/schools")
def api_schools():
    name = request.args.get("name", "")
    provinces = request.args.getlist("province"); types = request.args.getlist("type")
    natures = request.args.getlist("nature"); tags = request.args.getlist("tag")
    page = int(request.args.get("page", 1))
    sort = request.args.get("sort", "rank")
    order = request.args.get("order", "asc")

    where = "WHERE 1=1"; params = []
    if name: where += " AND college_name LIKE ?"; params.append(f"%{name}%")
    if provinces: where += " AND province IN ({})".format(",".join("?"*len(provinces))); params.extend(provinces)
    if types: where += " AND school_type IN ({})".format(",".join("?"*len(types))); params.extend(types)
    if natures: where += " AND nature IN ({})".format(",".join("?"*len(natures))); params.extend(natures)
    if tags:
        where += " AND (" + " OR ".join(["tag LIKE ?"]*len(tags)) + ")"; params.extend([f"%{t}%" for t in tags])

    total = query(f"SELECT count(1) as c FROM college_info {where}", params)[0]["c"]

    sort_col = "uniqueRank" if sort == "rank" else "college_name"
    # NULL/空值排最后
    null_first = "CASE WHEN uniqueRank='' OR uniqueRank IS NULL OR uniqueRank='-' THEN 1 ELSE 0 END"
    order_clause = f"ORDER BY {null_first}, cast({sort_col} AS int) {order.upper()}" if sort == "rank" else f"ORDER BY {sort_col} {order.upper()}"

    offset = (page-1)*50
    rows = query(f"SELECT college_name, uniqueRank, province, city, school_type, nature, tag FROM college_info {where} {order_clause} LIMIT 50 OFFSET {offset}", params)
    return jsonify({"rows": rows, "total": total, "page": page, "pages": max(1, math.ceil(total/50))})

# ─── 学校详情（支持位次/分数范围过滤） ───
@app.route("/api/school/<name>")
def api_school_detail(name):
    rank_min = request.args.get("rank_min", ""); rank_max = request.args.get("rank_max", "")
    score_min = request.args.get("score_min", ""); score_max = request.args.get("score_max", "")
    info = query("SELECT college_name, uniqueRank, province, city, school_type, nature, tag FROM college_info WHERE college_name=?", (name,))

    sqls = "SELECT year,batchName,enrollType,minScore,minScoreOrder,minCha,curriculum FROM schoolscore WHERE legalName=? AND minScoreOrder!=''"
    params = [name]
    if rank_min: sqls += " AND cast(minScoreOrder AS int) >= ?"; params.append(int(rank_min))
    if rank_max: sqls += " AND cast(minScoreOrder AS int) <= ?"; params.append(int(rank_max))
    if score_min: sqls += " AND cast(minScore AS int) >= ?"; params.append(int(score_min))
    if score_max: sqls += " AND cast(minScore AS int) <= ?"; params.append(int(score_max))
    sqls += " ORDER BY year DESC"
    scores = query(sqls, params)

    sqlm = "SELECT year,majorName,specialCourse,minScore,minScoreOrder,batchName FROM majorscore WHERE legalName=? AND minScoreOrder!=''"
    params_m = [name]
    if rank_min: sqlm += " AND cast(minScoreOrder AS int) >= ?"; params_m.append(int(rank_min))
    if rank_max: sqlm += " AND cast(minScoreOrder AS int) <= ?"; params_m.append(int(rank_max))
    if score_min: sqlm += " AND cast(minScore AS int) >= ?"; params_m.append(int(score_min))
    if score_max: sqlm += " AND cast(minScore AS int) <= ?"; params_m.append(int(score_max))
    sqlm += " ORDER BY year DESC"
    majors = query(sqlm, params_m)

    plans = query("SELECT year,major_name,enroll_num,tuition,lengthOfSchooling,selectSubjects,batch_name FROM college_plan WHERE legalName=? ORDER BY year DESC LIMIT 20", (name,))
    return jsonify({"info": info[0] if info else None, "scores": scores, "majors": majors, "plans": plans})

# ─── 专业反查（多年份、位次/分数范围过滤） ───
@app.route("/api/major_search")
def api_major_search():
    major = request.args.get("major", ""); years = request.args.getlist("year")
    rank_min = request.args.get("rank_min", ""); rank_max = request.args.get("rank_max", "")
    score_min = request.args.get("score_min", ""); score_max = request.args.get("score_max", "")
    sql = "SELECT year,legalName,majorName,specialCourse,minScore,minScoreOrder,batchName FROM majorscore WHERE 1=1"
    params = []
    if major:
        # 模糊搜索：专业名包含关键词，用 LIKE 匹配任意位置
        sql += " AND majorName LIKE ?"; params.append(f"%{major}%")
    if years: sql += " AND year IN ({})".format(",".join("?"*len(years))); params.extend(years)
    if rank_min: sql += " AND cast(minScoreOrder AS int) >= ?"; params.append(int(rank_min))
    if rank_max: sql += " AND cast(minScoreOrder AS int) <= ?"; params.append(int(rank_max))
    if score_min: sql += " AND cast(minScore AS int) >= ?"; params.append(int(score_min))
    if score_max: sql += " AND cast(minScore AS int) <= ?"; params.append(int(score_max))
    sql += " ORDER BY year DESC,cast(minScore AS int) DESC LIMIT 500"
    return jsonify(query(sql, params))

# ─── 招生计划（增强搜索，加省份/标签过滤） ───
@app.route("/api/plan_search")
def api_plan_search():
    major = request.args.get("major", ""); school = request.args.get("school", "")
    years = request.args.getlist("year")
    provinces = request.args.getlist("province")
    tags = request.args.getlist("tag")
    sql = "SELECT p.year,p.legalName,p.major_name,p.enroll_num,p.lengthOfSchooling,p.tuition,p.selectSubjects,p.batch_name FROM college_plan p"
    params = []
    if provinces or tags:
        sql += " JOIN college_info c ON p.legalName=c.college_name"
    sql += " WHERE 1=1"
    if major: sql += " AND p.major_name LIKE ?"; params.append(f"%{major}%")
    if school: sql += " AND p.legalName LIKE ?"; params.append(f"%{school}%")
    if years: sql += " AND p.year IN ({})".format(",".join("?"*len(years))); params.extend(years)
    if provinces: sql += " AND c.province IN ({})".format(",".join("?"*len(provinces))); params.extend(provinces)
    if tags: sql += " AND (" + " OR ".join(["c.tag LIKE ?"]*len(tags)) + ")"; params.extend([f"%{t}%" for t in tags])
    sql += " ORDER BY p.year DESC,p.legalName LIMIT 500"
    return jsonify(query(sql, params))

# ═══════════════════════════════════════
# 志愿推荐引擎（v2 完整版）
# ═══════════════════════════════════════

def parse_special_course(sc):
    """解析选科要求，返回 (first, conditions)
    first: '物理'/'历史'/None
    conditions: [{'type':'and'|'or'|'any', 'subjects':['化学','生物']}]
    """
    if not sc:
        return None, [{'type':'any','subjects':[]}]
    text = sc.replace("首选","").replace("再选","")
    first = None
    for p in ['物理','历史']:
        if p in text[:15]:
            first = p; break
    # 提取再选条件
    idx = text.find("再选")
    rest = text[idx+2:] if idx >= 0 else text
    if not rest.strip() or "不限" in rest:
        return first, [{'type':'any','subjects':[]}]
    conditions = []
    # 按 、和 / 分割（注意混合情况）
    parts = rest.split("、")
    for part in parts:
        part = part.strip().replace("(","").replace(")","")
        if "/" in part:
            subs = [x.strip() for x in part.split("/") if x.strip()]
            if subs: conditions.append({'type':'or','subjects':subs})
        elif part:
            conditions.append({'type':'and','subjects':[part]})
    return first, conditions if conditions else [{'type':'any','subjects':[]}]

def match_subjects_v2(sc, first_subj, second_subjs):
    """新版选科匹配
    first_subj: '物理'/'历史'
    second_subjs: ['化学','生物'] 按偏好顺序
    返回 (matched: bool, prefer_score: int)
    """
    first, conds = parse_special_course(sc)
    if first and first != first_subj:
        return False, 0
    if not conds or (len(conds)==1 and conds[0]['type']=='any'):
        return True, 10
    matched_any = False
    prefer_score = 0
    for cond in conds:
        if cond['type'] == 'and':
            if all(any(s in cs or cs in s for cs in cond['subjects']) for s in cond['subjects']):
                matched_any = True
                # 按考生偏好顺序加权
                for subj in cond['subjects']:
                    for idx, ps in enumerate(second_subjs):
                        if ps in subj or subj in ps:
                            prefer_score += max(0, 5 - idx)  # 第1偏好=5分, 第2=4分...
                            break
        elif cond['type'] == 'or':
            if any(any(ps in s or s in ps for s in cond['subjects']) for ps in second_subjs):
                matched_any = True
                # or 关系取考生偏好最高的科目加分
                for ps in second_subjs:
                    if any(ps in s or s in ps for s in cond['subjects']):
                        prefer_score += max(0, 5 - second_subjs.index(ps))
                        break
    return matched_any, min(10, prefer_score)

def calc_rank_score(ratio, drift):
    """位次匹配分 0~40"""
    if ratio < 1 - drift * 3 or ratio > 1 + drift * 3:
        return 0
    base = 40 * (1 - abs(ratio - 1) / drift) if drift > 0 else 40
    return max(0, min(40, base))

def calc_tag_score(tag_str, tags_filter, tag_mode):
    """标签分 0~25"""
    if not tags_filter:
        return 0
    tag_str = tag_str or ""
    points = {'985':10, '211':8, '双一流':5, '强基计划':2}
    if tag_mode == 'and':
        if all(t in tag_str for t in tags_filter):
            return 15
        return -1  # 不满足 AND
    else:  # or
        score = sum(points.get(t, 0) for t in tags_filter if t in tag_str)
        return min(25, score)

def calc_major_score(matched, keyword, keyword_mode, drift, ratio):
    """专业匹配分 0~20"""
    if not matched:
        return 0
    if keyword:
        if keyword_mode == 'mandatory' and not matched.get('keyword_hit'):
            return -1  # 强制模式不匹配
        if matched.get('keyword_hit'):
            r = matched['major_ratio']
            if abs(r - 1) <= drift: return 20
            elif abs(r - 1) <= drift * 2: return 12
            else: return 5
    # 有选科匹配但无关键字
    return 8 if matched.get('subject_matched') else 0

def calc_plan_score(plan_count):
    """计划分 0~15"""
    if plan_count is None or plan_count <= 0:
        return 0
    return min(15, math.log2(max(plan_count, 1)) * 3)

def pr(r):
    """安全转 int"""
    try: return int(float(str(r).replace(',','')))
    except: return 999999

@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    data = request.get_json()
    score = int(data.get("score", 0))
    rank = int(data.get("rank", 0))
    first_subj = data.get("firstSubject", "物理")        # 物理 / 历史
    second_subjs = data.get("secondSubjects", [])        # ['化学','生物']
    # 简称映射（college_plan.selectSubjects 用简称）
    SUBJ_SHORT = {"物理":"物","化学":"化","生物":"生","历史":"史","地理":"地","政治":"政"}
    first_short = SUBJ_SHORT.get(first_subj, first_subj[:1])
    second_short = [SUBJ_SHORT.get(s, s) for s in second_subjs]
    # 多关键词：中英文逗号分割
    import re
    keywords_raw = data.get("freeMajor", "")
    keywords = [k.strip() for k in re.split(r'[,，]', keywords_raw) if k.strip()]
    keyword_mode = data.get("freeMajorMode", "optional") # optional / mandatory / any
    tag_mode = data.get("tagMode", "or")                 # or / and
    tags_filter = data.get("tags", [])                   # ['985','211']
    provinces_filter = data.get("provinces", [])          # ['北京','上海']
    use_plan = data.get("usePlan", True)                 # 参考计划
    aggr = float(data.get("aggressiveness", 50))         # 0~100 越大越敢冲
    safety = float(data.get("safety", 50))               # 0~100 越大保底越多
    curriculum = "物理类" if first_subj == "物理" else "历史类"
    drift = 0.05 + aggr / 100 * 0.15       # 激进0→0.05 激进100→0.20

    # 动态年份：录取分用上年(2025)，招生计划用当年(2026)
    from datetime import datetime
    cur_year = datetime.now().year          # 2026
    score_year = str(cur_year - 1)          # 2025
    plan_year = str(cur_year)               # 2026

    # 从 schoolscore 获取学校位次（最低位次/最好录取线），去重
    schools_sql = """
        SELECT c.college_name, c.uniqueRank, c.province, c.tag,
               MIN(s.minScoreOrder) as minScoreOrder,
               MIN(s.minScore) as minScore
        FROM college_info c
        JOIN schoolscore s ON c.college_name = s.legalName
        WHERE s.year=? AND s.curriculum=? AND s.minScoreOrder!=''
    """
    schools_params = [score_year, curriculum]
    if provinces_filter:
        placeholders = ",".join(["?"]*len(provinces_filter))
        schools_sql += f" AND c.province IN ({placeholders})"
        schools_params.extend(provinces_filter)
    schools_sql += " GROUP BY c.college_name ORDER BY cast(c.uniqueRank AS int)"
    schools = query(schools_sql, schools_params)

    if not schools:
        return jsonify({"error": f"无 {score_year} 年 {curriculum} 录取数据"}), 400

    # 标签硬过滤
    if tags_filter and tag_mode == 'and':
        schools = [s for s in schools if all(t in (s["tag"] or "") for t in tags_filter)]

    result = {"year": score_year, "planYear": plan_year, "curriculum": curriculum,
              "aggressiveness": aggr, "safety": safety,
              "reach":[], "match":[], "safe":[]}

    for s in schools:
        tag_score = calc_tag_score(s.get("tag",""), tags_filter, tag_mode)
        if tag_score < 0: continue

        # 从 college_plan 获取 2026 年在招专业（选科匹配）
        plan_majors = query("""
            SELECT major_name, selectSubjects, enroll_num
            FROM college_plan WHERE legalName=? AND year=? AND curriculum=?
        """, (s["college_name"], plan_year, curriculum))

        matched_majors = []
        for pm in plan_majors:
            # 解析 selectSubjects 做选科匹配（格式：物+化 / 不限 / 物+化+生）
            ss = pm.get("selectSubjects","")
            if ss == "不限" or not ss.strip():
                subj_ok = True
            elif not second_subjs:
                # 无第二科目时，只需检查首选科目
                subj_ok = first_short in ss.replace("+"," ").split()
            else:
                required = [x.strip() for x in ss.replace("+"," ").split() if x.strip()]
                allowed = [first_short] + second_short
                subj_ok = all(r in allowed for r in required)

            if not subj_ok: continue

            # 查 majorscore 2025 获取历史分数参考
            ms = query("""
                SELECT minScore, minScoreOrder FROM majorscore
                WHERE legalName=? AND majorName=? AND year=? AND curriculum=? LIMIT 1
            """, (s["college_name"], pm["major_name"], score_year, curriculum))

            if ms:
                ref_score = ms[0]["minScore"]
                ref_rank = ms[0]["minScoreOrder"]
                is_new = False
            else:
                # 新专业：用该校该科类 majorscore 2025 均值
                avg = query("""
                    SELECT avg(cast(minScore AS int)) as s, avg(cast(minScoreOrder AS int)) as r
                    FROM majorscore WHERE legalName=? AND year=? AND curriculum=? AND minScore!='' AND minScoreOrder!=''
                """, (s["college_name"], score_year, curriculum))
                if avg and avg[0]["s"]:
                    ref_score = str(int(round(avg[0]["s"])))
                    ref_rank = str(int(round(avg[0]["r"])))
                    is_new = True
                else:
                    ref_score = s.get("minScore","")
                    ref_rank = s.get("minScoreOrder","")
                    is_new = True

            # 多关键词匹配（强制=OR过滤+不匹配跳过；可选=OR匹配但不过滤）
            keyword_hit = bool(keywords and any(k in (pm["major_name"] or "") for k in keywords))

            # 查计划数
            plan_this = query("SELECT enroll_num FROM college_plan WHERE legalName=? AND major_name=? AND year=? AND curriculum=? LIMIT 1",
                (s["college_name"], pm["major_name"], plan_year, curriculum))
            plan_last = query("SELECT enroll_num FROM college_plan WHERE legalName=? AND major_name=? AND year=? AND curriculum=? LIMIT 1",
                (s["college_name"], pm["major_name"], str(int(plan_year)-1), curriculum))

            matched_majors.append({
                "majorName": pm["major_name"] + (" ⚠️" if is_new else ""),
                "minScore": ref_score,
                "minScoreOrder": ref_rank,
                "keyword_hit": keyword_hit,
                "subject_matched": True,
                "prefer_score": 5,
                "planThisYear": plan_this[0]["enroll_num"] if plan_this else "-",
                "planLastYear": plan_last[0]["enroll_num"] if plan_last else "-"
            })

        if not matched_majors:
            continue
        if keyword_mode == 'mandatory' and keywords:
            kw_matched = [m for m in matched_majors if m['keyword_hit']]
            if not kw_matched: continue
            best = min(kw_matched, key=lambda m: pr(m['minScoreOrder']))
        else:
            best = min(matched_majors, key=lambda m: pr(m['minScoreOrder']))

        major_ratio = pr(best['minScoreOrder']) / rank if rank > 0 and best.get('minScoreOrder') else pr(s.get('minScoreOrder','')) / rank if rank > 0 and s.get('minScoreOrder') else 0
        prefer_total = sum(m['prefer_score'] for m in matched_majors[:10])

        # 查招生计划 + 趋势
        plan_count = None; plan_trend = 0
        if use_plan:
            plan = query(
                "SELECT enroll_num FROM college_plan WHERE legalName=? AND major_name=? AND year=? AND curriculum=? LIMIT 1",
                (s["college_name"], best["majorName"], plan_year, curriculum)
            )
            if plan:
                try: plan_count = int(float(plan[0]["enroll_num"]))
                except: pass
                # 查去年计划数算趋势
                last_plan = query(
                    "SELECT enroll_num FROM college_plan WHERE legalName=? AND major_name=? AND year=? AND curriculum=? LIMIT 1",
                    (s["college_name"], best["majorName"], str(int(plan_year)-1), curriculum)
                )
                if last_plan:
                    try:
                        last_n = int(float(last_plan[0]["enroll_num"]))
                        if last_n > 0:
                            ratio = plan_count / last_n
                            if ratio > 1.2: plan_trend = 2     # 扩招>20%
                            elif ratio < 0.8: plan_trend = -2  # 缩招>20%
                    except: pass
                else:
                    plan_trend = 2  # 新专业（去年无数据）→ 鼓励分
            else:
                avg = query(
                    "SELECT avg(cast(enroll_num AS int)) as a FROM college_plan WHERE legalName=? AND year=?",
                    (s["college_name"], plan_year)
                )
                if avg and avg[0]["a"]: plan_count = int(float(avg[0]["a"]))

        # 计算各项评分
        rank_score = calc_rank_score(major_ratio, drift)
        major_score = calc_major_score({
            'keyword_hit': best['keyword_hit'],
            'major_ratio': major_ratio,
            'subject_matched': True
        }, " ".join(keywords) if keywords else "", keyword_mode, drift, major_ratio)
        plan_score = calc_plan_score(plan_count) + plan_trend
        total = rank_score + tag_score + major_score + max(0, plan_score)  # plan不扣到负

        item = {
            "school": s["college_name"], "uniqueRank": s["uniqueRank"] or "-",
            "province": s["province"], "tag": s["tag"],
            "majorName": best["majorName"],
            "majorScore": best.get("minScore",""), "majorRank": best.get("minScoreOrder",""),
            "ratio": round(major_ratio, 4),
            "planCount": plan_count,
            "planThisYear": best.get("planThisYear"),
            "planLastYear": best.get("planLastYear"),
            "preferScore": prefer_total,
            "scores": {
                "rankScore": round(rank_score,1),
                "tagScore": round(tag_score,1),
                "majorScore": round(major_score,1),
                "planScore": round(plan_score,1),
                "total": round(total,1)
            }
        }

        # 分档逻辑：滑块 0~100，越大越激进/越保底
        reach_factor = 1.0 - aggr / 100 * 0.7     # 0%→1.0(跳过一切)  100%→0.3(可冲清北)
        safe_factor = 1.0 + safety / 100 * 4.0     # 0%→1.0(无保底)  100%→5.0(大量保底)
        school_rank = pr(best['minScoreOrder'])
        
        reach_lower = rank * reach_factor        # 冲刺最低位次
        match_upper = rank * (1.0 + safety / 100 * 2.0)  # 稳健上限：safety=0→1× safety=100→3×
        safe_upper = rank * safe_factor          # 保底最高位次
        
        if school_rank < reach_lower:            # 学校太好，够不着
            continue
        elif school_rank < rank:                 # 学校比你好 → 冲刺
            tier_key = "reach"
        elif school_rank < match_upper:          # 学校略差或相当 → 稳健
            tier_key = "match"
        elif school_rank < safe_upper:           # 学校明显更差 → 保底
            tier_key = "safe"
        else:                                    # 学校太差，跳过
            continue
        result[tier_key].append(item)

    for k in ("reach","match","safe"):
        result[k] = sorted(result[k], key=lambda x: -x["scores"]["total"])[:15]

    return jsonify(result)

# ─── AI 志愿分析 ───

@app.route("/api/ai/chat", methods=["POST"])
def api_ai_chat():
    data = request.get_json()
    message = data.get("message", "")
    history = data.get("history", [])
    reply, new_history = process_chat(history, message)
    return jsonify({"reply": reply, "history": new_history})

@app.route("/api/ai/reset", methods=["POST"])
def api_ai_reset():
    return jsonify({"history": []})

if __name__ == "__main__":
    print("高考志愿填报 - Web UI 启动: http://127.0.0.1:5080")
    app.run(host="0.0.0.0", port=5080, debug=True)
