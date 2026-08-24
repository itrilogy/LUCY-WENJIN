# 问津 · WenJin · 品牌资产

> 对齐实验室范式：见鹿 / 听默 / 观澜 · GuanLan  
> 归档对照：`Obsidian/departments/lab/鹿溪志愿-品牌资产`

## 双层结构

```
┌─────────────────────────────────────────────┐
│  产品层 brand/                               │
│    favicon.svg / logo.svg —— 志愿业务隐喻     │
├─────────────────────────────────────────────┤
│  实验室层                                    │
│    luxi-lab-main.svg ← 官方 LUXI LAB.svg     │
│    （关于页 / 出品方，三产品统一）              │
└─────────────────────────────────────────────┘
```

## 文件清单

| 文件 | 用途 |
|------|------|
| `favicon.svg` | ★ 浏览器 favicon / 侧栏小标 |
| `鹿溪志愿-产品标识.svg` | favicon 中文命名副本 |
| `logo.svg` | ★ 横版产品字锁 |
| `鹿溪志愿-横版字锁.svg` | logo 中文命名副本 |
| `luxi-lab-main.svg` | ★ 鹿溪联合实验室主 LOGO（官方） |
| `luxi-lab-lockup.svg` | 与 main 同源（URL 兼容） |
| `luxi-lab-main-v2.svg` | 官方 Version 2 备用 |

## 产品标识语义

| 元素 | 含义 |
|------|------|
| 鹿溪绿底 `#0D5E42` | 实验室品牌色 |
| 双枝分叉 + 中轴 | 志愿选择 / 升学路径 |
| 金色落点 `#F1C40F` | 目标院校 / 落点 |
| 溪流 `#00D2FF` | 清溪 · 数据与位次流动 |
| 源启星 | 灵感 / 智能推荐 |

## 色板（鹿溪 CI）

| 名称 | 色值 |
|------|------|
| 鹿溪绿 | `#0D5E42` |
| 源启白 | `#F5F7FA` |
| 进化蓝 | `#00D2FF` |
| 标题金 | `#F1C40F` |

## 修改流程

1. **产品标识**：改 `favicon.svg` / `logo.svg`，同步中文命名副本。  
2. **实验室主 LOGO**：只认官方 `鹿溪联合实验室/LUXI LAB.svg`；更新后拷贝到本目录 `luxi-lab-main.svg` 与 `luxi-lab-lockup.svg`。  
3. **勿**把听默几何 Y+L 实验标当作鹿溪主 LOGO。

## 工程引用

- HTML：`<link rel="icon" href="/static/brand/favicon.svg">`  
- 侧栏 / 关于：`/static/brand/logo.svg`、`/static/brand/luxi-lab-main.svg`
