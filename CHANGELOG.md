# 变更日志

## v1.3.0 / 鹿溪设计范式对齐与健壮性加固 — 2026-09-13

### 设计系统与前端（对齐 LUXI Design System v1.1）
- **中心化令牌接入**：引入 `static/tokens.css`，增补文字专用色（`--text-ok/danger/info/warn`）、5 档控件高度与输入框专属令牌。
- **全域去 Emoji 化**：侧栏导航项替换为内嵌 24 视口 1.7 描边线性矢量 SVG 图标；清理 `index.html` 与 `static/js/`（`ai.js`, `quality.js`, `recommend.js`, `search.js`, `shortlist.js`）所有功能性与标题 Emoji。
- **按钮层级系统**：每屏唯一实底鹿溪绿 Primary 按钮，其余统一收敛为 Secondary（描边）、Ghost 或 Danger。
- **表单布局对齐**：重构定向志愿推荐配置面板（`.form-panel` + `.form-row` + `.input-addon-group`），位次输入框与「分→位」按钮高度锁定 36px 严密咬合，移除多层嵌套白框。
- **无障碍与交互**：增加全局 `Esc` 退出 About 弹窗；统一使用 `--luxi-cyan` 焦点环；补充 `@media (prefers-reduced-motion: reduce)` 动效降级。

### 品牌资产规范（P0 合规）
- **标识职能明确**：写实主标不进入产品 UI；侧栏底部与关于页统一使用角本位实验室符号标（`luxi-lab.svg` / `luxi-lab-inverse.svg`）。
- **双标等大原则**：关于页模态框与 README 双标位中，产品方标与实验室符号标严格落实并排等大（48×48 / 64×64）。
- **产品方标同构**：重构 `favicon.svg` 与 `logo.svg` 为 48×48 鹿溪绿砖（`.brick`）+ 24 视口双枝航道 glyph（stroke 1.7）+ 水平溪流 + 标题金星。

### 核心架构与健壮性加固
- **数据库随仓托管与自愈解压**：将 3,000 所高校、16.7 万录取分线的全量数据库封装为标准 gzip 压缩包 `gaokao2025.sqlite.gz`（约 17.3MB，规避 GitHub 单文件 100MB 限制并正常版本追踪）；`core/db.py` 内置自愈解压逻辑，首次启动检测到未解包时自动无缝还原出 `gaokao2025.sqlite`。
- **数据库自愈建表**：`core/db.py` 内置 `init_schema()`，初次连接或空库启动时自动完成 9 张核心表与索引的创建，彻底杜绝 `no such table` 异常。
- **空库安全防护**：`/api/filters` 与 `/api/quality` 增加空表安全取值与年份默认回退；启动时打印高校数据录入统计与数据导入提示。
- **环境变量注入**：`core/config.py` 支持自动读取根目录 `.env`，提供 `.env.example` 模板，`.gitignore` 忽略 `.env` 防密钥泄漏。
- **推演诚实性声明**：推荐卡片与 AI 对话区域增加置信边界与“推演非高校录取承诺”口径标注。

---

## v1.2.2 / 文档与品牌资产 — 2026-08-12

### 文档
- 全面修订 `使用说明.md`（8 页功能、一分一段、概率、品牌）
- 更新 `README.md` 结构索引、品牌区、免责声明
- 同步 `ROADMAP` / `DB_SCHEMA` / `RECOMMEND_ENGINE` 既有增量

### 品牌（对齐实验室双层范式）
- `static/brand/favicon.svg` · `logo.svg`：鹿溪志愿产品标识（路径分叉 + 溪流 + 源启星）
- `static/brand/luxi-lab-main.svg`：官方 **LUXI LAB.svg** 主 LOGO
- `luxi-lab-lockup.svg` / `main-v2` 备用；中文命名副本
- `static/brand/README.md` 使用与修改流程
- 侧栏 / 关于页 / favicon 接入；主色倾向鹿溪绿 CI

---

## v1.2.1 / 百度一分一段 + 概率校准 — 2026-08-12

### 调研结论
- `gaokao.baidu.com/gk/*` 学校库接口**不含**一分一段
- 百度 **opendata** 卡片接口有一分一段：
  - `GET https://opendata.baidu.com/api.php`
  - `resource_id=50266` · `query=一分一段` · `province/year/category`

### 一分一段
- 新增 `core/baidu_segment.py` 解析与请求
- `scripts/crawl_score_segment.py` 爬取江西 2021–2026（物理/历史或文理）
- `score_segment` 支持 `source=baidu|approx`，查询优先 baidu
- 批次线写入 `score_batchline`
- 实测入库约 **6867** 行；580 分物理类 → 位次 16546–16993

### 概率校准
- `core/recommend/calibrate.py`：
  - 跨年 majorscore 位次相对变化 → σ（可按学校）
  - 伪标签 + L2 正则拟合 logistic k/bias
