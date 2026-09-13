<div align="center">
  <img src="static/brand/favicon.svg" width="64" height="64" alt="问津 · WenJin 产品标" />
  &nbsp;&nbsp;
  <img src="static/brand/luxi-lab.svg" width="64" height="64" alt="鹿溪联合创新实验室 LUXI LAB 符号标" />
</div>

<h1 align="center">问津 · WenJin（鹿溪志愿）</h1>

<p align="center">
  <strong>向道问津，顺溪成程</strong><br/>
  <em>Finding the right passage where choices meet the future.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Matrix-理数%C2%B7三思-0D5E42" alt="matrix" />
  <img src="https://img.shields.io/badge/Product-问津%20WenJin-0D5E42" alt="product" />
  <img src="https://img.shields.io/badge/Design-LUXI%20v1.1-0D5E42" alt="design" />
  <img src="https://img.shields.io/badge/Version-v1.3.0-f1c40f" alt="version" />
  <img src="https://img.shields.io/badge/Lab-鹿溪联合创新实验室-047538" alt="lab" />
  <img src="https://img.shields.io/badge/Stack-Flask%20%7C%20SQLite%20%7C%20DeepSeek-blue" alt="stack" />
</p>

<p align="center">
  <b>鹿溪联合创新实验室</b>（LUXI Joint Innovation Lab）出品<br/>
  仓库：<a href="https://github.com/itrilogy/LUCY-WENJIN">itrilogy/LUCY-WENJIN</a>
</p>

---

> 面向江西省高考考生的智能化志愿填报与梯度推演助手。基于开源项目 `gaokao2025`（`qt/topschool/`）改造：原项目提供百度高考 API 与 SQLite 表结构基础；本项目扩展为江西 **3+1+2** Web 应用——查询 + 冲稳保推荐 + AI 分析 + 百度一分一段 + 概率校准。
> 
> 本项目前端已全量遵从**《鹿溪设计范式》（LUXI Design System v1.1）**与 `luxi-scenario-kit-final.html` 参考套件规范。

---

## ✨ 功能一览

| 页面 | 功能 |
|------|------|
| 大学搜索 | 省份 / 类型 / 办学 / 标签筛选 + 分页排序 |
| 学校详情 | 录取分 · 专业分 · 计划 + 位次/分数过滤 |
| 专业反查 | 模糊搜索 + 多年份过滤 |
| 招生计划 | 多维搜索选科与计划数 |
| **志愿推荐** | 冲稳保 · 四维评分 · **校准概率** · 专业簇 · CSV 导出 |
| **AI 分析** | DeepSeek 多工具 Function Calling + **SSE 流式** |
| 备选清单 | localStorage + 云端 session 同步 |
| 数据质量 | 覆盖率 · 一分一段 · 一键校准 |

---

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/itrilogy/LUCY-WENJIN.git
cd LUCY-WENJIN

# 2. 安装依赖
python3 -m pip install -r requirements.txt

# 3. 环境变量配置（可选，AI 对话需配置 DeepSeek API Key）
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY=sk-xxxx

# 4. 数据库分发与自动还原
# 仓库内置已收录 3000 所高校、16.7 万录取分线数据的压缩包（gaokao2025.sqlite.gz，约 17MB）
# 首次运行 python3 app.py 时，系统会自动解压还原出完整的 gaokao2025.sqlite（约 116MB）
# 也可手动解压：gzip -dk gaokao2025.sqlite.gz

# 5. 启动服务（默认端口 5080）
python3 app.py
# 或：bash scripts/run_server.sh
```

# 浏览器
open http://127.0.0.1:5080
```

> **数据库说明**：因 GitHub 单文件上限为 100MB，全量数据库以标准 gzip 压缩包 `gaokao2025.sqlite.gz`（约 17.3MB）随版本库分发；程序启动时内置自愈还原机制，若检测到未解压则自动解包释放为 `gaokao2025.sqlite`，无需手动干预。

### 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `GAOKAO_DB` | SQLite 路径 | `./gaokao2025.sqlite` |
| `GAOKAO_PLAN_YEAR` | 招生计划年份 | 当年 |
| `GAOKAO_SCORE_YEAR` | 录取数据年份 | 当年 − 1 |
| `GAOKAO_API_TOKEN` | API Token（空 = 不校验） | 空 |
| `GAOKAO_RATE_LIMIT` | 每 IP 每分钟请求上限 | 60 |
| `FLASK_DEBUG` | `1` 开启调试 | `0` |
| `DEEPSEEK_API_KEY` | AI 分析密钥 | 空 |

### Docker

```bash
# 根目录放置 gaokao2025.sqlite 后
docker compose up --build
```

### 一分一段与概率校准

```bash
# 从百度 opendata 拉取江西一分一段，并校准概率模型
python3 scripts/crawl_score_segment.py --all --calibrate

python3 -m pytest tests/ -q
```

