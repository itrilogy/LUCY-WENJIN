# 高考志愿数据库 · 结构说明书

> **数据库文件** `gaokao2025.sqlite`  
> **引擎** SQLite3 · WAL 模式  
> **数据范围** 全国高校在**江西省**的录取数据  
> **覆盖年份** 2021 – 2026（库内实测；文档曾写 2020 但无 2020 数据）  
> **最后校验** 2026-08（本地库统计）

---

## 1. 表概览（实测行数）

| 表 | 用途 | 粒度 | 行数(实测) |
|---|------|------|:---:|
| `college_info` | 高校基本信息 | 1 行 / 校 | **3,000** |
| `schoolscore` | 录取分数线 | 1 行 / 校·年·科类·批次·类型 | **21,330** |
| `majorscore` | 专业分数线 | 1 行 / 校·年·科类·专业·批次 | **166,971** |
| `college_plan` | 招生计划 | 1 行 / 校·年·科类·专业 | **158,511** |
| `crawl_skip` | 爬虫负向缓存 | 1 行 / 校·年·科类·表 | **58,672** |
| `college_detail` | 预留详情（当前几乎不用） | — | 少量 |

路径：默认项目根目录；可用环境变量 `GAOKAO_DB` 覆盖。连接封装见 `core/db.py`。

---

## 2. college_info

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增 |
| `college_name` | TEXT | 学校全称 · 唯一索引 |
| `province` / `city` | TEXT | 所在省市 |
| `school_type` | TEXT | 综合类 / 理工类 … |
| `education` | TEXT | 本科 / 专科 |
| `nature` | TEXT | 公办 / 民办 |
| `uniqueRank` | TEXT | 校友会排名（TEXT，排序时 cast） |
| `tag` | TEXT | 985 · 211 · 双一流 · 强基计划 |
| `logo` | BLOB | 校徽（可选） |

**索引**: `UNIQUE INDEX idx_college_info_name ON (college_name)`

---

## 3. schoolscore

| 字段 | 类型 | 说明 |
|------|------|------|
| `legalName` | TEXT | 学校名 |
| `province` | TEXT | 固定 `江西` |
| `year` | TEXT | 2021–2025 |
| `curriculum` | TEXT | 见 §8 |
| `batchName` / `enrollType` | TEXT | 批次 / 招生类型 |
| `minScore` / `minScoreOrder` | TEXT | 最低分 / **最低位次**（数值语义，存 TEXT） |

**索引**: `UNIQUE (legalName, province, year, curriculum, batchName, enrollType)`

---

## 4. majorscore

| 字段 | 类型 | 说明 |
|------|------|------|
| `legalName` / `majorName` | TEXT | 学校 / 专业全称 |
| `year` / `curriculum` | TEXT | 年 / 科类 |
| `minScore` / `minScoreOrder` | TEXT | 专业最低分 / 位次 |
| `specialCourse` | TEXT | **长文案**选科：`首选物理，再选化学` |
| `simplifySpecialCourse` | TEXT | 简化选科 |

**索引**: `UNIQUE (legalName, majorName, province, year, curriculum, batchName)`  
另有 lookup 索引：`(legalName, majorName, year, curriculum)`

---

## 5. college_plan

| 字段 | 类型 | 说明 |
|------|------|------|
| `legalName` / `major_name` | TEXT | 学校 / 专业 |
| `year` | TEXT | 2021–**2026** |
| `curriculum` | TEXT | 科类 |
| `enroll_num` | TEXT | 计划人数 |
| `selectSubjects` | TEXT | **简称**选科，见 §8.1 |
| `tuition` / `lengthOfSchooling` / `batch_name` | TEXT | 学费 / 学制 / 批次 |

**唯一索引（注意）**:

```sql
UNIQUE (legalName, major_name, province, year, batch_name)
-- 不含 curriculum：若同专业同年同批次跨科类，存在冲突风险
-- 用 scripts/data_quality.py 检测
```

lookup 索引含 `curriculum`：`(legalName, major_name, year, curriculum)`

---

## 6. crawl_skip

负向缓存：已确认某校·年·科类·表无数据。

| 字段 | 说明 |
|------|------|
| PK `(school_name, year, curriculum, table_name)` | |
| `checked_at` | 标记时间 |

---

## 7. 数据关系

