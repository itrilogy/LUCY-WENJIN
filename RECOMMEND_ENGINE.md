# 志愿推荐引擎 · 算法设计说明

> **版本** v3.1 — 2026.08（Phase 3）  
> **实现** `core/recommend/engine.py` + `probability.py` + `clusters.py`  
> **数据基准** `college_plan(PLAN_YEAR)` + `schoolscore/majorscore(SCORE_YEAR)`  
> **说明** 默认 当年计划 + 上年录取；可用环境变量覆盖  
> **变更历史** 见 `CHANGELOG.md`

---

## 目录

1. [输入参数](#1-输入参数)
2. [数据加载策略](#2-数据加载策略)
3. [选科匹配规则](#3-选科匹配规则)
4. [评分体系](#4-评分体系)
5. [位次匹配与过滤](#5-位次匹配与过滤)
6. [分档算法](#6-分档算法)
7. [专业分数来源](#7-专业分数来源)
8. [输出字段](#8-输出字段)
9. [动态年份](#9-动态年份)
10. [部署与 API](#10-部署与-api)

---

## 1. 输入参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|:---:|------|
| `score` | int | — | 高考分数 |
| `rank` | int | — | 省位次 |
| `firstSubject` | string | `物理` | 首选科目：物理/历史 |
| `secondSubjects` | array | `[]` | 再选科目：化学/生物/政治/地理 |
| `freeMajor` | string | `""` | 专业关键词，中英文逗号分割 |
| `freeMajorMode` | string | `optional` | `optional`=加权不筛 / `mandatory`=至少命中一个 |
| `provinces` | array | `[]` | 大学所在省份筛选 |
| `tags` | array | `[]` | 985/211/双一流/强基计划 |
| `tagMode` | string | `or` | `or`=含任一 / `and`=同时含全部 |
| `aggressiveness` | int | `50` | 0-100，越大越敢冲（仅影响 drift） |
| `safety` | int | `50` | 0-100，越大保底越多 |
| `usePlan` | bool | `true` | 是否参考招生计划数 |
| `rankFilterWidth` | float | `3.0` | 位次过滤阈值倍数（详见 §5） |

---

## 2. 数据加载策略

### 2.1 批量预加载（v2 优化）

推荐引擎启动时，通过 **5 次 SQL 查询** 完成全部数据预加载，替代原始的 N+1 逐条查询模式（原实现每次请求触发约 22,000 次 SQL 查询）：

```
查询 1: 学校列表
   SELECT c.college_name, ..., MIN(s.minScoreOrder)
   FROM college_info c JOIN schoolscore s ...
   WHERE s.year=? AND s.curriculum=?
   GROUP BY c.college_name
   → 获取所有有录取数据的学校及其最低位次

查询 2: 招生计划 + 专业分数（核心批量查询）
   SELECT p.*, m.minScore, m.minScoreOrder
   FROM college_plan p
   LEFT JOIN majorscore m ON p.legalName=m.legalName
       AND p.major_name=m.majorName AND m.year=? AND m.curriculum=?
   WHERE p.year=? AND p.curriculum=?
   → LEFT JOIN 保证 plan 行全部保留，majorscore 匹配不上则 m 字段为 NULL

查询 3: 去年计划数
   SELECT legalName, major_name, enroll_num
   FROM college_plan WHERE year=? AND curriculum=?

查询 4: 各校 majorscore 均值（新专业回退用）
   SELECT legalName, avg(...) as avgScore, avg(...) as avgRank
   FROM majorscore WHERE year=? AND curriculum=? GROUP BY legalName

查询 5: 各校 plan 均值（回退用）
   SELECT legalName, avg(enroll_num) as avgPlan
   FROM college_plan WHERE year=? GROUP BY legalName
```

预加载完成后，在 Python 中用 `defaultdict(list)` 和 `dict` 建立内存索引，后续所有查找都是 O(1) 字典访问，零数据库查询。

### 2.2 数据库连接复用

全局单例 `_db_conn` 替代每次查询开闭连接，消除约 22,000 次 SQLite connect/disconnect 开销。

### 2.3 索引优化

```sql
CREATE INDEX idx_majorscore_lookup ON majorscore(legalName, majorName, year, curriculum);
CREATE INDEX idx_plan_lookup ON college_plan(legalName, major_name, year, curriculum);
```

---

## 3. 选科匹配规则

`college_plan.selectSubjects` 使用简称格式：

| 数据库值 | 含义 |
|---------|------|
| `不限` | 无限制 |
| `物+化` | 必须物理+化学 |
| `物+化+生` | 必须物理+化学+生物 |
| `史+政` | 必须历史+政治 |

简称映射：`物理→物` `化学→化` `生物→生` `历史→史` `地理→地` `政治→政`

**实测高频格式**（勿只按「不限 / 物+化」实现）：

| 值 | 含义 |
|----|------|
| `物+不限` / `史+不限` | 首选约束 + 再选任意（「不限」不是科目 token） |
| `物+化` / `史+政` | 首选 + 再选 AND |
| `物+(化+生)` | 括号内再选 AND |

匹配逻辑（`match_select_subjects`）：

```
1. 空 / "不限" → 通过
2. 顶层按 + 分割（括号内 + 不拆）
3. token 为 "不限" → 跳过（不加入 required）
4. token 为 (化+生) → 括号内科目均须 ⊆ allowed
5. 普通 token（物/化/…）须 ∈ allowed
6. allowed = {首选简称} ∪ {再选简称…}
```

---

## 4. 评分体系

### 4.1 评分项

| 评分项 | 权重 | 算法 |
|--------|:---:|------|
| 位次匹配 | 0~40 | 考生位次与专业录取位次的接近程度（详见 §5） |
| 标签分 | 0~15 | OR 模式累加 / AND 模式全匹配得 15 分 |
| 专业匹配 | 0~20 | 关键词命中且选科匹配的专业优先赋分 |
| 计划趋势 | -5~+15 | 扩招>20%:+2 / 缩招>20%:-2 / 新专业:+2 / 计划数对数加分 |
| **总分** | **0~90** | 四项累加（计划不扣到负） |

### 4.2 标签分计算

```python
points = {'985':10, '211':8, '双一流':5, '强基计划':2}

OR 模式: sum(points[t] for t in tags_filter if t in tag_str), max=25  # TAG_OR_CAP
AND 模式: 15 if all(t in tag_str for t in tags_filter) else -1(跳过)
# 与 core/config.py 中 TAG_POINTS / TAG_OR_CAP / TAG_AND_SCORE 一致
```

### 4.3 专业匹配分

```python
有关键词 + 命中:  ratio 在 drift 内=20分, 2×drift 内=12分, 其他=5分
有关键词 + 强制模式未命中: -1(跳过)
无关键词但有选科匹配: 8分
```

### 4.4 计划趋势分

```python
calc_plan_score(count) = min(15, log2(max(count,1)) × 3)

趋势修正:
  扩招 >20%: +2
  缩招 >20%: -2
  新专业(去年无数据): +2 (鼓励)
```

---

## 5. 位次匹配与过滤

### 5.1 核心参数

```python
drift = 0.05 + aggressiveness / 100 × 0.15
```

| 激进度 | drift | 含义 |
|:-----:|:-----:|------|
| 0% | 0.05 | 极保守，仅推荐位次几乎完全匹配 |
| 20% | 0.08 | 保守 |
| 50% | 0.125 | 默认 |
| 100% | 0.20 | 激进，接受更大的位次差距 |

### 5.2 位次比

```
major_ratio = 专业录取位次(pr) / 考生位次(rank)

pr(major_ratio) → 安全转 int，失败返回 999999
major_ratio < 1 → 专业比考生好（冲刺）
major_ratio > 1 → 专业比考生差（保底）
major_ratio = 1 → 完全匹配
```

### 5.3 三区模型

评分 + 过滤 分三个区，由 `drift` 和 `rankFilterWidth`（默认 3.0）控制边界：

```
             1-w×d      1-d      rank=1    1+d     1+w×d
位次比:     ───|─────────|─────────|─────────|─────────|───
             │  过滤区  │  零分区  │  评分区  │  零分区  │  过滤区
             │  直接跳过 │ 展示但0分│ 40→0递减 │ 展示但0分│  直接跳过
```

**边界公式**：

| 区 | 范围 | 行为 |
|:-|:----|:----|
| **评分区** | `[1-d, 1+d]` | `score = 40 × (1 - \|ratio-1\| / d)`，线性递减至 0 |
| **零分区（缓冲）** | `[1-w×d, 1-d)` ∪ `(1+d, 1+w×d]` | 位次评分为 0，但标签、专业匹配等分数仍有效，仍可展示 |
| **过滤区** | `< 1-w×d` 或 `> 1+w×d` | **直接跳过此专业**，不进入推荐列表 |

### 5.4 rankFilterWidth 的作用

`rankFilterWidth`（简称 `w`）控制缓冲区的宽度：

```
w=2:  缓冲区窄 → 位次匹配要求严
w=3:  默认值   → 平衡
w=4:  缓冲区宽 → 更多边缘学校进入零分区展示
w=5+: 接近无过滤 → 仅靠评分筛选
```

**示例**（rank=13700, 激进20%, drift=0.08）：

| 学校 | 专业位次 | 位次比 | w=2 边界0.84 | w=3 边界0.76 | w=4 边界0.68 |
|:----|:-------:|:-----:|:-----------:|:-----------:|:-----------:|
| 哈工大深圳 | 2449 | 0.178 | 过滤 ❌ | 过滤 ❌ | 过滤 ❌ |
| 华南理工 | 10141 | 0.740 | 过滤 ❌ | 过滤 ❌ | 零分区展示 |
| 暨南大学 | 10583 | 0.773 | 过滤 ❌ | 零分区展示 | 零分区展示 |
| 华南理工(其他) | 11000 | 0.803 | 过滤 ❌ | 零分区展示 | 零分区展示 |
| 华南师大 | 15220 | 1.111 | 评分区(5分) | 评分区(11分) | 评分区(11分) |

### 5.5 位次匹配分计算

```python
def calc_rank_score(ratio, drift, width=3.0):
    if ratio < 1 - drift * width or ratio > 1 + drift * width:
        return 0
    base = 40 * (1 - abs(ratio - 1) / drift) if drift > 0 else 40
    return max(0, min(40, base))
```

---

## 6. 分档算法

### 6.1 档位判定

每个**专业独立判定**档位（一所学校的不同专业可在不同档位）：

```python
safe_factor  = 1.0 + safety / 100 × 4.0

match_upper = rank × (1.0 + safety / 100 × 2.0)
safe_upper  = rank × safe_factor

if   major_rank < rank          → 冲刺 🔴（专业比你好）
elif major_rank < match_upper   → 稳健 🟡（专业略差于你）
elif major_rank < safe_upper    → 保底 🟢（专业明显更差）
else                             → 跳过（专业太差）
```

### 6.2 示例

rank=13700, aggressiveness=20%(drift=0.08), safety=20%:

| 档位 | 位次区间 | 说明 |
|:---:|:--------:|------|
| 冲刺 🔴 | < 13,700 | 专业录取位次优于考生 |
| 稳健 🟡 | 13,700 ~ 19,180 | 专业录取位次略差于考生 |
| 保底 🟢 | 19,180 ~ 24,660 | 专业录取位次明显差于考生 |
| 跳过 | > 24,660 | 专业太差 |

### 6.3 v1→v2 分档变更

**v1（原版，已废弃）**：
```python
reach_factor = 1.0 - aggressiveness / 100 × 0.7
reach_lower = rank × reach_factor
if school_rank < reach_lower: continue  # ❌ 错误跳过合法冲刺校
```

**问题**：`reach_lower` 在学校录取位次优于考生时错误地跳过，导致激进度低时无冲刺校。例如激进20%时，rank=13700 的 reach_lower=11782，华南理工(10141) 和暨南大学(10583) 均被跳过。

**v2 修复**：去掉 `reach_lower`。学校（专业）位次比用户好就无条件进入冲刺，不再因激进度低而跳过。

---

## 7. 专业分数来源

| 情况 | 分数来源 | 标记 |
|------|---------|:---:|
| majorscore 2025 有同名专业 | 真实录取分/位次 | — |
| 无同名专业（新专业） | 该校该科类 majorscore 2025 均值 | ⚠️ |
| 连均值都无 | schoolscore 2025 全校线 | ⚠️ |

> 注：新专业标记 `⚠️` 仅在 UI 显示时添加，数据库查询使用原始专业名，避免 v1 中 `⚠️` 后缀污染查询条件导致计划数查不到的 bug。

---

## 8. 输出字段

| 字段 | 说明 |
|------|------|
| `school` / `uniqueRank` / `province` / `tag` | 学校基本信息 |
| `majorName` | 专业名（⚠️ 标记均值估算） |
| `majorScore` / `majorRank` | 该专业 2025 年录取分和位次 |
| `ratio` | 专业位次 / 考生位次 |
| `planThisYear` / `planLastYear` | 2026 / 2025 计划招生人数 |
| `scores.rankScore` / `tagScore` / `majorScore` / `planScore` / `total` | 四项评分及总分 |

> v2 变化：每个专业独立输出一行，一所学校可以有多个专业进入推荐列表。不再选取"最佳专业"代表学校。

---

## 9. 动态年份

```python
plan_year  = datetime.now().year        # 2026
score_year = plan_year - 1             # 2025
major_year = score_year                # 2025（若无则降级 2024）
```

---

## 10. 部署与 API

### 启动

```bash
cd /Users/kwangwah/Project/gaokao2025
source venv/bin/activate
python3 app.py
# → http://127.0.0.1:5080
```

### API 调用

```bash
curl -s -X POST http://127.0.0.1:5080/api/recommend \
  -H 'Content-Type: application/json' \
  -d '{"score":603,"rank":13700,"firstSubject":"物理","secondSubjects":["化学","生物"],"provinces":["广东"],"tags":["211","双一流"],"tagMode":"and","aggressiveness":20,"safety":20,"rankFilterWidth":3}'
```

### AI 分析模式

启动 WebUI → 侧边栏「💬 AI分析」→ 与 AI 对话即可。AI 通过 Function Calling 调用推荐 API。


---

## 11. 录取概率模型（v3.2 · 已校准）

实现：`core/recommend/probability.py` + `calibrate.py`

### 输入
- 考生位次 `student_rank`
- 专业录取位次 `major_rank`
- 可选：计划扩缩招、是否新专业、学校名（取学校级 σ）

### 算法
1. `ratio = major_rank / student_rank`（位次越小越好；ratio>1 考生优于专业线 → 易录）
2. `p = sigmoid(k * (ratio - 1) + bias) + plan_adj`
3. k/bias 由 `run_calibration` 伪标签拟合（L2 正则，避免 0/100% 极化）
4. σ 来自 majorscore 跨年相对位次变化中位数；可覆盖学校级 σ
5. 区间：`ratio * (1±σ)` 再映射到概率；新专业 σ≥0.14

### 一分一段
- 百度 opendata `resource_id=50266`（**非** `/gk/*` 学校库）
- 分→位默认 `rank_max`（同分最差位次）
- 爬取：`scripts/crawl_score_segment.py --all --calibrate`

### 声明
**校准后的启发式估算，仍非官方录取概率，不构成录取承诺。**

### 专业簇
见 `core/recommend/clusters.py`。`useCluster=true` 时 `freeMajor` 自动扩展同簇别名。
