#!/usr/bin/env python3
"""高考志愿填报助手 - Web UI（江西版）"""

from __future__ import annotations

import math
import os
import sys

# 保证项目根在 path 上
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import csv
import io
import json

from flask import Flask, Response, jsonify, make_response, render_template, request

from ai_recommend import process_chat, process_chat_stream
from core.config import DEBUG, HOST, PORT, SECRET_KEY
from core.db import query
from core.rank_table import (
    convert_rank_across_years,
    rebuild_approx_from_schoolscore,
    rank_to_score,
    score_to_rank,
    segment_stats,
)
from core.recommend import list_clusters, run_recommend
from core.security import protect
from core.shortlist_store import (
    add_item,
    clear_items,
    list_items,
    new_session_id,
    remove_item,
    replace_all,
    to_csv,
)
from core.tools import compare_schools, search_major

app = Flask(__name__)
app.secret_key = SECRET_KEY

SESSION_COOKIE = "gk_sid"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def api_health():
    from core.config import PLAN_YEAR, SCORE_YEAR
    from core.db import get_db_path

    return jsonify(
        {
            "ok": True,
            "db": str(get_db_path()),
            "scoreYear": SCORE_YEAR,
            "planYear": PLAN_YEAR,
        }
    )


@app.route("/api/filters")
@protect
def api_filters():
    return jsonify(
        {
            "provinces": [
                r["province"]
                for r in query(
                    "SELECT DISTINCT province FROM college_info WHERE province!='' ORDER BY province"
                )
            ],
            "types": [
                r["school_type"]
                for r in query(
                    "SELECT DISTINCT school_type FROM college_info WHERE school_type!='' ORDER BY school_type"
                )
            ],
            "natures": [
                r["nature"]
                for r in query(
                    "SELECT DISTINCT nature FROM college_info WHERE nature!='' ORDER BY nature"
                )
            ],
            "years": [
                r["year"]
                for r in query(
                    "SELECT DISTINCT year FROM majorscore ORDER BY year DESC"
                )
            ],
            "planYears": [
                r["year"]
                for r in query(
                    "SELECT DISTINCT year FROM college_plan ORDER BY year DESC"
                )
            ],
        }
    )


@app.route("/api/schools")
@protect
def api_schools():
    name = request.args.get("name", "")
    provinces = request.args.getlist("province")
    types = request.args.getlist("type")
    natures = request.args.getlist("nature")
    tags = request.args.getlist("tag")
    page = max(1, int(request.args.get("page", 1)))
    sort = request.args.get("sort", "rank")
    order = request.args.get("order", "asc")
    if order.upper() not in ("ASC", "DESC"):
        order = "asc"

    where = "WHERE 1=1"
    params: list = []
    if name:
        where += " AND college_name LIKE ?"
        params.append(f"%{name}%")
    if provinces:
        where += " AND province IN ({})".format(",".join("?" * len(provinces)))
        params.extend(provinces)
    if types:
        where += " AND school_type IN ({})".format(",".join("?" * len(types)))
        params.extend(types)
    if natures:
        where += " AND nature IN ({})".format(",".join("?" * len(natures)))
        params.extend(natures)
    if tags:
        where += " AND (" + " OR ".join(["tag LIKE ?"] * len(tags)) + ")"
        params.extend([f"%{t}%" for t in tags])

    total = query(f"SELECT count(1) as c FROM college_info {where}", params)[0]["c"]

    sort_col = "uniqueRank" if sort == "rank" else "college_name"
    null_first = (
        "CASE WHEN uniqueRank='' OR uniqueRank IS NULL OR uniqueRank='-' THEN 1 ELSE 0 END"
    )
    if sort == "rank":
        order_clause = (
            f"ORDER BY {null_first}, cast({sort_col} AS int) {order.upper()}"
        )
    else:
        order_clause = f"ORDER BY {sort_col} {order.upper()}"

    offset = (page - 1) * 50
    rows = query(
        f"SELECT college_name, uniqueRank, province, city, school_type, nature, tag "
        f"FROM college_info {where} {order_clause} LIMIT 50 OFFSET {offset}",
        params,
    )
    return jsonify(
        {
            "rows": rows,
            "total": total,
            "page": page,
            "pages": max(1, math.ceil(total / 50)),
        }
    )