- `estimate_admit_prob` 默认使用校准参数；结果含 `calibrated` / `params`
- API：`POST /api/rank/rebuild`（`source=baidu`）、`POST /api/rank/calibrate`
- 数据质量页：拉取百度一分一段 / 概率校准按钮

### 校准结果示例（江西 2025 物理类）
- k≈11 · bias≈0.25 · σ≈0.10（跨年样本 ~1.8 万）

---

## v1.2 / Phase 3 产品化 — 2026-08-12

### 算法
- **录取概率模型** `estimate_admit_prob`：位次比 logistic + 计划扩缩招 + 新专业波动区间
- 推荐结果每行增加 `admit.{prob,low,high,pct,rangePct,label}`
- 支持 `sortBy=prob` 按概率排序

### 专业簇
- `core/recommend/clusters.py`：计算机/医学/师范/经管等 16 簇
- 推荐参数 `useCluster`（默认开），关键词自动扩展

### 一分一段
- 表 `score_segment`；可从 `schoolscore` 重建近似对照
- API：分↔位、跨年粗换算；推荐页「分→位」按钮

### AI
- 多工具：`recommend` / `search_major` / `compare_schools` / `explain_admission`
- `POST /api/ai/stream` SSE 流式输出

### 备选与导出
- 云端 `user_shortlist`（session cookie）
- 推荐/备选 **CSV 导出**；备选同步/拉取云端

### 运维
- 侧栏「数据质量」看板
- `Dockerfile` + `docker-compose.yml`

### 测试
- `tests/test_phase3.py`；全量 **21 passed**

---

## v1.1 / 工程化 — 2026-08-12

### 架构
- 新增 `core/`：`config` / `db` / `security` / `recommend/{engine,scoring,subjects}`
- `app.py` 瘦身为 Flask 路由层；推荐逻辑迁入 `core.recommend.run_recommend`
- `ai_recommend.py` **直调**推荐引擎，去掉 `127.0.0.1:5080` HTTP 自环
- `dbconn2025.py` 改为包装 `core.db`，**消除硬编码 `/Users/ic/...` 路径**
- 前端内联 JS 拆为 `static/js/{utils,multi,search,recommend,ai,shortlist,main}.js`

### 正确性
- 修复选科匹配：支持 `物+不限` / `史+不限` / `物+(化+生)` 等真实枚举
- 爬虫 `is_skipped` / `mark_skipped` / `has_data` / insert 全面 **参数化 SQL**

### 安全与运维
- 默认 `FLASK_DEBUG=0`；`scripts/run_server.sh` 支持 gunicorn
- 可选 `GAOKAO_API_TOKEN` 鉴权 + `GAOKAO_RATE_LIMIT` 限流
- 年份可配置：`GAOKAO_PLAN_YEAR` / `GAOKAO_SCORE_YEAR` / `GAOKAO_DB`

### 质量
- `tests/` pytest：选科、评分、推荐集成、health
- `scripts/data_quality.py` 数据质量报告
- `scripts/probe_api.py` 外网 API 契约探针
- 更新 `DB_SCHEMA.md`（实测行数与 selectSubjects 枚举）
- 新增 `ROADMAP.md` 演进路线

---

## v2.1 — 2026-06-28

### 🚀 性能优化

#### 批量 LEFT JOIN 替代 N+1 查询
- **背景**：原 `api_recommend()` 在 per-school + per-major 循环中逐条查询数据库，每次请求触发约 22,000 次独立 SQL 查询
- **改动**：`app.py` — 用 5 次批量预加载查询（含 LEFT JOIN）替代，数据在 Python 字典中做 O(1) 索引
- **效果**：响应时间从 ~30+ 秒降至 ~1 秒

#### 数据库连接复用
- **改动**：`app.py` — `query()` 函数改用全局单例 `_db_conn`，消除每次查询的 connect/disconnect 开销
- **修复**：`dbconn2025.py` 中硬编码的路径 `/Users/ic/...` 改为动态获取

#### 新增 SQLite 索引
```sql
CREATE INDEX idx_majorscore_lookup ON majorscore(legalName, majorName, year, curriculum);
CREATE INDEX idx_plan_lookup ON college_plan(legalName, major_name, year, curriculum);
```

### 🐛 算法修复

#### 分档逻辑 — 去掉 reach_lower 跳过
- **问题**：`reach_lower = rank × (1 − aggr/100 × 0.7)` 错误地跳过了合法冲刺校
  - 激进 20% 时，reach_lower=11782，华南理工(10141) 和暨南大学(10583) 被跳过
- **改动**：`app.py` — 去掉 reach_lower 判断，学校位次比用户好即进入冲刺
- **文件**：`RECOMMEND_ENGINE.md §6.3`

