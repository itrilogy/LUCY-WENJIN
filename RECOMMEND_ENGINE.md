# 志愿推荐引擎 · 算法范式

> **版本** 2026.06  
> **数据基准** `college_plan(2026)` + `schoolscore(2025)` + `majorscore(2025)`  
> **说明** 2026 年招生计划 + 2025 年录取数据

---

## 输入参数

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
| `aggressiveness` | int | `50` | 0-100，越大越敢冲 |
| `safety` | int | `50` | 0-100，越大保底越多 |
| `usePlan` | bool | `true` | 是否参考招生计划数 |

---

## 分档算法

```
reach_factor = 1.0 - aggressiveness / 100 × 0.7     // 0%→1.0(跳过一切)  100%→0.3(敢冲清北)
safe_factor  = 1.0 + safety / 100 × 4.0             // 0%→1.0(无保底)  100%→5.0(大量保底)

reach_lower = rank × reach_factor    // 冲刺最低位次
match_upper = rank × 2.0            // 稳健最高位次
safe_upper  = rank × safe_factor    // 保底最高位次

if   school_rank < reach_lower → 跳过（学校太好够不着）
elif school_rank < rank        → 冲刺 🔴
elif school_rank < match_upper → 稳健 🟡
elif school_rank < safe_upper  → 保底 🟢
else                           → 跳过（学校太差）
```

**示例**：rank=13700, aggressiveness=50(默认), safety=50(默认)

| 档位 | 位次区间 | 典型学校 |
|------|:--------:|---------|
| 跳过 | < 6,850 | 清北复交 |
| 冲刺 🔴 | 6,850 ~ 13,700 | 南昌大学(10k) |
| 稳健 🟡 | 13,700 ~ 27,400 | 江西师大(18k) |
| 保底 🟢 | 27,400 ~ 41,100 | 赣南师大(35k) |
| 跳过 | > 41,100 | 太差的学校 |

**激进 70%**：reach_factor=0.51 → 冲刺下限=6,987（几乎不变）但稳健上限不变

**保守 30%**：reach_factor=0.79 → 冲刺下限=10,823（少了很多冲刺校）

---

## 评分体系

| 评分项 | 权重 | 算法 |
|--------|:---:|------|
| 位次匹配 | 0~50 | 考生位次与学校录取位次的接近程度，完全匹配=50分 |
| 标签分 | 0~15 | 985=15、211=10、双一流=10、强基=5，累加不封顶 |
| 专业匹配 | 0~10 | 关键词命中且选科匹配的专业优先赋分 |
| 计划趋势 | -5~+15 | 扩招>20%:+2 / 缩招>20%:-2 / 新专业:+2 / 计划数对数加分 |
| **总分** | **0~90** | 四项累加（计划不扣到负） |

---

## 选科匹配规则

`college_plan.selectSubjects` 使用简称格式：

| 数据库值 | 含义 |
|---------|------|
| `不限` | 无限制 |
| `物+化` | 必须物理+化学 |
| `物+化+生` | 必须物理+化学+生物 |
| `史+政` | 必须历史+政治 |

简称映射：`物理→物 化学→化 生物→生 历史→史 地理→地 政治→政`

匹配逻辑：
```
1. selectSubjects="不限" → 自动匹配 ✅
2. 解析 required = ["物","化"]
3. allowed = [首选简称] + [再选简称...]
4. required ⊆ allowed → 匹配 ✅
5. 无再选科目时：仅检查首选匹配
```

---

## 专业分数来源

| 情况 | 分数来源 | 标记 |
|------|---------|:---:|
| majorscore 2025 有同名专业 | 真实录取分/位次 | — |
| 无同名专业（新专业） | 该校该科类 majorscore 2025 均值 | ⚠️ |
| 连均值都无 | schoolscore 2025 全校线 | ⚠️ |

---

## 输出字段

| 字段 | 说明 |
|------|------|
| `school` / `uniqueRank` / `province` / `tag` | 学校基本信息 |
| `majorName` | 专业名（⚠️ 标记均值估算） |
| `majorScore` / `majorRank` | 该专业 2025 年录取分和位次 |
| `ratio` | 专业位次 / 考生位次 |
| `planThisYear` / `planLastYear` | 2026 / 2025 计划招生人数 |
| `scores.rankScore` / `tagScore` / `majorScore` / `planScore` / `total` | 四项评分及总分 |

---

## 动态年份

```python
plan_year  = datetime.now().year        # 2026
score_year = plan_year - 1             # 2025
major_year = score_year                # 2025（若无则降级 2024）
```

---

## 部署说明

```bash
# 启动 Web 服务
cd /Users/ic/Project/gaokao2025
source venv/bin/activate
python app.py
# → http://127.0.0.1:5080
```

### API 调用

```bash
curl -s -X POST http://127.0.0.1:5080/api/recommend \
  -H 'Content-Type: application/json' \
  -d '{"score":585,"rank":13700,"firstSubject":"物理","secondSubjects":["化学","生物"]}'
```

### AI 分析模式

启动 WebUI → 侧边栏「💬 AI分析」→ 与 AI 对话即可。