@app.route("/api/school/<name>")
@protect
def api_school_detail(name):
    rank_min = request.args.get("rank_min", "")
    rank_max = request.args.get("rank_max", "")
    score_min = request.args.get("score_min", "")
    score_max = request.args.get("score_max", "")
    info = query(
        "SELECT college_name, uniqueRank, province, city, school_type, nature, tag "
        "FROM college_info WHERE college_name=?",
        (name,),
    )

    sqls = (
        "SELECT year,batchName,enrollType,minScore,minScoreOrder,minCha,curriculum "
        "FROM schoolscore WHERE legalName=? AND minScoreOrder!=''"
    )
    params: list = [name]
    if rank_min:
        sqls += " AND cast(minScoreOrder AS int) >= ?"
        params.append(int(rank_min))
    if rank_max:
        sqls += " AND cast(minScoreOrder AS int) <= ?"
        params.append(int(rank_max))
    if score_min:
        sqls += " AND cast(minScore AS int) >= ?"
        params.append(int(score_min))
    if score_max:
        sqls += " AND cast(minScore AS int) <= ?"
        params.append(int(score_max))
    sqls += " ORDER BY year DESC"
    scores = query(sqls, params)

    sqlm = (
        "SELECT year,majorName,specialCourse,minScore,minScoreOrder,batchName "
        "FROM majorscore WHERE legalName=? AND minScoreOrder!=''"
    )
    params_m: list = [name]
    if rank_min:
        sqlm += " AND cast(minScoreOrder AS int) >= ?"
        params_m.append(int(rank_min))
    if rank_max:
        sqlm += " AND cast(minScoreOrder AS int) <= ?"
        params_m.append(int(rank_max))
    if score_min:
        sqlm += " AND cast(minScore AS int) >= ?"
        params_m.append(int(score_min))
    if score_max:
        sqlm += " AND cast(minScore AS int) <= ?"
        params_m.append(int(score_max))
    sqlm += " ORDER BY year DESC"
    majors = query(sqlm, params_m)

    plans = query(
        "SELECT year,major_name,enroll_num,tuition,lengthOfSchooling,selectSubjects,batch_name "
        "FROM college_plan WHERE legalName=? ORDER BY year DESC LIMIT 50",
        (name,),
    )
    return jsonify(
        {
            "info": info[0] if info else None,
            "scores": scores,
            "majors": majors,
            "plans": plans,
        }
    )


@app.route("/api/major_search")
@protect
def api_major_search():
    major = request.args.get("major", "")
    years = request.args.getlist("year")
    rank_min = request.args.get("rank_min", "")
    rank_max = request.args.get("rank_max", "")
    score_min = request.args.get("score_min", "")
    score_max = request.args.get("score_max", "")
    sql = (
        "SELECT year,legalName,majorName,specialCourse,minScore,minScoreOrder,batchName "
        "FROM majorscore WHERE 1=1"
    )
    params: list = []
    if major:
        sql += " AND majorName LIKE ?"
        params.append(f"%{major}%")
    if years:
        sql += " AND year IN ({})".format(",".join("?" * len(years)))
        params.extend(years)
    if rank_min:
        sql += " AND cast(minScoreOrder AS int) >= ?"
        params.append(int(rank_min))
    if rank_max:
        sql += " AND cast(minScoreOrder AS int) <= ?"
        params.append(int(rank_max))
    if score_min:
        sql += " AND cast(minScore AS int) >= ?"
        params.append(int(score_min))
    if score_max:
        sql += " AND cast(minScore AS int) <= ?"
        params.append(int(score_max))
    sql += " ORDER BY year DESC,cast(minScore AS int) DESC LIMIT 500"
    return jsonify(query(sql, params))


