# -*- coding: utf-8 -*-
"""秋讯看板 · 数据服务层：封装 Hiring-Radar，供 UI 调用。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import hiring_radar as hr  # noqa: E402

from my_targets import AGENT_PIPELINE, TRACKS, YRD_LOCATIONS  # noqa: E402

USER_PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_prefs.json")
USER_SEED_PATH = os.path.join(ROOT, "parsers", "companies.user.seed")

_BUILTIN_LABELS = {
    "bytedance": ("字节跳动", "大厂"),
    "tencent": ("腾讯", "大厂"),
    "netease": ("网易", "大厂"),
    "jd": ("京东", "大厂"),
    "baidu": ("百度", "大厂"),
    "unitree": ("宇树科技", "具身智能"),
    "nio": ("蔚来", "车厂"),
    "xpeng": ("小鹏", "车厂"),
    "bambulab": ("拓竹", "消费电子"),
    "momenta": ("Momenta", "自动驾驶"),
    "boke": ("波克城市", "游戏"),
    "yostar": ("悠星", "游戏"),
    "tesla-cn": ("特斯拉中国", "车厂"),
    "shopee": ("Shopee虾皮", "互联网"),
    "shlab": ("上海人工智能实验室", "AI科研"),
}

_GLOBAL_PRESETS = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "nvidia": "NVIDIA",
    "figure": "Figure",
    "scale": "Scale AI",
    "1x": "1X",
}


def _ensure_loaded() -> None:
    """加载官方 seed；每次调用都重新套用用户公司（防 Streamlit 热重载丢解析器）。"""
    if not getattr(_ensure_loaded, "_done", False):
        hr._load_company_seeds()
        _ensure_loaded._done = True  # type: ignore[attr-defined]
    # 先 prefs 再 seed：prefs 为权威来源，seed 作备份
    _apply_custom_parsers()
    _load_user_seed_file()


def _load_user_seed_file() -> None:
    """加载用户自行接入的 companies.user.seed（与官方 seed 同格式）。"""
    if not os.path.isfile(USER_SEED_PATH):
        return
    try:
        with open(USER_SEED_PATH, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = [x.strip() for x in ln.split("|")]
        if len(parts) < 4:
            continue
        key, typ, company, a1 = parts[0].lower(), parts[1].lower(), parts[2], parts[3]
        a2 = parts[4] if len(parts) > 4 else ""
        if not key:
            continue
        # 用户 seed 可覆盖同 key（保证重启后仍是用户接入的门户参数）
        _inject_parser(key, typ, company, a1, a2)


def _inject_parser(key: str, typ: str, company: str, a1: str, a2: str = "") -> None:
    typ = (typ or "").lower()
    if typ == "feishu" and a1:
        hr.LOCAL_PARSERS[key] = {
            "command": "python3",
            "args": ["parsers/feishu.py", a1, company, "{keyword}"],
        }
    elif typ == "moka" and a1 and a2:
        hr.LOCAL_PARSERS[key] = {
            "command": "python3",
            "args": ["parsers/moka.py", a1, a2, company, "{keyword}"],
        }
    elif typ == "beisen" and a1:
        hr.LOCAL_PARSERS[key] = {
            "command": "python3",
            "args": ["parsers/beisen.py", a1, company, "{keyword}"],
        }


def _apply_custom_parsers() -> None:
    prefs = load_user_prefs()
    for item in prefs.get("custom_parsers") or []:
        key = (item.get("key") or "").strip().lower()
        if not key:
            continue
        _inject_parser(
            key,
            item.get("type") or "",
            item.get("name") or key,
            item.get("arg1") or "",
            item.get("arg2") or "",
        )


def _sync_user_seed_file(prefs: Optional[Dict[str, Any]] = None) -> None:
    """用 custom_parsers 全量重写 companies.user.seed，保证下次启动可恢复。"""
    prefs = prefs if prefs is not None else load_user_prefs()
    customs = prefs.get("custom_parsers") or []
    lines = ["# 用户自行接入的公司（粘贴门户链接 / 工作台添加，勿手改 key）\n"]
    for item in customs:
        key = (item.get("key") or "").strip().lower()
        typ = (item.get("type") or "").strip().lower()
        name = (item.get("name") or key).strip()
        a1 = (item.get("arg1") or "").strip()
        a2 = (item.get("arg2") or "").strip()
        track = (item.get("track") or "").strip()
        if not key or not typ or not a1:
            continue
        lines.append(f"{key} | {typ} | {name} | {a1} | {a2} | {track}\n")
    os.makedirs(os.path.dirname(USER_SEED_PATH) or ".", exist_ok=True)
    tmp = USER_SEED_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.replace(tmp, USER_SEED_PATH)


def _parse_seed_meta() -> Dict[str, Tuple[str, str]]:
    meta: Dict[str, Tuple[str, str]] = dict(_BUILTIN_LABELS)
    for path in (
        os.path.join(ROOT, "parsers", "companies.seed"),
        USER_SEED_PATH,
    ):
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#"):
                    continue
                parts = [x.strip() for x in ln.split("|")]
                if len(parts) < 3:
                    continue
                key, company = parts[0].lower(), parts[2]
                track = parts[5] if len(parts) > 5 else ""
                meta[key] = (company, track)
    prefs = load_user_prefs()
    for item in prefs.get("custom_parsers") or []:
        key = (item.get("key") or "").strip().lower()
        name = (item.get("name") or key).strip()
        if key:
            meta[key] = (name, item.get("track") or "")
    return meta


def parse_ats_portal_url(url: str) -> Optional[Dict[str, str]]:
    """
    从招聘门户链接识别 ATS 类型与参数。
    支持：飞书 *.jobs.feishu.cn、Moka app.mokahr.com、北森 *.zhiye.com / *.hotjob.cn
    """
    raw = (url or "").strip()
    if not raw:
        return None
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    try:
        u = urlparse(raw)
    except Exception:
        return None
    host = (u.netloc or "").lower().split("@")[-1]
    path = u.path or ""

    # 飞书：xxx.jobs.feishu.cn[/website-path]
    m = re.match(r"^([a-z0-9_-]+)\.jobs\.feishu\.cn$", host)
    if m:
        portal = host
        path_id = path.strip("/").split("/")[0] if path.strip("/") else ""
        if path_id and re.fullmatch(r"[A-Za-z0-9_-]+", path_id):
            portal = f"{host}/{path_id}"
        return {
            "type": "feishu",
            "arg1": portal,
            "arg2": "",
            "suggest_key": m.group(1).lower(),
        }

    # Moka：app.mokahr.com/(campus|social)-recruitment/{org}/{site}
    if "mokahr.com" in host:
        mm = re.search(
            r"/(?:campus|social)-recruitment/([A-Za-z0-9_-]+)/(\d+)",
            path,
            re.I,
        )
        if mm:
            return {
                "type": "moka",
                "arg1": mm.group(1),
                "arg2": mm.group(2),
                "suggest_key": mm.group(1).lower(),
            }

    # 北森：{slug}.zhiye.com 或 {slug}.hotjob.cn
    bm = re.match(r"^([a-z0-9_-]+)\.(?:zhiye\.com|hotjob\.cn)$", host)
    if bm:
        return {
            "type": "beisen",
            "arg1": bm.group(1),
            "arg2": "",
            "suggest_key": bm.group(1).lower(),
        }

    return None


def _unique_key(base: str) -> str:
    _ensure_loaded()
    base = re.sub(r"[^a-z0-9_-]+", "", (base or "co").lower()) or "co"
    if base not in hr.LOCAL_PARSERS:
        return base
    for i in range(2, 50):
        cand = f"{base}{i}"
        if cand not in hr.LOCAL_PARSERS:
            return cand
    return f"{base}_{int(datetime.now().timestamp())}"


def connect_company_from_url(
    track: str,
    company_name: str,
    portal_url: str,
    key: str = "",
) -> Dict[str, Any]:
    """
    粘贴招聘门户链接 → 写入用户 seed → 加入赛道 → 可立即自动拉岗。
    """
    name = (company_name or "").strip()
    if not name:
        raise ValueError("请填写公司名称")
    parsed = parse_ats_portal_url(portal_url)
    if not parsed:
        raise ValueError(
            "无法识别该链接。请粘贴飞书（*.jobs.feishu.cn）、"
            "Moka（app.mokahr.com/.../公司/数字）或北森（*.zhiye.com）招聘门户地址。"
        )

    _ensure_loaded()
    use_key = (key or "").strip().lower() or _unique_key(parsed["suggest_key"])
    if use_key in hr.LOCAL_PARSERS and resolve_company_key(name) != use_key:
        # 已有同 key，直接复用并加入赛道
        add_keys_to_track(track, [use_key])
        remove_wishlist_by_name(track, name)
        return {
            "status": "scrapable",
            "key": use_key,
            "name": company_display_name(use_key),
            "message": f"该门户已在库中，已加入本赛道：{company_display_name(use_key)}",
        }

    typ, a1, a2 = parsed["type"], parsed["arg1"], parsed.get("arg2") or ""
    row = {
        "key": use_key,
        "type": typ,
        "name": name,
        "arg1": a1,
        "arg2": a2,
        "track": track,
        "portal_url": (portal_url or "").strip(),
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    prefs = load_user_prefs()
    customs = prefs.setdefault("custom_parsers", [])
    customs = [c for c in customs if (c.get("key") or "").lower() != use_key]
    customs.append(row)
    prefs["custom_parsers"] = customs
    # 确保写入赛道池，下次打开仍在「本赛道」
    bucket = prefs.setdefault("extra_keys_by_track", {}).setdefault(track, [])
    if use_key not in bucket:
        bucket.append(use_key)
    save_user_prefs(prefs)
    _sync_user_seed_file(prefs)

    _inject_parser(use_key, typ, name, a1, a2)
    remove_wishlist_by_name(track, name)

    type_label = {"feishu": "飞书", "moka": "Moka", "beisen": "北森"}.get(typ, typ)
    return {
        "status": "scrapable",
        "key": use_key,
        "name": name,
        "type": typ,
        "message": f"已接入{type_label}门户，可自动拉岗：{name}（{use_key}）。请在「本赛道」选择后点开始检索。",
    }


def list_local_companies() -> List[Dict[str, str]]:
    _ensure_loaded()
    meta = _parse_seed_meta()
    rows = []
    for key in sorted(hr.LOCAL_PARSERS.keys()):
        name, track = meta.get(key, (key, ""))
        rows.append({"key": key, "name": name, "track": track, "label": f"{name} ({key})"})
    return rows


def list_tracks() -> List[str]:
    return sorted({c["track"] for c in list_local_companies() if c["track"]})


def list_global_presets() -> List[Dict[str, str]]:
    return [{"key": k, "name": v, "label": f"{v} ({k})"} for k, v in _GLOBAL_PRESETS.items()]


def list_profile_tracks() -> List[str]:
    return list(TRACKS.keys())


def profile_track_meta(name: str) -> Dict[str, Any]:
    return TRACKS.get(name) or {}


def company_display_name(key: str) -> str:
    meta = _parse_seed_meta()
    return meta.get(key, (key, ""))[0]


def load_user_prefs() -> Dict[str, Any]:
    empty = {
        "extra_keys_by_track": {},
        "wishlist_by_track": {},
        "interested_jobs": [],
        "custom_parsers": [],
    }
    if not os.path.isfile(USER_PREFS_PATH):
        return dict(empty)
    try:
        with open(USER_PREFS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(empty)
        for k, v in empty.items():
            data.setdefault(k, v if not isinstance(v, list) else list(v))
            if isinstance(v, dict) and not isinstance(data.get(k), dict):
                data[k] = {}
            if isinstance(v, list) and not isinstance(data.get(k), list):
                data[k] = []
        return data
    except Exception:
        return dict(empty)


def save_user_prefs(prefs: Dict[str, Any]) -> None:
    """原子写入，避免写到一半进程退出导致 prefs 损坏；并同步 user seed。"""
    os.makedirs(os.path.dirname(USER_PREFS_PATH) or ".", exist_ok=True)
    tmp = USER_PREFS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, USER_PREFS_PATH)
    # 自建门户与 seed 双写，重启只丢一边也能恢复
    try:
        if "custom_parsers" in prefs:
            _sync_user_seed_file(prefs)
    except Exception:
        pass


def prefs_storage_info() -> Dict[str, Any]:
    """给 UI 展示：持久化路径与自建公司数量。"""
    prefs = load_user_prefs()
    customs = prefs.get("custom_parsers") or []
    extras = prefs.get("extra_keys_by_track") or {}
    extra_n = sum(len(v or []) for v in extras.values())
    writable = False
    try:
        probe = USER_PREFS_PATH + ".write_test"
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        writable = True
    except Exception:
        writable = False
    return {
        "prefs_path": USER_PREFS_PATH,
        "seed_path": USER_SEED_PATH,
        "custom_count": len(customs),
        "extra_key_count": extra_n,
        "wishlist_count": sum(
            len(v or []) for v in (prefs.get("wishlist_by_track") or {}).values()
        ),
        "writable": writable,
    }


def export_user_prefs_bytes() -> bytes:
    prefs = load_user_prefs()
    return json.dumps(prefs, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"


def import_user_prefs_bytes(raw: bytes) -> Dict[str, Any]:
    """合并导入：保留原感兴趣清单，覆盖/合并公司与赛道池。"""
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON 根节点必须是对象")
    prefs = load_user_prefs()
    # 合并 custom_parsers（按 key）
    by_key = {
        (c.get("key") or "").lower(): c
        for c in (prefs.get("custom_parsers") or [])
        if c.get("key")
    }
    for c in data.get("custom_parsers") or []:
        k = (c.get("key") or "").strip().lower()
        if k:
            by_key[k] = c
    prefs["custom_parsers"] = list(by_key.values())
    # 合并赛道池
    for track, keys in (data.get("extra_keys_by_track") or {}).items():
        bucket = prefs.setdefault("extra_keys_by_track", {}).setdefault(track, [])
        for k in keys or []:
            k = (k or "").strip().lower()
            if k and k not in bucket:
                bucket.append(k)
    # 合并 wishlist
    for track, items in (data.get("wishlist_by_track") or {}).items():
        bucket = prefs.setdefault("wishlist_by_track", {}).setdefault(track, [])
        names = {(x.get("name") or "").strip() for x in bucket}
        for it in items or []:
            n = (it.get("name") or "").strip()
            if n and n not in names:
                bucket.append(it)
                names.add(n)
    # 感兴趣岗位：导入侧优先追加
    seen = {x.get("uid") for x in (prefs.get("interested_jobs") or [])}
    for job in data.get("interested_jobs") or []:
        uid = job.get("uid")
        if uid and uid not in seen:
            prefs.setdefault("interested_jobs", []).append(job)
            seen.add(uid)
    save_user_prefs(prefs)
    _ensure_loaded._done = False  # type: ignore[attr-defined]
    _ensure_loaded()
    return prefs_storage_info()


def _job_uid(job: Dict[str, Any]) -> str:
    raw = "|".join(
        [
            str(job.get("company") or ""),
            str(job.get("title") or ""),
            str(job.get("url") or job.get("id") or ""),
        ]
    )
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def list_interested_jobs() -> List[Dict[str, Any]]:
    prefs = load_user_prefs()
    return list(prefs.get("interested_jobs") or [])


def add_interested_job(job: Dict[str, Any]) -> Dict[str, Any]:
    prefs = load_user_prefs()
    bucket = prefs.setdefault("interested_jobs", [])
    uid = _job_uid(job)
    for item in bucket:
        if item.get("uid") == uid:
            return item
    row = {
        "uid": uid,
        "company": job.get("company") or "",
        "title": job.get("title") or "",
        "location": job.get("location") or "",
        "type": job.get("type") or "",
        "url": job.get("url") or job.get("apply_url") or "",
        "portal_url": job.get("portal_url") or "",
        "jd": (job.get("jd") or "")[:800],
        "status": "感兴趣",
        "note": "",
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    bucket.insert(0, row)
    save_user_prefs(prefs)
    return row


def update_interested_job(uid: str, **fields: Any) -> bool:
    prefs = load_user_prefs()
    for item in prefs.get("interested_jobs") or []:
        if item.get("uid") == uid:
            for k, v in fields.items():
                if k in ("status", "note") and v is not None:
                    item[k] = v
            save_user_prefs(prefs)
            return True
    return False


def remove_interested_job(uid: str) -> bool:
    prefs = load_user_prefs()
    before = len(prefs.get("interested_jobs") or [])
    prefs["interested_jobs"] = [x for x in (prefs.get("interested_jobs") or []) if x.get("uid") != uid]
    save_user_prefs(prefs)
    return len(prefs["interested_jobs"]) < before


def clear_interested_jobs() -> None:
    prefs = load_user_prefs()
    prefs["interested_jobs"] = []
    save_user_prefs(prefs)


def add_wishlist_by_name(
    track: str,
    name: str,
    city: str = "",
    url: str = "",
    note: str = "待接入自动拉岗",
) -> Dict[str, str]:
    """登记尚未接入的公司：写入 wishlist，并给出官网搜索链接。"""
    from urllib.parse import quote

    name = (name or "").strip()
    if not name:
        raise ValueError("请填写公司名称")
    prefs = load_user_prefs()
    bucket = prefs.setdefault("wishlist_by_track", {}).setdefault(track, [])
    for item in bucket:
        if (item.get("name") or "").strip() == name:
            if city:
                item["city"] = city
            if url:
                item["url"] = url
            item["search_hint"] = item.get("search_hint") or (
                f"https://www.bing.com/search?q={quote(name + ' 校园招聘 招聘官网')}"
            )
            save_user_prefs(prefs)
            return item
    row = {
        "name": name,
        "city": (city or "").strip() or "待补充",
        "url": (url or "").strip(),
        "note": note,
        "search_hint": f"https://www.bing.com/search?q={quote(name + ' 校园招聘 招聘官网')}",
    }
    bucket.append(row)
    save_user_prefs(prefs)
    return row


def remove_wishlist_by_name(track: str, name: str) -> bool:
    prefs = load_user_prefs()
    bucket = prefs.setdefault("wishlist_by_track", {}).setdefault(track, [])
    before = len(bucket)
    prefs["wishlist_by_track"][track] = [x for x in bucket if (x.get("name") or "").strip() != name.strip()]
    save_user_prefs(prefs)
    return len(prefs["wishlist_by_track"][track]) < before


def suggest_scrapable(track: str, limit: int = 6) -> List[Dict[str, str]]:
    """给用户推荐本赛道已可自动拉岗的公司。"""
    catalog = track_company_catalog(track)
    return [
        {"key": c["key"], "name": c["name"], "label": c["label"]}
        for c in (catalog.get("enabled") or [])[:limit]
    ]


def add_keys_to_track(track: str, keys: List[str]) -> List[str]:
    """把已接入系统的公司 key 加入用户自定义赛道池，返回最终列表。"""
    _ensure_loaded()
    prefs = load_user_prefs()
    bucket = prefs.setdefault("extra_keys_by_track", {}).setdefault(track, [])
    valid = []
    for k in keys:
        k = (k or "").strip().lower()
        if not k or k not in hr.LOCAL_PARSERS:
            continue
        if k not in bucket:
            bucket.append(k)
        valid.append(k)
    save_user_prefs(prefs)
    return valid


def try_add_company(track: str, query: str, city: str = "") -> Dict[str, Any]:
    """
    智能加入：
    - 若能匹配系统已支持公司 → 加入可自动拉岗池
    - 否则 → 按公司名登记到 wishlist（只知道名字也能加）
    """
    q = (query or "").strip()
    if not q:
        raise ValueError("请输入公司名或 key")
    key = resolve_company_key(q)
    if key:
        add_keys_to_track(track, [key])
        return {
            "status": "scrapable",
            "key": key,
            "name": company_display_name(key),
            "message": f"已加入本赛道，可自动拉岗：{company_display_name(key)} ({key})",
        }
    # 已在赛道预设 / 待接入列表？仍允许再登记以补城市，并给出明确反馈
    catalog = track_company_catalog(track)
    already = next(
        (w for w in (catalog.get("wishlist") or []) if (w.get("name") or "").strip() == q),
        None,
    )
    item = add_wishlist_by_name(track, q, city=city or (already or {}).get("city") or "")
    if already:
        return {
            "status": "wishlist",
            "key": "",
            "name": item["name"],
            "message": f"「{item['name']}」已在待接入公司列表。可点「搜官网」找投递入口。",
            "item": item,
            "already": True,
        }
    return {
        "status": "wishlist",
        "key": "",
        "name": item["name"],
        "message": f"「{item['name']}」已加入待接入公司。可先搜官网投递；接入数据源后即可自动拉岗。",
        "item": item,
        "already": False,
    }


def resolve_company_key(query: str) -> Optional[str]:
    """支持 key 或中文名模糊匹配到可爬公司。"""
    _ensure_loaded()
    q = (query or "").strip().lower()
    if not q:
        return None
    if q in hr.LOCAL_PARSERS:
        return q
    meta = _parse_seed_meta()
    # 精确中文名
    for key, (name, _) in meta.items():
        if key in hr.LOCAL_PARSERS and name.lower() == q:
            return key
    # 包含匹配
    hits = []
    for key, (name, _) in meta.items():
        if key not in hr.LOCAL_PARSERS:
            continue
        if q in name.lower() or q in key:
            hits.append(key)
    if len(hits) == 1:
        return hits[0]
    if hits:
        return hits[0]
    return None


def track_company_catalog(track_name: str) -> Dict[str, Any]:
    """
    返回赛道公司目录：
    - enabled: 已在赛道池且可自动拉岗
    - available_to_add: 系统已支持但未加入本赛道
    - wishlist: 期望覆盖但尚未自动拉岗
    """
    _ensure_loaded()
    meta = profile_track_meta(track_name)
    seed_meta = _parse_seed_meta()
    prefs = load_user_prefs()
    extra = prefs.get("extra_keys_by_track", {}).get(track_name, [])

    base_keys = list(meta.get("scrape_keys") or [])
    # 按 seed 赛道标签自动扩容
    tags = set(meta.get("seed_track_tags") or [])
    if tags:
        for key, (name, seed_track) in seed_meta.items():
            if key in hr.LOCAL_PARSERS and any(t in (seed_track or "") for t in tags):
                if key not in base_keys:
                    base_keys.append(key)
    for k in extra:
        if k in hr.LOCAL_PARSERS and k not in base_keys:
            base_keys.append(k)
    # 用户接入的门户：按 track 字段归入本赛道（即使 extra_keys 漏写也能恢复）
    for item in prefs.get("custom_parsers") or []:
        if (item.get("track") or "") != track_name:
            continue
        k = (item.get("key") or "").strip().lower()
        if k and k in hr.LOCAL_PARSERS and k not in base_keys:
            base_keys.append(k)

    enabled = []
    enabled_keys = set()
    for key in base_keys:
        if key not in hr.LOCAL_PARSERS:
            continue
        name, seed_track = seed_meta.get(key, (key, ""))
        enabled.append(
            {
                "key": key,
                "name": name,
                "seed_track": seed_track,
                "label": f"{name} ({key})",
                "source": "user" if key in extra and key not in (meta.get("scrape_keys") or []) else "preset",
            }
        )
        enabled_keys.add(key)

    available_to_add = []
    for key in sorted(hr.LOCAL_PARSERS.keys()):
        if key in enabled_keys:
            continue
        name, seed_track = seed_meta.get(key, (key, ""))
        available_to_add.append(
            {
                "key": key,
                "name": name,
                "seed_track": seed_track,
                "label": f"{name} ({key}) · {seed_track}",
            }
        )

    wishlist = list(meta.get("wishlist") or []) + list(meta.get("portal_only") or [])
    # 用户自行登记的公司名
    for w in prefs.get("wishlist_by_track", {}).get(track_name, []) or []:
        wishlist.append(dict(w))
    # 去重 wishlist by name，并补齐搜索入口
    seen_names = set()
    uniq_wish = []
    for w in wishlist:
        n = (w.get("name") or "").strip()
        if not n or n in seen_names:
            continue
        seen_names.add(n)
        row = dict(w)
        row["name"] = n
        if not row.get("search_hint"):
            row["search_hint"] = f"https://www.bing.com/search?q={n}+校园招聘+招聘官网"
        uniq_wish.append(row)

    return {
        "enabled": enabled,
        "available_to_add": available_to_add,
        "wishlist": uniq_wish,
        "enabled_count": len(enabled),
        "system_total": len(hr.LOCAL_PARSERS),
    }


def get_agent_pipeline() -> List[Dict[str, Any]]:
    return list(AGENT_PIPELINE)


def _ats_type_for_key(key: str) -> str:
    _ensure_loaded()
    spec = hr.LOCAL_PARSERS.get(key) or {}
    args = spec.get("args") or []
    if not args:
        return "未知"
    script = str(args[0]).replace("\\", "/").lower()
    if script.endswith("feishu.py") or "feishu" in script:
        return "飞书"
    if script.endswith("moka.py") or "moka" in script:
        return "Moka"
    if script.endswith("beisen.py") or "beisen" in script:
        return "北森"
    if script.endswith("shlab.py"):
        return "飞书·上海AI实验室"
    return "自定义"


def _portal_arg_for_key(key: str) -> str:
    _ensure_loaded()
    if key == "shlab":
        return "aicarrier.jobs.feishu.cn → shlab.org.cn"
    spec = hr.LOCAL_PARSERS.get(key) or {}
    args = spec.get("args") or []
    if len(args) >= 2:
        script = str(args[0]).replace("\\", "/")
        if script.endswith("moka.py") and len(args) >= 3:
            return f"{args[1]}/{args[2]}"
        if script.endswith("shlab.py"):
            return "aicarrier.jobs.feishu.cn → shlab.org.cn"
        val = str(args[1])
        if val in ("{keyword}", "{company}"):
            return _portal_url_for_local(key) or val
        return val
    return ""


def search_jobs(
    mode: str,
    target: str,
    keyword: str = "",
    recent_days: int = 0,
    location_mode: str = "不限地点",
    emit: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """单公司检索，并产出可可视化的 Agent 运行轨迹 trace。"""
    import time

    _ensure_loaded()
    target = (target or "").strip().lower()
    if not target:
        raise ValueError("请选择或填写公司")

    first_kw = keyword.split(",")[0].strip() if keyword else ""
    kws = [k.strip().lower() for k in keyword.split(",") if k.strip()]
    company_key = target if mode == "local" else ""
    steps: List[Dict[str, Any]] = []
    t0 = time.perf_counter()

    def _step(sid: str, status: str, title: str, detail: str = "", **metrics: Any) -> None:
        row = {
            "id": sid,
            "status": status,
            "title": title,
            "detail": detail,
            "metrics": {k: v for k, v in metrics.items() if v is not None},
            "ms": int((time.perf_counter() - t0) * 1000),
        }
        steps.append(row)
        if emit:
            emit(row)

    _step(
        "listen",
        "done",
        "编译检索意图",
        f"关键词「{keyword or first_kw or '（空）'}」· 地点「{location_mode}」· 近 {recent_days} 天",
        keywords=len(kws) or (1 if first_kw else 0),
        location_mode=location_mode,
        recent_days=recent_days,
    )

    ats = _ats_type_for_key(target) if mode == "local" else "自动探测"
    portal = _portal_arg_for_key(target) if mode == "local" else target
    _step(
        "choose",
        "done",
        f"路由到 {company_display_name(target) if mode == 'local' else target}",
        f"ATS={ats} · 门户参数={portal or '—'}",
        company=company_display_name(target) if mode == "local" else target,
        ats=ats,
        portal=portal,
    )

    _step("fetch", "running", "正在拉取原始岗位…", f"调用 {ats} 解析器")
    t_fetch = time.perf_counter()
    if mode == "local":
        spec = hr.LOCAL_PARSERS.get(target)
        if not spec:
            raise ValueError(f"未注册的公司: {target}")
        items, src = hr.fetch_local(spec, name=target, keyword=first_kw, company=target)
        company_key = target
    else:
        items, src = hr.resolve_and_fetch(target, None, "")
    fetch_ms = int((time.perf_counter() - t_fetch) * 1000)

    if steps and steps[-1]["id"] == "fetch" and steps[-1]["status"] == "running":
        steps.pop()
    _step(
        "fetch",
        "done",
        f"采集完成 · 原始 {len(items or [])} 条",
        f"来源 {src or ats} · 耗时 {fetch_ms} ms",
        raw=len(items or []),
        source=src,
        fetch_ms=fetch_ms,
        ats=ats,
    )

    if not items:
        _step("judge", "done", "无原始岗位可过滤", "采集为空，跳过过滤", kept=0, dropped=0)
        _step("deliver", "done", "交付空结果", "可换关键词或检查门户是否可访问", matched=0)
        return {
            "source": src,
            "total": 0,
            "matched": 0,
            "jobs": [],
            "stats": {},
            "errors": [],
            "trace": {"steps": steps, "mode": mode, "target": target},
            "keyword_used": keyword or first_kw,
        }

    after_kw = [it for it in items if _match_keyword(it, kws)]
    drop_kw = len(items) - len(after_kw)
    _step(
        "judge",
        "done",
        f"关键词过滤 · 保留 {len(after_kw)} / {len(items)}",
        f"规则：标题/JD/部门包含任一关键词；剔除 {drop_kw} 条",
        before=len(items),
        after=len(after_kw),
        dropped=drop_kw,
        stage="keyword",
    )

    filt = after_kw
    if recent_days > 0:
        before = len(filt)
        filt = [
            it
            for it in filt
            if (hr._days_ago(it.get("date")) is None or hr._days_ago(it.get("date")) <= recent_days)
        ]
        _step(
            "judge",
            "done",
            f"时效过滤 · 近 {recent_days} 天 · 保留 {len(filt)}",
            f"剔除 {before - len(filt)} 条过旧岗位",
            before=before,
            after=len(filt),
            dropped=before - len(filt),
            stage="recent",
        )

    before_loc = len(filt)
    filt = [it for it in filt if _match_location(it, location_mode)]
    if location_mode == "江浙沪优先":
        _step(
            "judge",
            "done",
            f"地点过滤 · 保留 {len(filt)} / {before_loc}",
            f"江浙沪优先；地点缺失的岗位会保留以免误杀；剔除 {before_loc - len(filt)} 条",
            before=before_loc,
            after=len(filt),
            dropped=before_loc - len(filt),
            stage="location",
        )

    filt = [_enrich_job(it, company_key) for it in filt]
    for it in filt:
        it.pop("_wd", None)
    with_jd = sum(1 for it in filt if it.get("jd"))
    _step(
        "judge",
        "done",
        f"补全链接与 JD · {with_jd} 条含描述",
        "改写易失效的中转链，附带招聘首页",
        with_jd=with_jd,
        stage="enrich",
    )

    stats = {
        "companies": Counter(it.get("company") or "" for it in filt if it.get("company")).most_common(8),
        "locations": Counter(it.get("location") or "" for it in filt if it.get("location")).most_common(8),
        "depts": Counter(it.get("dept") or "" for it in filt if it.get("dept")).most_common(6),
        "with_jd": with_jd,
    }
    _step(
        "deliver",
        "done",
        f"交付 {len(filt)} 条命中岗位",
        "可在岗位卡加入感兴趣，或导出 JSON/CSV",
        matched=len(filt),
        total_raw=len(items),
    )

    return {
        "source": src,
        "total": len(items),
        "matched": len(filt),
        "jobs": filt,
        "stats": stats,
        "errors": [],
        "trace": {
            "steps": steps,
            "mode": mode,
            "target": target,
            "company": company_display_name(target) if mode == "local" else target,
            "ats": ats,
            "portal": portal,
        },
        "keyword_used": keyword or first_kw,
    }


def search_track(
    track_name: str,
    keyword: str = "",
    location_mode: str = "江浙沪优先",
    recent_days: int = 0,
    max_companies: int = 8,
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
    emit: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """按画像赛道批量查询多公司，合并结果，并汇总 Agent 轨迹。"""
    import time

    _ensure_loaded()
    meta = profile_track_meta(track_name)
    if not meta:
        raise ValueError(f"未知赛道: {track_name}")

    catalog = track_company_catalog(track_name)
    keys = [c["key"] for c in (catalog.get("enabled") or [])][:max_companies]
    if not keys:
        keys = [k for k in (meta.get("scrape_keys") or []) if k in hr.LOCAL_PARSERS][:max_companies]

    kw = keyword or meta.get("keywords") or ""
    all_jobs: List[Dict[str, Any]] = []
    errors: List[str] = []
    total_raw = 0
    company_traces: List[Dict[str, Any]] = []
    steps: List[Dict[str, Any]] = []
    t0 = time.perf_counter()

    def _step(sid: str, status: str, title: str, detail: str = "", **metrics: Any) -> None:
        row = {
            "id": sid,
            "status": status,
            "title": title,
            "detail": detail,
            "metrics": {k: v for k, v in metrics.items() if v is not None},
            "ms": int((time.perf_counter() - t0) * 1000),
        }
        steps.append(row)
        if emit:
            emit(row)

    _step(
        "listen",
        "done",
        f"赛道「{track_name}」批量扫描",
        f"关键词「{kw}」· {location_mode} · 计划 {len(keys)} 家公司",
        companies_planned=len(keys),
    )
    _step(
        "choose",
        "done",
        "排出信息源队列",
        " · ".join(company_display_name(k) for k in keys[:8]) + (" …" if len(keys) > 8 else ""),
        queue=keys,
    )

    for i, key in enumerate(keys):
        if progress_cb:
            progress_cb(company_display_name(key), i + 1, len(keys))
        _step(
            "fetch",
            "running",
            f"拉取 {company_display_name(key)}（{i + 1}/{len(keys)}）",
            f"ATS={_ats_type_for_key(key)}",
            company=company_display_name(key),
        )
        try:
            part = search_jobs(
                mode="local",
                target=key,
                keyword=kw,
                recent_days=recent_days,
                location_mode=location_mode,
            )
            total_raw += int(part.get("total") or 0)
            all_jobs.extend(part.get("jobs") or [])
            company_traces.append(part.get("trace") or {})
            if steps and steps[-1].get("status") == "running":
                steps.pop()
            _step(
                "fetch",
                "done",
                f"{company_display_name(key)} · 原始 {part.get('total', 0)} · 命中 {part.get('matched', 0)}",
                f"ATS={_ats_type_for_key(key)}",
                raw=part.get("total", 0),
                matched=part.get("matched", 0),
                company=company_display_name(key),
            )
        except Exception as e:
            if steps and steps[-1].get("status") == "running":
                steps.pop()
            errors.append(f"{company_display_name(key)}({key}): {e}")
            _step("fetch", "error", f"{company_display_name(key)} 失败", str(e), company=company_display_name(key))

    seen = set()
    uniq = []
    for j in all_jobs:
        sig = (j.get("company", ""), j.get("title", ""), j.get("location", ""))
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(j)

    _step(
        "judge",
        "done",
        f"合并去重 · {len(uniq)} 条",
        f"合并前 {len(all_jobs)} · 去掉重复 {len(all_jobs) - len(uniq)}",
        before=len(all_jobs),
        after=len(uniq),
    )
    _step(
        "deliver",
        "done",
        f"交付赛道结果 · {len(uniq)} 条",
        f"扫描 {len(keys)} 家 · 失败 {len(errors)} 家",
        matched=len(uniq),
        companies=len(keys),
        errors=len(errors),
    )

    stats = {
        "companies": Counter(it.get("company") or "" for it in uniq if it.get("company")).most_common(12),
        "locations": Counter(it.get("location") or "" for it in uniq if it.get("location")).most_common(12),
        "depts": Counter(it.get("dept") or "" for it in uniq if it.get("dept")).most_common(8),
        "with_jd": sum(1 for it in uniq if it.get("jd")),
    }
    return {
        "source": f"track/{track_name}",
        "total": total_raw,
        "matched": len(uniq),
        "jobs": uniq,
        "stats": stats,
        "errors": errors,
        "portal_only": meta.get("portal_only") or [],
        "queried_keys": keys,
        "keyword_used": kw,
        "trace": {
            "steps": steps,
            "mode": "track",
            "target": track_name,
            "company_traces": company_traces,
            "queried": [company_display_name(k) for k in keys],
        },
    }


def _portal_url_for_local(key: str) -> str:
    """尽量给出公司招聘门户首页（比岗位深链更稳）。"""
    if key == "shlab":
        return "https://www.shlab.org.cn/joinus"
    _ensure_loaded()
    spec = hr.LOCAL_PARSERS.get(key) or {}
    args = spec.get("args") or []
    if not args:
        return ""
    script = str(args[0]).replace("\\", "/")
    if script.endswith("shlab.py"):
        return "https://www.shlab.org.cn/joinus"
    if script.endswith("feishu.py") and len(args) >= 2:
        host = str(args[1])
        path = ""
        if "/" in host:
            host, path = host.split("/", 1)
        return f"https://{host}/{path}".rstrip("/") + "/"
    if script.endswith("moka.py") and len(args) >= 3:
        org, site = args[1], args[2]
        return f"https://app.mokahr.com/social-recruitment/{org}/{site}?locale=zh-CN#/"
    if script.endswith("beisen.py") and len(args) >= 2:
        slug = args[1]
        return f"https://{slug}.zhiye.com/social/jobs"
    builtins = {
        "bytedance": "https://jobs.bytedance.com/",
        "tencent": "https://careers.tencent.com/",
        "netease": "https://hr.163.com/",
        "jd": "https://zhaopin.jd.com/",
        "baidu": "https://talent.baidu.com/",
        "unitree": "https://www.unitree.com/",
        "shlab": "https://www.shlab.org.cn/joinus",
    }
    return builtins.get(key, "")


def _rewrite_official_url(job: Dict[str, Any], company_key: str) -> Dict[str, Any]:
    """把易出错的 ATS 中转链改成更稳的官网详情。"""
    jid = str(job.get("id") or "").strip()
    url = (job.get("url") or "").strip()
    title = job.get("title") or ""
    typ = job.get("type") or ""

    # 上海人工智能实验室 → 官网详情
    if company_key == "shlab" or "aicarrier.jobs.feishu.cn" in url or "shlab.org.cn" in url:
        mode = "campus"
        text = f"{title} {typ}"
        if any(x in text for x in ("社招", "社会招聘")) and "校招" not in text and "实习" not in text:
            mode = "social"
        elif any(x in text for x in ("校招", "校园", "实习", "留用")):
            mode = "campus"
        if jid:
            job["url"] = f"https://www.shlab.org.cn/joinus/detail/{jid}?mode={mode}"
            alt = "social" if mode == "campus" else "campus"
            job["apply_url"] = f"https://www.shlab.org.cn/joinus/detail/{jid}?mode={alt}"
        job["portal_url"] = "https://www.shlab.org.cn/joinus"
        job["deep_link"] = bool(jid)
        job["link_note"] = "已导向上海人工智能实验室官网详情页"
        return job

    # Moka：必须用 hash 路由；若旧格式 /job/uuid 则改写
    if "mokahr.com" in url:
        if "/job/" in url and "#/job/" not in url:
            parts = url.split("/job/")
            if len(parts) == 2:
                base = parts[0]
                mid = parts[1].split("?")[0].strip("/")
                url = f"{base}?locale=zh-CN#/job/{mid}"
                job["url"] = url
                job["apply_url"] = url.replace("/social-recruitment/", "/campus-recruitment/")
        job["deep_link"] = True
        job["link_note"] = "Moka 链接含 #，请用下方「复制链接」在浏览器地址栏打开更稳"
        return job

    # 北森：优先 detail?jobAdId=
    if "zhiye.com" in url and jid and "jobAdId=" not in url:
        # 从 portal 推断 slug
        portal = job.get("portal_url") or ""
        slug = ""
        if "://" in portal:
            host = portal.split("://", 1)[1].split("/", 1)[0]
            if host.endswith(".zhiye.com"):
                slug = host.replace(".zhiye.com", "")
        if not slug and "://" in url:
            host = url.split("://", 1)[1].split("/", 1)[0]
            if host.endswith(".zhiye.com"):
                slug = host.replace(".zhiye.com", "")
        if slug:
            job["url"] = f"https://{slug}.zhiye.com/social/detail?jobAdId={jid}"
            job["deep_link"] = True
            job["link_note"] = "北森深链；若空白请点招聘首页再搜岗位名"
            return job

    return job


def _enrich_job(job: Dict[str, Any], company_key: str = "") -> Dict[str, Any]:
    job = dict(job)
    job["date_fmt"] = hr._fmt_date(job.get("date"))
    portal = _portal_url_for_local(company_key) if company_key else (job.get("portal_url") or "")
    job["portal_url"] = portal
    job["company_key"] = company_key

    job = _rewrite_official_url(job, company_key)

    url = (job.get("url") or "").strip()
    apply_url = (job.get("apply_url") or "").strip()

    if url and url.rstrip("/").endswith("/social/jobs"):
        job["link_note"] = "北森深链不稳定时，请用招聘首页站内搜索岗位名"
        job["portal_url"] = portal or url
        job["deep_link"] = bool(job.get("id"))
    elif url and "link_note" not in job:
        job["deep_link"] = True
        job["link_note"] = job.get("link_note") or ""
    elif not url:
        job["url"] = portal
        job["deep_link"] = False
        job["link_note"] = "无岗位深链，已回退到公司招聘首页"

    if apply_url:
        job["apply_url"] = apply_url
    if portal and not job.get("portal_url"):
        job["portal_url"] = portal
    return job


def _match_keyword(it: Dict[str, Any], kws: List[str]) -> bool:
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


def _match_location(it: Dict[str, Any], location_mode: str) -> bool:
    if location_mode != "江浙沪优先":
        return True
    loc = (it.get("location") or "") + " " + (it.get("title") or "")
    if not loc.strip():
        # 地点缺失时先保留，避免误杀
        return True
    return any(x in loc for x in YRD_LOCATIONS)