#### 每专业独立输出
- **问题**：`best = min(matched_majors, key=pr)` 每校只选一个"最佳专业"
- **改动**：`app.py` — 评分和分档移到 per-major 循环内部，每个专业独立输出一行

#### 位次匹配门槛过滤
- **问题**：位次差距巨大的专业（如哈工大深圳 rank=2449, 用户 rank=13700）位次评分为 0，但靠标签分仍进入推荐列表
- **改动**：`app.py` — 位次比超出 `1 ± drift×width` 时直接跳过
- **新增参数**：`rankFilterWidth`（默认 3.0），控制过滤阈值宽窄

#### 学校详情查询参数名修复
- **问题**：`sd()` 中 `id.replace('1_','_')` 将 `r1_min`→`r_min`，后端期望 `rank_min`
- **改动**：`templates/index.html` — 用显式映射 `{r1_min:'rank_min', ...}`

#### 专业名模糊匹配（修复中外合作办学等后缀导致匹配失败）
- **问题**：`LEFT JOIN ... ON p.major_name = m.majorName` 精确匹配，但两表专业名格式不一致
  - `majorscore`: "信息与计算科学（中外合作办学）" rank=14562
  - `college_plan`: "信息与计算科学" ← 无后缀，匹配失败，降级到学校均值 rank=10682
- **改动**：`app.py` — 用 Python 端模糊匹配替代 SQL LEFT JOIN 精确匹配
  - 匹配策略：精确名 → 去掉括号后缀的 base 名 → 前缀包含匹配 → 学校均值
  - 索引构建改为两次独立查询（plan + majorscore）+ Python 侧匹配

### 🎛️ 新功能

#### rankFilterWidth UI 控件
- **改动**：`templates/index.html` — 推荐页新增"位次过滤阈值"滑杆（1~8，步进 0.5）
  - 实时显示当前值，随 API 请求提交
  - 覆盖默认值 3.0，用户可交互式调节过滤严格程度
- **同步**：`ai_recommend.py` — AI 工具定义 + 系统提示词增加 rankFilterWidth 询问步骤

#### 备选清单（Shortlist）
- **新增**：`templates/index.html` — 推荐结果每行增加 `➕` 按钮，点击添加到备选
- **新增**：侧边栏 `📋 备选清单` 页面（p6）
- **存储**：`localStorage` 持久化，刷新不丢失
- **功能**: 查看/删除/清空/导出打印，点击学校名可跳转详情

### 🐞 其他修复

#### 推荐表格重复列
- **问题**：柱状条编辑时引入重复列（`计划` 和 `位次比` 各出现两次）
- **改动**：`templates/index.html` — 删除重复的 467-468 行，恢复 9 列标准布局

#### 表头增加 tooltip 说明
- **改动**：`templates/index.html` — 为 `分/位次`、`计划`、`位次比` 三列添加 `title` 属性
  - 分/位次: "该专业2025年录取最低分/最低位次"
  - 计划: "2026计划数/2025计划数"
  - 位次比: "专业位次÷考生位次，<1表示冲刺"

### 🎨 UI 优化

#### 省份选择器改造
- **问题**：志愿推荐页用 `<select multiple>`，需 Ctrl 多选，移动端不可用
- **改动**：`templates/index.html` — 替换为统一的 `buildMulti()` 点击式组件
- **新增**：状态数组 `selRecP`、前缀处理器 `rp`

#### 加载动画升级
- **改动**：`templates/index.html` — "计算中..." → CSS spinner + "正在分析学校录取数据..."

#### Toast 通知替换 alert
- **改动**：`templates/index.html` — 新增 `showToast()` 函数，替换 4 处 `alert()`
- **新增**：CSS `.toast` 样式（info/warn/err 三色），右上角滑入 3 秒自动消失

#### 评分可视化柱状条
- **改动**：`templates/index.html` — 推荐结果评分明细从纯文本改为四色水平柱状条
  - 位次 🔵 蓝 / 标签 🟣 紫 / 专业 🟡 橙 / 计划 🟢 绿

#### AI Markdown 渲染
- **改动**：`templates/index.html` — 新增 `md2html()` 函数，AI 回复中的 Markdown 表格、粗体、代码正确渲染
- **新增**：CSS `.ai-msg` 表格/代码样式

#### 学校详情输入防抖
- **改动**：`templates/index.html` — 位次/分数范围输入增加 300ms 防抖 + Enter 键触发 + 显式"查询"按钮

#### 输入值保持
- **问题**：`sd()` 重建 HTML 时输入框值丢失
- **改动**：`templates/index.html` — 在重建前保存输入值，重建后通过 `value` 属性恢复

---

## v2.0 — 2026-06 基线

- 初始 Flask Web 应用
- 志愿推荐引擎（v1 算法）
- DeepSeek AI 集成
- 爬虫数据采集
- SQLite 数据库