@app.route("/api/plan_search")
@protect
def api_plan_search():
    major = request.args.get("major", "")
    school = request.args.get("school", "")
    years = request.args.getlist("year")
    provinces = request.args.getlist("province")
    tags = request.args.getlist("tag")
    sql = (
        "SELECT p.year,p.legalName,p.major_name,p.enroll_num,p.lengthOfSchooling,"
        "p.tuition,p.selectSubjects,p.batch_name FROM college_plan p"
    )
    params: list = []
    if provinces or tags:
        sql += " JOIN college_info c ON p.legalName=c.college_name"
    sql += " WHERE 1=1"
    if major:
        sql += " AND p.major_name LIKE ?"
        params.append(f"%{major}%")
    if school:
        sql += " AND p.legalName LIKE ?"
        params.append(f"%{school}%")
    if years:
        sql += " AND p.year IN ({})".format(",".join("?" * len(years)))
        params.extend(years)
    if provinces:
        sql += " AND c.province IN ({})".format(",".join("?" * len(provinces)))
        params.extend(provinces)
    if tags:
        sql += " AND (" + " OR ".join(["c.tag LIKE ?"] * len(tags)) + ")"
        params.extend([f"%{t}%" for t in tags])
    sql += " ORDER BY p.year DESC,p.legalName LIMIT 500"
    return jsonify(query(sql, params))


@app.route("/api/recommend", methods=["POST"])
@protect
def api_recommend():
    data = request.get_json(silent=True) or {}
    result = run_recommend(data)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/ai/chat", methods=["POST"])
@protect
def api_ai_chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    history = data.get("history", [])
    reply, new_history = process_chat(history, message)
    return jsonify({"reply": reply, "history": new_history})


@app.route("/api/ai/stream", methods=["POST"])
@protect
def api_ai_stream():
    """SSE 流式 AI 对话。"""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    history = data.get("history", [])

    def event_stream():
        for ev in process_chat_stream(history, message):
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/ai/reset", methods=["POST"])
@protect
def api_ai_reset():
    return jsonify({"history": []})


@app.route("/api/meta")
@protect
def api_meta():
    """数据元信息：供前端/运维查看年份与覆盖。"""
    from core.config import LAST_PLAN_YEAR, PLAN_YEAR, SCORE_YEAR

    counts = {
        "college_info": query("SELECT count(1) c FROM college_info")[0]["c"],
        "schoolscore": query("SELECT count(1) c FROM schoolscore")[0]["c"],
        "majorscore": query("SELECT count(1) c FROM majorscore")[0]["c"],
        "college_plan": query("SELECT count(1) c FROM college_plan")[0]["c"],
    }
    return jsonify(
        {
            "scoreYear": SCORE_YEAR,
            "planYear": PLAN_YEAR,
            "lastPlanYear": LAST_PLAN_YEAR,
            "counts": counts,
            "clusters": list(list_clusters().keys()),
        }
    )


# ─── Phase3: 专业簇 / 工具 / 分位次 / 备选云端 / 导出 / 质量 ───


@app.route("/api/clusters")
@protect
def api_clusters():
    return jsonify(list_clusters())


@app.route("/api/tools/search_major", methods=["POST"])
@protect
def api_tool_search_major():
    data = request.get_json(silent=True) or {}
    return jsonify(
        search_major(
            data.get("major") or "",
            data.get("year"),
            data.get("curriculum"),
            int(data.get("limit") or 30),
        )
    )


@app.route("/api/tools/compare_schools", methods=["POST"])
@protect
def api_tool_compare():
    data = request.get_json(silent=True) or {}
    return jsonify(
        compare_schools(
            list(data.get("schools") or []),
            data.get("year"),
            data.get("curriculum") or "物理类",
        )
    )


@app.route("/api/rank/score_to_rank")
@protect
def api_score_to_rank():
    score = int(request.args.get("score") or 0)
    year = request.args.get("year")
    curriculum = request.args.get("curriculum") or "物理类"
    if score <= 0:
        return jsonify({"error": "score 无效"}), 400
    r = score_to_rank(score, year, curriculum)
    if not r:
        return jsonify({"error": "无对照数据，请先 rebuild"}), 404
    return jsonify(r)


@app.route("/api/rank/rank_to_score")
@protect
def api_rank_to_score():
    rank = int(request.args.get("rank") or 0)
    year = request.args.get("year")
    curriculum = request.args.get("curriculum") or "物理类"
    if rank <= 0:
        return jsonify({"error": "rank 无效"}), 400
    r = rank_to_score(rank, year, curriculum)
    if not r:
        return jsonify({"error": "无对照数据"}), 404
    return jsonify(r)


