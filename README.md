# 鹿溪志愿 · LUXI Volunteer

> **林深见鹿 · 源启清溪**  
> 面向江西省高考考生的智能化志愿填报助手  
> 出品：**鹿溪联合创新实验室**（LUXI Joint Innovation Lab）

<p align="left">
  <img src="static/brand/favicon.svg" width="48" height="48" alt="鹿溪志愿">
  &nbsp;
  <img src="static/brand/logo.svg" width="280" alt="鹿溪志愿字锁">
</p>

仓库：[`itrilogy/luxi-volunteer`](https://github.com/itrilogy/luxi-volunteer)

基于开源项目 `gaokao2025`（`qt/topschool/`）改造。原项目提供百度高考 API 与 SQLite 表结构基础；本项目扩展为江西 **3+1+2** Web 应用：查询 + 冲稳保推荐 + AI 分析 + 百度一分一段 + 概率校准。

---

## 功能一览

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

## 快速开始

```bash
# 克隆
git clone https://github.com/itrilogy/luxi-volunteer.git
cd luxi-volunteer

# 依赖（需自备 gaokao2025.sqlite，默认不入库）
python3 -m pip install -r requirements.txt

# 启动（默认关闭 debug）
python3 app.py
# 或：bash scripts/run_server.sh

# 浏览器
open http://127.0.0.1:5080
```

> 数据库文件 `gaokao2025.sqlite` 体积较大，默认由 `.gitignore` 排除。部署时请将已爬取的库放到项目根目录，或通过 `GAOKAO_DB` 指定路径。

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

## 与原项目的区别

| 方面 | 原项目 (`qt/topschool/`) | 鹿溪志愿 |
|------|-------------------------|---------|
| 省份 | 浙江（3+3） | **江西（3+1+2）** |
| 界面 | Qt 桌面 | **Flask Web SPA** |
| 推荐 | 无 | **评分 + 概率 + 专业簇** |
| AI | 无 | **多工具 FC + SSE** |
| 一分一段 | 无 | **百度官方表** |
| 爬虫 | 全量 | **增量 + crawl_skip + 重试** |

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3 · Flask 3 |
| 数据库 | SQLite 3（WAL） |
| 前端 | HTML / CSS / JS（模块化 SPA） |
| AI | DeepSeek Chat |
| 部署 | gunicorn / Docker Compose |
| 数据 | 百度高考 API · opendata 一分一段 |

---

## 项目结构

```
luxi-volunteer/
├── app.py                 # Flask 路由
├── ai_recommend.py        # DeepSeek 多工具 + SSE
├── core/                  # 配置 · DB · 推荐 · 一分一段 · 校准
├── getdata2025.py         # 学校库爬虫
├── scripts/               # 一分一段 / 质量 / 探针 / 启动
├── static/
│   ├── brand/             # 产品 favicon/logo + 实验室主 LOGO
│   ├── js/
│   └── style.css
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

## 品牌资产

| 用途 | 路径 |
|------|------|
| Favicon / 侧栏小标 | [`static/brand/favicon.svg`](static/brand/favicon.svg) |
| 产品横版字锁 | [`static/brand/logo.svg`](static/brand/logo.svg) |
| 实验室主 LOGO | [`static/brand/luxi-lab-main.svg`](static/brand/luxi-lab-main.svg)（官方 LUXI LAB） |

色板：鹿溪绿 `#0D5E42` · 进化蓝 `#00D2FF` · 源启白 `#F5F7FA`。详见 [`static/brand/README.md`](static/brand/README.md)。

---

## 文档

| 文档 | 内容 |
|------|------|
| [使用说明.md](使用说明.md) | 用户操作手册 |
| [RECOMMEND_ENGINE.md](RECOMMEND_ENGINE.md) | 推荐与概率算法 |
| [DB_SCHEMA.md](DB_SCHEMA.md) | 库表与一分一段 |
| [ROADMAP.md](ROADMAP.md) | 演进路线 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更 |

---

## 致谢

- 原项目 `qt/topschool` 数据与 API 思路  
- 百度高考 / opendata 一分一段  
- DeepSeek  
- 鹿溪联合创新实验室  

---

## 免责声明

本工具仅供志愿填报参考，录取结果以教育考试院与高校官方公布为准。概率模型为启发式估算，**不构成录取承诺**。
