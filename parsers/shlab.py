#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上海人工智能实验室（AILAB / PJLab）本地解析器。

数据源：飞书门户 aicarrier.jobs.feishu.cn/522799
对外链接：一律改写为官网详情页 https://www.shlab.org.cn/joinus/detail/{id}?mode=...
（飞书 aicarrier 中转页常显示不正确/需登录，官网详情稳定可投）

用法: python3 shlab.py [keyword] [pages]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 允许直接运行：把上级 parsers 包路径搞定
sys.path.insert(0, str(Path(__file__).resolve().parent))
import feishu  # noqa: E402

HOST = "aicarrier.jobs.feishu.cn/522799"
COMPANY = "上海人工智能实验室"
PORTAL = "https://www.shlab.org.cn/joinus"


def _mode(title: str, typ: str) -> str:
    text = f"{title} {typ}"
    if any(x in text for x in ("校招", "校园", "实习", "留用实习", "campus")):
        return "campus"
    if any(x in text for x in ("社招", "社会招聘", "social")):
        return "social"
    # 默认校招页也能打开多数岗位；社招 mode 作次选
    return "campus"


def fetch(keyword: str = "", pages: int = 4):
    raw = feishu.fetch(HOST, COMPANY, keyword=keyword, pages=pages, limit=50)
    out = []
    for j in raw:
        jid = str(j.get("id") or "")
        title = j.get("title") or ""
        typ = j.get("type") or ""
        mode = _mode(title, typ)
        detail = f"{PORTAL}/detail/{jid}?mode={mode}" if jid else PORTAL
        # 备用：另一种 mode，避免偶发打不开
        alt_mode = "social" if mode == "campus" else "campus"
        alt = f"{PORTAL}/detail/{jid}?mode={alt_mode}" if jid else PORTAL
        j = dict(j)
        j["url"] = detail
        j["apply_url"] = alt
        j["portal_url"] = PORTAL
        out.append(j)
    return out


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else ""
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    print(json.dumps(fetch(kw, pages), ensure_ascii=False))