@app.route("/api/rank/convert")
@protect
def api_rank_convert():
    rank = int(request.args.get("rank") or 0)
    from_year = request.args.get("from") or ""
    to_year = request.args.get("to") or ""
    curriculum = request.args.get("curriculum") or "物理类"
    if not (rank and from_year and to_year):
        return jsonify({"error": "需要 rank, from, to"}), 400
    r = convert_rank_across_years(rank, from_year, to_year, curriculum)
    if not r:
        return jsonify({"error": "换算失败"}), 404
    return jsonify(r)


@app.route("/api/rank/rebuild", methods=["POST"])
@protect
def api_rank_rebuild():
    """重建近似表，或 source=baidu 时从百度拉取。"""
    data = request.get_json(silent=True) or {}
    source = (data.get("source") or "approx").lower()
    year = data.get("year")
    curriculum = data.get("curriculum")
    if source == "baidu":
        from core.baidu_segment import JIANGXI_YEARS, fetch_segment
        from core.config import PROVINCE_DEFAULT
        from core.rank_table import upsert_baidu_rows

        total = 0
        jobs = []
        if year and curriculum:
            jobs = [(str(year), curriculum)]
        elif year:
            # 该年常见科类
            y = str(year)
            cats = ["物理类", "历史类"] if int(y) >= 2024 else ["理科", "文科"]
            jobs = [(y, c) for c in cats]
        else:
            jobs = [(y, c) for y, cats in JIANGXI_YEARS for c in cats]
        errors = []
        for y, c in jobs:
            try:
                seg = fetch_segment(PROVINCE_DEFAULT, y, c)
                if seg.get("ok"):
                    total += upsert_baidu_rows(y, c, seg["rows"], seg.get("batchline"))
            except Exception as e:
                errors.append(f"{y}/{c}: {e}")
        return jsonify(
            {
                "ok": True,
                "source": "baidu",
                "rows": total,
                "errors": errors,
                "stats": segment_stats(year),
            }
        )
    n = rebuild_approx_from_schoolscore(year, curriculum)
    return jsonify({"ok": True, "source": "approx", "rows": n, "stats": segment_stats(year)})


@app.route("/api/rank/stats")
@protect
def api_rank_stats():
    return jsonify(segment_stats(request.args.get("year")))


@app.route("/api/rank/calibrate", methods=["POST"])
@protect
def api_rank_calibrate():
    """运行概率模型校准（依赖 majorscore 跨年 + 可选一分一段）。"""
    from core.recommend.calibrate import run_calibration

    data = request.get_json(silent=True) or {}
    curriculum = data.get("curriculum") or "物理类"
    cal = run_calibration(
        curriculum,
        data.get("scoreYear"),
        data.get("prevYear"),
    )
    return jsonify({"ok": True, "calibration": cal})


@app.route("/api/rank/calibration")
@protect
def api_rank_calibration_get():
    from core.recommend.calibrate import get_calibration, load_meta

    curriculum = request.args.get("curriculum") or "物理类"
    return jsonify(
        {
            "calibration": get_calibration(curriculum),
            "latest": load_meta("prob_calib:latest"),
        }
    )


def _session_id() -> str:
    sid = request.cookies.get(SESSION_COOKIE) or request.headers.get("X-Session-Id")
    if not sid:
        sid = (request.get_json(silent=True) or {}).get("sessionId") or ""
    return sid or ""


def _with_session(resp, sid: str):
    resp.set_cookie(
        SESSION_COOKIE, sid, max_age=86400 * 180, httponly=False, samesite="Lax"
    )
    return resp


@app.route("/api/shortlist", methods=["GET"])
@protect
def api_shortlist_get():
    sid = _session_id() or new_session_id()
    items = list_items(sid)
    resp = make_response(jsonify({"sessionId": sid, "items": items}))
    return _with_session(resp, sid)


@app.route("/api/shortlist", methods=["POST"])
@protect
def api_shortlist_add():
    data = request.get_json(silent=True) or {}
    sid = _session_id() or data.get("sessionId") or new_session_id()
    item = data.get("item") or data
    add_item(sid, item)
    resp = make_response(jsonify({"ok": True, "sessionId": sid, "items": list_items(sid)}))
    return _with_session(resp, sid)


