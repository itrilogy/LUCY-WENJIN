# 高考志愿数据库 · 结构说明书

> **数据库文件** `gaokao2025.sqlite`  
> **引擎** SQLite3 · WAL 模式  
> **数据范围** 全国高校在江西省的录取数据  
> **覆盖年份** 2020 – 2026  
> **最后更新** 2026-06  

---

## 目录

1. 表概览
2. college_info · 高校基本信息
3. schoolscore · 录取分数线
4. majorscore · 专业分数线
5. college_plan · 招生计划
6. crawl_skip · 爬虫缓存
7. 数据关系
8. 科类说明
9. 年份约定

---

## 1. 表概览

| 表 | 用途 | 粒度 | 行数(约) |
|---|------|------|:---:|
| `college_info` | 高校基本信息 | 1 行 / 校 | 3,000 |
| `schoolscore` | 录取分数线 | 1 行 / 校·年·科类·批次·类型 | 21,000 |
| `majorscore` | 专业分数线 | 1 行 / 校·年·科类·专业·批次 | 160,000 |
| `college_plan` | 招生计划 | 1 行 / 校·年·科类·专业 | 80,000 |
| `crawl_skip` | 爬虫负向缓存 | 1 行 / 校·年·科类·表 | 8,000 |

---

## 2. college_info

> 全国高校目录，带校友会排名和学校标签

| 字段 | 类型 | 空 | 说明 |
|------|------|:--:|------|
| `id` | INTEGER PK | — | 自增 |
| `college_name` | TEXT | — | 学校全称 · 唯一索引 |
| `province` | TEXT | ✓ | 所在省 |
| `city` | TEXT | ✓ | 所在城市 |
| `school_type` | TEXT | ✓ | 综合类 / 理工类 / 师范类 ... |
| `education` | TEXT | ✓ | 本科 / 专科 |
| `nature` | TEXT | ✓ | 公办 / 民办 |
| `uniqueRank` | TEXT | ✓ | 校友会排名 |
| `tag` | TEXT | ✓ | 985 · 211 · 双一流 · 强基计划 |
| `batch` | TEXT | ✓ | 招生批次 |
| `logo` | BLOB | ✓ | 校徽图片 (Base64 PNG) |

**索引**: `UNIQUE INDEX idx_college_info_name ON (college_name)`

---

## 3. schoolscore

> 学校级录取分数线

| 字段 | 类型 | 说明 |
|------|------|------|
| `legalName` | TEXT | 学校名 |
| `province` | TEXT | 考生省份 · 固定 `江西` |
| `year` | TEXT | 年份 2020-2025 |
| `curriculum` | TEXT | 理科/文科 (2020-2023) · 物理类/历史类 (2024-2025) |
| `batchName` | TEXT | 本科批 / 提前批 / 本科一批 |
| `enrollType` | TEXT | 普通类 / 国家专项 / 地方专项 / 中外合作 |
| `minScore` | TEXT | 最低录取分数 |
| `minScoreOrder` | TEXT | **最低位次** |
| `minCha` | TEXT | 批次线差 |

**索引**: `UNIQUE INDEX idx_schoolscore ON (legalName, province, year, curriculum, batchName, enrollType)`

---

## 4. majorscore

> 专业级录取分数线

| 字段 | 类型 | 说明 |
|------|------|------|
| `legalName` | TEXT | 学校名 |
| `majorName` | TEXT | **专业全称** |
| `year` | TEXT | 2020-2025 |
| `curriculum` | TEXT | 科类 |
| `batchName` | TEXT | 批次 |
| `minScore` | TEXT | 专业最低分 |
| `minScoreOrder` | TEXT | **专业最低位次** |
| `specialCourse` | TEXT | 选科要求 · `首选物理，再选化学` |
| `simplifySpecialCourse` | TEXT | 简化选科 · `物+化` |

**索引**: `UNIQUE INDEX idx_majorscore ON (legalName, majorName, province, year, curriculum, batchName)`

---

## 5. college_plan

> 招生计划 — 高校提前公布的当年度各专业招生人数

| 字段 | 类型 | 说明 |
|------|------|------|
| `legalName` | TEXT | 学校名 |
| `major_name` | TEXT | **专业名** |
| `year` | TEXT | 2020-2026 |
| `curriculum` | TEXT | 科类 |
| `batch_name` | TEXT | 批次 |
| `enroll_num` | TEXT | **计划招生人数** |
| `tuition` | TEXT | 学费 |
| `lengthOfSchooling` | TEXT | 学制 |
| `selectSubjects` | TEXT | 选科要求 · `物+化` / `不限` |

**索引**: `UNIQUE INDEX idx_college_plan ON (legalName, major_name, province, year, batch_name)`

---

## 6. crawl_skip

> 爬虫负向缓存 — "已确认无数据"

| 字段 | 类型 | 说明 |
|------|------|------|
| `school_name` | TEXT PK | 学校名 |
| `year` | TEXT PK | 年份 |
| `curriculum` | TEXT PK | 科类 |
| `table_name` | TEXT PK | `schoolscore` / `majorscore` / `college_plan` |
| `checked_at` | TIMESTAMP | 标记时间 |

---

## 7. 数据关系

```
college_info
  │
  ├─ college_name ──→ schoolscore.legalName
  ├─ college_name ──→ majorscore.legalName
  └─ college_name ──→ college_plan.legalName
```

---

## 8. 科类说明

| 年份 | 科类取值 | 高考制度 |
|------|---------|------|
| 2020 – 2023 | `理科` `文科` | 旧高考（文理分科） |
| 2024 – 2026 | `物理类` `历史类` | 新高考 3+1+2 |

**选科要求格式**（college_plan.selectSubjects）

| 值 | 含义 |
|----|------|
| `不限` | 无选科限制 |
| `物+化` | 物理+化学 |
| `物+化+生` | 物理+化学+生物 |
| `史+政` | 历史+政治 |

---

## 9. 年份约定

| 表 | 年份范围 | 最新有数据 | 说明 |
|---|---------|:---:|------|
| `college_info` | — | — | 静态清单 |
| `schoolscore` | 2020-2025 | 2025 | 2026 录取未出分 |
| `majorscore` | 2020-2025 | 2025 | 2026 待公布 |
| `college_plan` | 2020-2026 | **2026** | 提前公布，6 月已有 |

**推荐规则**: `college_plan(今年)` + `schoolscore(上年)` + `majorscore(上年)`
