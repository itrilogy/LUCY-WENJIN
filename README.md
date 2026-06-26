# 鹿溪志愿

> 🦌 **林深见鹿 · 源启清溪**  
> 面向江西省高考考生的智能化志愿填报助手

基于开源项目 `gaokao2025`（`qt/topschool/`）改造而来。原项目提供了百度高考 API 调用逻辑和 SQLite 数据库表结构基础，本项目在此基础上进行了大量改造。

---

## 与原项目的区别

| 方面 | 原项目 (`qt/topschool/`) | 鹿溪志愿 |
|------|-------------------------|---------|
| 省份 | 浙江（3+3 新高考） | **江西（3+1+2 新高考）** |
| 界面 | Qt Widgets 桌面应用（需编译） | **Flask Web 应用（浏览器即用）** |
| 功能 | 4 个查询 Tab | **6 个页面 + 志愿推荐引擎 + AI 分析** |
| 爬虫 | 一次性全量爬取 | **增量爬取 + crawl_skip 负向缓存 + 断点续传** |
| 推荐算法 | 无（仅查询） | **综合评分引擎（位次/标签/专业/计划 四项评分）** |
| AI | 无 | **DeepSeek Function Calling 对话式分析** |
| 选科 | 3+3 综合（一种 curriculum） | **3+1+2（物理类/历史类 + 再选科目匹配）** |
| 数据年份 | 2020-2024 | **2020-2026（含当年招生计划）** |
| 容错 | 无重试 | **3 次超时重试 + 自动提交 + WAL 模式** |

---

## 快速开始

```bash
# 1. 激活虚拟环境
cd /Users/ic/Project/gaokao2025
source venv/bin/activate

# 2. 启动 Web 服务
python app.py

# 3. 浏览器打开
open http://127.0.0.1:5080
```

### 爬虫（如需更新数据）

```bash
python getdata2025.py school    # 全国学校清单（约 5 分钟）
python getdata2025.py score     # 录取分数线（约 1-2 小时）
python getdata2025.py major     # 专业分数线（约 1-2 小时）
python getdata2025.py plan      # 招生计划（约 1-2 小时）
```

---

## 功能一览

| 页面 | 功能 | 对应 Qt Tab |
|------|------|:----------:|
| 🏫 大学搜索 | 省份/类型/档次多选筛选 + 分页 + 排名排序 | Tab1 |
| 📋 学校详情 | 录取分 + 专业分 + 招生计划 + 位次分数过滤 | Tab2 |
| 📚 专业反查 | 模糊搜索 + 多年份 + 位次/分数范围过滤 | Tab3 |
| 📝 招生计划 | 省份/学校/专业/年份/标签多维搜索 | Tab4 |
| 🎯 志愿推荐 | 分数/位次/选科 → 冲稳保 + 评分明细 | 🆕 |
| 💬 AI 分析 | DeepSeek 对话式志愿咨询 | 🆕 |

---

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python 3.14 + Flask 3.1 |
| 数据库 | SQLite 3（WAL 模式） |
| 前端 | 原生 HTML / CSS / JavaScript（SPA） |
| AI | DeepSeek Chat（Function Calling） |
| 数据源 | 百度高考 API / 中国教育在线 |

---

## 项目结构

```
gaokao2025/
├── app.py                  # Flask Web 主程序
├── ai_recommend.py         # DeepSeek AI 志愿分析引擎
├── getdata2025.py          # 爬虫主程序
├── dbconn2025.py           # SQLite 连接封装（单例）
├── crawl_2025_major.py     # 2025 专业分补爬脚本
├── crawl_2026_plan.py      # 2026 招生计划补爬脚本
├── gaokao2025.sqlite       # SQLite 数据库
├── templates/
│   └── index.html          # 前端 SPA 页面
├── static/
│   └── style.css           # 全局样式
├── qt/                     # Qt 桌面应用（原项目，已不依赖）
├── 设计备忘-爬虫调度器.md   # 爬虫架构设计
├── 设计备忘-WebGUI.md      # Web UI 设计
├── DB_SCHEMA.md            # 数据库结构说明
├── RECOMMEND_ENGINE.md     # 推荐引擎算法范式
└── 使用说明.md              # 用户手册
```

---

## 致谢

- 原项目 `gaokao2025`（`qt/topschool/`）提供了百度高考 API 调用逻辑和数据表结构基础
- 百度高考 API / 中国教育在线提供录取数据
- DeepSeek 提供 AI 对话能力