@app.route("/api/shortlist/sync", methods=["POST"])
@protect
def api_shortlist_sync():
    """用本地列表整表覆盖云端（合并入口）。"""
    data = request.get_json(silent=True) or {}
    sid = _session_id() or data.get("sessionId") or new_session_id()
    items = data.get("items") or []
    n = replace_all(sid, items)
    resp = make_response(
        jsonify({"ok": True, "sessionId": sid, "count": n, "items": list_items(sid)})
    )
    return _with_session(resp, sid)


@app.route("/api/shortlist", methods=["DELETE"])
@protect
def api_shortlist_del():
    data = request.get_json(silent=True) or {}
    sid = _session_id() or data.get("sessionId") or ""
    if not sid:
        return jsonify({"error": "无 session"}), 400
    key = data.get("key") or request.args.get("key")
    if key:
        remove_item(sid, key)
    else:
        clear_items(sid)
    resp = make_response(jsonify({"ok": True, "items": list_items(sid)}))
    return _with_session(resp, sid)


@app.route("/api/shortlist/export.csv")
@protect
def api_shortlist_csv():
    sid = _session_id()
    if not sid:
        return jsonify({"error": "无 session"}), 400
    body = to_csv(sid)
    return Response(
        body,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=shortlist.csv",
        },
    )


@app.route("/api/recommend/export.csv", methods=["POST"])
@protect
def api_recommend_csv():
    data = request.get_json(silent=True) or {}
    result = data if "reach" in data else run_recommend(data)
    if "error" in result:
        return jsonify(result), 400
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "档位",
            "学校",
            "专业",
            "最低分",
            "最低位次",
            "位次比",
            "录取概率",
            "概率区间",
            "总分",
            "计划今年",
            "计划去年",
            "省份",
            "标签",
        ]
    )
    for tier, label in (
        ("reach", "冲刺"),
        ("match", "稳健"),
        ("safe", "保底"),
    ):
        for it in result.get(tier) or []:
            adm = it.get("admit") or {}
            sc = it.get("scores") or {}
            w.writerow(
                [
                    label,
                    it.get("school"),
                    it.get("majorName"),
                    it.get("majorScore"),
                    it.get("majorRank"),
                    it.get("ratio"),
                    adm.get("pct"),
                    adm.get("rangePct"),
                    sc.get("total"),
                    it.get("planThisYear"),
                    it.get("planLastYear"),
                    it.get("province"),
                    it.get("tag"),
                ]
            )
    return Response(
        "\ufeff" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=recommend.csv",
        },
    )


@app.route("/api/quality")
@protect
def api_quality():
    """轻量数据质量看板 API。"""
    from core.config import PLAN_YEAR, SCORE_YEAR
    from core.recommend.calibrate import load_meta

    plan_schools = query(
        "SELECT count(DISTINCT legalName) c FROM college_plan WHERE year=?",
        (PLAN_YEAR,),
    )[0]["c"]
    score_schools = query(
        "SELECT count(DISTINCT legalName) c FROM schoolscore WHERE year=?",
        (SCORE_YEAR,),
    )[0]["c"]
    ss_top = query(
        """
        SELECT selectSubjects, count(1) n FROM college_plan
        WHERE year=? GROUP BY selectSubjects ORDER BY n DESC LIMIT 12
        """,
        (PLAN_YEAR,),
    )
    # 多年 rank 表统计
    rank_all = []
    for y in ("2026", "2025", "2024", "2023", "2022", "2021"):
        rank_all.extend(segment_stats(y))
    return jsonify(
        {
            "scoreYear": SCORE_YEAR,
            "planYear": PLAN_YEAR,
            "counts": {
                "college_info": query("SELECT count(1) c FROM college_info")[0]["c"],
                "schoolscore": query("SELECT count(1) c FROM schoolscore")[0]["c"],
                "majorscore": query("SELECT count(1) c FROM majorscore")[0]["c"],
                "college_plan": query("SELECT count(1) c FROM college_plan")[0]["c"],
            },
            "coverage": {
                "planSchools": plan_schools,
                "scoreSchools": score_schools,
            },
            "selectSubjectsTop": ss_top,
            "rankTable": rank_all or segment_stats(SCORE_YEAR),
            "calibration": load_meta("prob_calib:latest"),
        }
    )


if __name__ == "__main__":
    print(f"鹿溪志愿 Web UI: http://127.0.0.1:{PORT}  (debug={DEBUG})")
    app.run(host=HOST, port=PORT, debug=DEBUG, threaded=True)
