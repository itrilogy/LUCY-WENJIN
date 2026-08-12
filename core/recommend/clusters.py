# -*- coding: utf-8 -*-
"""专业簇 / 学科门类关键词扩展。

用户输入「计算机」时，自动扩展为同簇专业名关键词，提高匹配召回。
"""

from __future__ import annotations

from typing import Dict, List, Set

# 簇名 → 别名/子专业关键词
MAJOR_CLUSTERS: Dict[str, List[str]] = {
    "计算机": [
        "计算机",
        "软件工程",
        "网络工程",
        "信息安全",
        "物联网",
        "数据科学",
        "人工智能",
        "智能科学",
        "信息工程",
        "电子信息",
        "计算机科学",
        "网络安全",
        "区块链",
        "空间信息",
    ],
    "人工智能": [
        "人工智能",
        "智能科学",
        "机器人",
        "机器学习",
        "智能控制",
        "智能制造",
        "自动化",
        "数据科学",
    ],
    "电子信息": [
        "电子信息",
        "通信工程",
        "微电子",
        "集成电路",
        "光电",
        "电子科学",
        "信息工程",
        "电信工程",
    ],
    "医学": [
        "临床医学",
        "口腔医学",
        "预防医学",
        "麻醉学",
        "医学影像",
        "护理学",
        "药学",
        "中医学",
        "基础医学",
        "儿科学",
        "精神医学",
    ],
    "师范": [
        "师范",
        "教育学",
        "小学教育",
        "学前教育",
        "汉语言文学",
        "数学与应用数学",
        "英语",
        "思想政治教育",
        "学科教学",
    ],
    "经济金融": [
        "金融",
        "经济学",
        "国际经济",
        "财政学",
        "保险",
        "投资",
        "会计",
        "财务管理",
        "审计",
        "经济与贸易",
    ],
    "管理": [
        "工商管理",
        "行政管理",
        "公共管理",
        "人力资源管理",
        "物流管理",
        "信息管理",
        "工程管理",
        "旅游管理",
        "市场营销",
    ],
    "法学": ["法学", "法律", "知识产权", "社会工作", "政治学"],
    "机械": [
        "机械",
        "机械设计",
        "车辆工程",
        "过程装备",
        "智能制造",
        "材料成型",
        "工业设计",
    ],
    "土木建筑": [
        "土木工程",
        "建筑学",
        "城乡规划",
        "工程造价",
        "给排水",
        "建筑环境",
        "道路桥梁",
        "测绘",
    ],
    "电气能源": [
        "电气工程",
        "自动化",
        "能源",
        "新能源",
        "核工程",
        "储能",
        "电力系统",
    ],
    "化学化工": [
        "化学",
        "应用化学",
        "化学工程",
        "制药工程",
        "材料化学",
        "高分子",
        "精细化工",
    ],
    "生物环境": [
        "生物",
        "生物工程",
        "生物技术",
        "环境工程",
        "环境科学",
        "生态",
        "海洋",
        "食品科学",
    ],
    "外语": ["英语", "翻译", "日语", "法语", "德语", "西班牙语", "俄语", "商务英语"],
    "新闻传媒": [
        "新闻",
        "传播",
        "广播电视",
        "广告学",
        "网络与新媒体",
        "编辑出版",
        "播音",
    ],
    "艺术设计": [
        "设计",
        "视觉传达",
        "环境设计",
        "产品设计",
        "数字媒体",
        "动画",
        "美术",
        "音乐",
    ],
}


def expand_keywords(raw_keywords: List[str]) -> List[str]:
    """将用户关键词扩展为簇内别名集合（保序去重）。"""
    seen: Set[str] = set()
    out: List[str] = []

    def add(k: str):
        k = k.strip()
        if k and k not in seen:
            seen.add(k)
            out.append(k)

    for kw in raw_keywords:
        add(kw)
        # 精确簇名
        if kw in MAJOR_CLUSTERS:
            for a in MAJOR_CLUSTERS[kw]:
                add(a)
            continue
        # 簇名包含 / 关键词命中簇别名
        for cluster, aliases in MAJOR_CLUSTERS.items():
            if kw == cluster or kw in aliases or any(kw in a or a in kw for a in aliases[:3]):
                for a in aliases:
                    add(a)
                add(cluster)
    return out


def match_major_keywords(major_name: str, keywords: List[str]) -> bool:
    if not keywords or not major_name:
        return False
    name = major_name
    return any(k in name for k in keywords)


def list_clusters() -> Dict[str, List[str]]:
    return {k: list(v) for k, v in MAJOR_CLUSTERS.items()}