- 一分一段接口：`opendata.baidu.com`（`resource_id=50266`），**不是**学校库 `/gk/*`
- 推荐结果中的录取概率为**校准后的启发式**，非官方录取率

### 学校库爬虫（按需）

```bash
python3 getdata2025.py school   # 全国学校清单
python3 getdata2025.py score    # 录取分数线
python3 getdata2025.py major    # 专业分数线
python3 getdata2025.py plan     # 招生计划
```

---

## 🔄 与原项目的区别

| 方面 | 原项目 (`qt/topschool/`) | 问津 · WenJin |
|------|-------------------------|---------|
| 省份 | 浙江（3+3） | **江西（3+1+2）** |
| 界面 | Qt 桌面 | **Flask Web SPA** |
| 推荐 | 无 | **评分 + 概率 + 专业簇** |
| AI | 无 | **多工具 FC + SSE** |
| 一分一段 | 无 | **百度官方表** |
| 爬虫 | 全量 | **增量 + crawl_skip + 重试** |

---

## 🛠 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3 · Flask 3 |
| 数据库 | SQLite 3（WAL） |
| 前端 | HTML / CSS / JS（模块化 SPA） |
| AI | DeepSeek Chat |
| 部署 | gunicorn / Docker Compose |
| 数据 | 百度高考 API · opendata 一分一段 |

---

## 🏗 项目结构

```
LUCY-WENJIN/
├── app.py                 # Flask 路由
├── ai_recommend.py        # DeepSeek 多工具 + SSE
├── core/                  # 配置 · DB · 推荐 · 一分一段 · 校准
├── getdata2025.py         # 学校库爬虫
├── scripts/               # 一分一段 / 质量 / 探针 / 启动
├── .env.example           # 环境变量模板
├── static/
│   ├── brand/             # 产品方标/字锁 + 实验室符号标
│   ├── js/
│   ├── tokens.css         # 鹿溪设计令牌（LUXI Tokens v1.1）
│   └── style.css          # 问津现代化轻量样式系统
├── templates/index.html
├── tests/
├── 使用说明.md
├── RECOMMEND_ENGINE.md
├── DB_SCHEMA.md
├── ROADMAP.md
├── CHANGELOG.md
└── Dockerfile / docker-compose.yml
```

---

## 🎨 品牌标识（LUXI Design System v1.1）

| 标识 | 预览 | 规格与说明 | 资源文件 |
| :---: | :---: | :--- | :--- |
| **产品方标** | <img src="static/brand/favicon.svg" width="32" height="32" alt="问津" /> | 48×48 鹿溪绿圆角砖 + 双枝航道 glyph（stroke 1.7） + 水平溪流 + 金星 | `static/brand/favicon.svg` |
| **产品字锁** | [`static/brand/logo.svg`](static/brand/logo.svg) | 横版产品字锁（方标 + 标准排印） | `static/brand/logo.svg` |
| **实验室符号标** | <img src="static/brand/luxi-lab.svg" width="32" height="32" alt="LUXI LAB" /> | 角本位符号标（Y + 一横 · 无方框，浅底深绿/深底反白双态） | `static/brand/luxi-lab.svg` |

**色板（LUXI CI）**

| Token | 色值 | 用途 |
| :--- | :--- | :--- |
| 鹿溪绿 | `#0D5E42` | 主色 / 图标底板 |
| 源启白 | `#F5F7FA` | 浅色背景 / 反白 |
| 进化蓝 | `#00D2FF` | 溪流 / 数据高亮 |
| 标题金 | `#F1C40F` | 落点 / 显著信号 |

详见 [`static/brand/README.md`](static/brand/README.md)。

---

## 📚 文档

| 文档 | 内容 |
|------|------|
| [使用说明.md](使用说明.md) | 用户操作手册 |
| [RECOMMEND_ENGINE.md](RECOMMEND_ENGINE.md) | 推荐与概率算法 |
| [DB_SCHEMA.md](DB_SCHEMA.md) | 库表与一分一段 |
| [ROADMAP.md](ROADMAP.md) | 演进路线 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更 |

---

## 🙏 致谢

- 原项目 `qt/topschool` 数据与 API 思路  
- 百度高考 / opendata 一分一段  
- DeepSeek  
- 鹿溪联合创新实验室  

---

## ⚖️ 免责声明

本工具仅供志愿填报参考，录取结果以教育考试院与高校官方公布为准。概率模型为启发式估算，**不构成录取承诺**。

---

<div align="center">
  <img src="static/brand/luxi-lab.svg" width="48" height="48" alt="LUXI LAB 符号标" />
  <p><strong>问津 · WenJin</strong> · 向道问津，顺溪成程</p>
  <p>© 鹿溪联合创新实验室 · LUXI Joint Innovation Lab</p>
  <p><em>林深见鹿，源启清溪 · Deep Insights, Evolutionary Origin.</em></p>
</div>
