# -*- coding: utf-8 -*-
"""Hiring Radar 查询服务层 —— 供 UI / Agent 复用。"""
from __future__ import annotations

import os
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import hiring_radar as hr  # noqa: E402

# 内置大厂中文名（种子表未覆盖的）
_BUILTIN_LABELS = {
    "bytedance": "字节跳动",
    "tencent": "腾讯",
    "netease": "网易",
    "jd": "京东",
    "baidu": "百度",
    "unitree": "宇树科技",
    "nio": "蔚来",
    "xpeng": "小鹏",
    "bambulab": "拓竹",
    "momenta": "Momenta",
    "boke": "波克城市",
    "yostar": "悠星",
    "tesla-cn": "特斯拉中国",
    "figure": "Figure AI",
    "figureai": "Figure AI",
    "1x": "1X",
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "scale": "Scale AI",
    "scaleai": "Scale AI",
    "nvidia": "NVIDIA",
}

# 秋招/产品向常用公司（置顶）
FEATURED_LOCAL = [
    "zhipu", "moonshot", "minimax", "baichuan", "01ai", "modelbest",
    "bytedance", "tencent", "baidu", "netease", "jd",
    "nio", "xpeng", "li", "agibot", "unitree",
]


def ensure_loaded() -> None:
    hr._load_company_seeds()


def load_company_catalog() -> Dict[str, Dict[str, str]]:
    """返回 {key: {label, kind, sector}}。kind: local | global | board"""
    ensure_loaded()
    catalog: Dict[str, Dict[str, str]] = {}

    seed_path = os.path.join(ROOT, "parsers", "companies.seed")
    if os.path.isfile(seed_path):
        with open(seed_path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                parts = [x.strip() for x in ln.split("|")]
                if len(parts) < 4:
                    continue
                key, typ, company = parts[0].lower(), parts[1].lower(), parts[2]
                sector = parts[5] if len(parts) > 5 else typ
                catalog[key] = {"label": company, "kind": "local", "sector": sector or typ}

    for key in hr.LOCAL_PARSERS:
        if key not in catalog:
            catalog[key] = {
                "label": _BUILTIN_LABELS.get(key, key),
                "kind": "local",
                "sector": "大厂/内置",
            }
        else:
            catalog[key]["kind"] = "local"

    for key in hr.COMPANIES:
        catalog[key] = {
            "label": _BUILTIN_LABELS.get(key, key.title()),
            "kind": "global",
            "sector": "海外 ATS",
        }

    for board in ("remoteok", "remotive", "weworkremotely", "workingnomads", "all"):
        catalog[f"board:{board}"] = {
            "label": f"聚合板 · {board}",
            "kind": "board",
            "sector": "远程聚合",
        }
    return catalog


def company_options(prefer_local: bool = True) -> List[Tuple[str, str]]:
    """返回 [(display, key), ...] 供下拉框。"""
    catalog = load_company_catalog()
    featured = []
    locals_, globals_, boards = [], [], []

    for key, meta in catalog.items():
        display = f"{meta['label']}  ({key})"
        item = (display, key)
        if key in FEATURED_LOCAL:
            featured.append(item)
        elif meta["kind"] == "local":
            locals_.append(item)
        elif meta["kind"] == "global":
            globals_.append(item)
        else:
            boards.append(item)

    featured.sort(key=lambda x: FEATURED_LOCAL.index(x[1]) if x[1] in FEATURED_LOCAL else 99)
    locals_.sort(key=lambda x: x[0])
    globals_.sort(key=lambda x: x[0])
    boards.sort(key=lambda x: x[0])

    # 去重：featured 已出现的不再进 locals_
    featured_keys = {k for _, k in featured}
    locals_ = [x for x in locals_ if x[1] not in featured_keys]

    if prefer_local:
        return featured + locals_ + globals_ + boards
    return featured + globals_ + locals_ + boards


def search_jobs(
    company_key: str,
    keyword: str = "",
    recent_days: int = 0,
) -> Dict[str, Any]:
    """
    统一查询入口。
    返回 {ok, source, total, matched, jobs, error, company_top, dept_top, loc_top}
    """
    ensure_loaded()
    company_key = (company_key or "").strip()
    first_kw = keyword.split(",")[0].strip() if keyword else ""
    kws = [k.strip().lower() for k in keyword.split(",") if k.strip()]

    try:
        if company_key.startswith("board:"):
            board = company_key.split(":", 1)[1]
            items, src = hr.fetch_boards(board)
        elif company_key in hr.LOCAL_PARSERS:
            spec = hr.LOCAL_PARSERS[company_key]
            items, src = hr.fetch_local(spec, name=company_key, keyword=first_kw, company="")
        elif company_key in hr.COMPANIES:
            items, src = hr.resolve_and_fetch(company_key, None, first_kw if hr.COMPANIES[company_key][0] == "workday" else "")
        else:
            # 尝试当全球公司名 auto-probe
            items, src = hr.resolve_and_fetch(company_key, None, "")
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "source": "",
            "total": 0,
            "matched": 0,
            "jobs": [],
            "company_top": [],
            "dept_top": [],
            "loc_top": [],
        }

    def match(it: dict) -> bool:
        if not kws:
            return True
        hay = (
            it.get("title", "")
            + " "
            + it.get("company", "")
            + " "
            + it.get("dept", "")
            + " "
            + it.get("team", "")
            + " "
            + it.get("location", "")
            + " "
            + it.get("jd", "")
            + " "
            + it.get("comp", "")
        ).lower()
        return any(k in hay for k in kws)

    filt = [it for it in items if match(it)]
    if recent_days > 0:
        filt = [
            it
            for it in filt
            if (hr._days_ago(it.get("date") or "") is None or hr._days_ago(it.get("date") or "") <= recent_days)
        ]

    for it in filt:
        it.pop("_wd", None)

    company_top = Counter(it.get("company", "") for it in filt if it.get("company")).most_common(8)
    dept_top = Counter(it.get("dept", "") for it in filt if it.get("dept")).most_common(6)
    loc_top = Counter(it.get("location", "") for it in filt if it.get("location")).most_common(6)

    return {
        "ok": True,
        "error": "",
        "source": src,
        "total": len(items),
        "matched": len(filt),
        "jobs": filt,
        "company_top": company_top,
        "dept_top": dept_top,
        "loc_top": loc_top,
    }


def jobs_to_rows(jobs: List[dict], limit: Optional[int] = None) -> List[dict]:
    rows = []
    subset = jobs if limit is None else jobs[:limit]
    for j in subset:
        rows.append(
            {
                "公司": j.get("company") or "",
                "岗位": j.get("title") or "",
                "地点": j.get("location") or "",
                "类型": j.get("type") or "",
                "部门": j.get("dept") or "",
                "薪资": j.get("comp") or "",
                "日期": j.get("date") or "",
                "链接": j.get("url") or j.get("apply_url") or "",
                "JD": j.get("jd") or "",
            }
        )
    return rows
