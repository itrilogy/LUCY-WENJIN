# 鹿溪志愿 · 演进路线图

> 状态更新：2026-08 · **v1.2.2 文档与品牌** · Phase 3 + 一分一段校准已落地

## 总览

```
Phase 0  关键修复与安全底线     ✅
Phase 1  模块化 + 测试 + 前端拆分 ✅
Phase 2  数据质量 / 运维 / 限流   ✅
Phase 3  算法增强与产品化        ✅
  └ 百度一分一段 + 概率校准      ✅
  └ 文档修订 + 品牌 LOGO/favicon ✅
Phase 4  深化（可选）            ⬜ 见文末
```

---

## Phase 0–2 ✅

见历史 CHANGELOG / 此前 ROADMAP。

---

## Phase 3 — 已完成 ✅

| 方向 | 状态 | 实现 |
|------|:----:|------|
| 录取概率模型 | ✅ | `core/recommend/probability.py`，结果字段 `admit` |
| 专业簇/职业库 | ✅ | `core/recommend/clusters.py`，推荐页「专业簇」开关 |
| AI 多工具 | ✅ | recommend / search_major / compare_schools / explain_admission |
| 流式 SSE | ✅ | `POST /api/ai/stream` + 前端 `ai.js` |
| 云端志愿表 | ✅ | `user_shortlist` 表 + session cookie / `X-Session-Id` |
| 一分一段近似 | ✅ | `score_segment` + 从 schoolscore 重建 |
| CSV 导出 | ✅ | 推荐结果 / 备选清单 |
| 数据质量看板 | ✅ | 侧栏「数据质量」页 + `/api/quality` |
| 容器化 Docker | ✅ | `Dockerfile` + `docker-compose.yml` |

### 新增 API（摘要）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ai/stream` | SSE 流式对话 |
| GET | `/api/clusters` | 专业簇字典 |
| GET | `/api/rank/score_to_rank` | 分→位 |
| GET | `/api/rank/rank_to_score` | 位→分 |
| GET | `/api/rank/convert` | 跨年位次粗换算 |
| POST | `/api/rank/rebuild` | 重建近似一分一段 |
| GET/POST/DELETE | `/api/shortlist` | 云端备选 |
| POST | `/api/shortlist/sync` | 整表同步 |
| POST | `/api/recommend/export.csv` | 推荐 CSV |
| GET | `/api/quality` | 质量看板数据 |

---

## Phase 4 — 可选深化 ⬜

| 方向 | 描述 | 优先级 |
|------|------|:------:|
| 官方一分一段 CSV 导入 | 替换 approx 源 | 高 |
| 校准概率模型 | 用历史「压线录取」样本拟合 | 中 |
| 完整用户账号 | 手机/邮箱登录，多设备 | 中 |
| 江西专业组规则 | 组内调剂约束 | 中 |
| 多省数据源 | 配置化 province | 低 |
| AI RAG 章程/就业 | 向量检索 | 低 |

---

## 本地命令

```bash
python3 -m pytest tests/ -q          # 21+ 用例
python3 scripts/data_quality.py
python3 app.py

# Docker
docker compose up --build
# 浏览器 http://127.0.0.1:5080
```

---

## 架构（v1.2）

```
app.py
ai_recommend.py          # 多工具 + SSE
core/
  recommend/
    engine.py            # +概率 +专业簇
    probability.py
    clusters.py
    scoring.py / subjects.py
  rank_table.py          # 一分一段
  shortlist_store.py     # 云端备选
  tools.py               # AI/API 工具
  config / db / security
Dockerfile / docker-compose.yml
static/js/               # +quality.js，推荐/AI/备选增强
```