```
college_info.college_name
  ├─→ schoolscore.legalName
  ├─→ majorscore.legalName
  └─→ college_plan.legalName
```

推荐时 **plan.major_name ↔ majorscore.majorName** 需模糊匹配（括号后缀、中外合作等），见 `core/recommend/engine.py`。

---

## 8. 科类说明

| 年份 | 科类取值 | 高考制度 |
|------|---------|------|
| 2021 – 2023 | `理科` `文科` | 旧高考 |
| 2024 – 2026 | `物理类` `历史类` | 新高考 3+1+2 |

### 8.1 `college_plan.selectSubjects`（实测高频）

| 值 | 约条数(2026) | 含义 |
|----|-------------:|------|
| `物+化` | ~12.8k | 物理+化学 |
| **`物+不限`** | **~12.0k** | 首选物理，再选不限 |
| **`史+不限`** | **~4.6k** | 首选历史，再选不限 |
| `物+(化+生)` | ~0.3k | 再选化学+生物 |
| `史+政` | ~0.3k | 历史+政治 |
| `物+生` / `物+地` / `史+地` … | 较少 | 其他组合 |

解析实现：`core/recommend/subjects.py` 的 `match_select_subjects`  
（必须忽略 `不限` token，并正确处理括号内 AND）。

### 8.2 `majorscore.specialCourse`（长文案样例）

- `首选物理，再选化学`
- `首选物理，再选不限`
- `首选历史，再选思想政治`
- `首选物理，再选化学、生物(2科必选)`

---

## 9. 年份约定

| 表 | 库内范围 | 最新 | 说明 |
|---|---------|:---:|------|
| `college_info` | — | — | 静态清单 |
| `schoolscore` | 2021–2025 | 2025 | 当年录取未出分 |
| `majorscore` | 2021–2025 | 2025 | 同上 |
| `college_plan` | 2021–2026 | **2026** | 提前公布 |

**推荐规则**（`core/config.py` 可环境变量覆盖）:

```
college_plan(GAOKAO_PLAN_YEAR) + schoolscore/majorscore(GAOKAO_SCORE_YEAR)
默认: plan=当年, score=当年-1
```

### 覆盖缺口（实测）

| 指标 | 约值 |
|------|-----:|
| 2026 plan 学校数 | 2166 |
| 2025 schoolscore 学校数 | 1969 |
| plan 有但无上年录取分 | ~238 |

有 plan 无 score 的专业会走学校 majorscore 均值回退（结果中标记 ⚠️）。

---

## 10. 数据质量命令

```bash
python3 scripts/data_quality.py   # 生成 scripts/data_quality_report.json
python3 scripts/probe_api.py      # 外网 API 契约探针（可选）
```

---

## 11. 一分一段表 score_segment（百度官方源）

> 数据源：`https://opendata.baidu.com/api.php` · `resource_id=50266` · `query=一分一段`  
> 爬取：`python3 scripts/crawl_score_segment.py --all --calibrate`  
> 实现：`core/baidu_segment.py` + `core/rank_table.py`

| 字段 | 说明 |
|------|------|
| `year` / `curriculum` / `score` | PK 维度 |
| `rank_min` / `rank_max` | 该分位次区间（越小越好） |
| `count` | 本分人数 |
| `source` | `baidu` 官方卡片 / `approx` schoolscore 近似 |
| `surpass` / `tips` | 超过比例 / 批次提示 |

另表 `score_batchline`：批次线（本科批/专科批）。

**江西已入库（实测）**：2021–2026，约 **6800+** 行 baidu 源。

查询优先 `source=baidu`。分→位默认取 `rank_max`（同分最差位次，偏保守）。

### 概率校准 meta · model_meta

| key | 内容 |
|-----|------|
| `prob_calib:物理类` | k / bias / σ / 学校级 σ |
| `prob_calib:latest` | 最近一次校准 |

---

## 12. 已知设计债

1. 分数/位次/计划人数多为 **TEXT**，查询侧 `cast AS int`
2. plan 唯一键 **不含 curriculum**
3. plan 与 majorscore **专业名格式不一致**，依赖模糊匹配
4. 选科双格式（简称 vs 长文案），推荐以 plan 简称为准
5. 概率校准为伪标签 + 跨年波动启发式，非官方录取率
