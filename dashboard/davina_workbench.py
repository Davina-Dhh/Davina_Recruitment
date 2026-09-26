# -*- coding: utf-8 -*-
"""Davina 秋招 · 暖色卡通工作台"""
from __future__ import annotations

import base64
import html
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

_DASHBOARD_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _DASHBOARD_DIR.parent
_ASSETS = _DASHBOARD_DIR / "assets"
for pth in (_ROOT_DIR, _DASHBOARD_DIR):
    if str(pth) not in sys.path:
        sys.path.insert(0, str(pth))

_spec = importlib.util.spec_from_file_location("davina_svc", _DASHBOARD_DIR / "radar_service.py")
_svc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_svc)

add_interested_job = _svc.add_interested_job
add_keys_to_track = _svc.add_keys_to_track
clear_interested_jobs = _svc.clear_interested_jobs
company_display_name = _svc.company_display_name
connect_company_from_url = _svc.connect_company_from_url
get_agent_pipeline = _svc.get_agent_pipeline
list_interested_jobs = _svc.list_interested_jobs
list_profile_tracks = _svc.list_profile_tracks
parse_ats_portal_url = _svc.parse_ats_portal_url
profile_track_meta = _svc.profile_track_meta
remove_interested_job = _svc.remove_interested_job
remove_wishlist_by_name = _svc.remove_wishlist_by_name
resolve_company_key = _svc.resolve_company_key
search_jobs = _svc.search_jobs
search_track = _svc.search_track
suggest_scrapable = _svc.suggest_scrapable
track_company_catalog = _svc.track_company_catalog
try_add_company = _svc.try_add_company
update_interested_job = _svc.update_interested_job

from my_targets import (  # noqa: E402
    BRAND_CN,
    BRAND_DAVINA,
    BRAND_EN,
    BRAND_NAME,
    BRAND_TAGLINE,
    DEFAULT_LOCATION_MODE,
    DEFAULT_QUERY_MODE,
    DEFAULT_TRACK,
)

import ai_service as _ai  # noqa: E402
import resume_service as _resume  # noqa: E402
from ui_chrome import apply_chrome, render_prd_view, render_sidebar_nav  # noqa: E402

_STEP_EMOJI = {
    "listen": "🎧",
    "choose": "🗺️",
    "fetch": "🧺",
    "judge": "✅",
    "ai": "✨",
    "deliver": "🎁",
}


def _img_data_uri(name: str) -> str:
    path = _ASSETS / name
    if not path.is_file():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


_URI_HERO = _img_data_uri("davina-mascot-hero.png")
_URI_SEARCH = _img_data_uri("davina-mascot-search.png")
_URI_STEPS = _img_data_uri("davina-agent-steps.png")

st.set_page_config(
    page_title=BRAND_NAME,
    page_icon="🦊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

apply_chrome()


def _init() -> None:
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("error", None)
    st.session_state.setdefault("active_stage", "listen")
    st.session_state.setdefault("flash", "")
    st.session_state.setdefault("pending_tip", None)
    st.session_state.setdefault("live_trace", [])
    st.session_state.setdefault("ai_notes", {})
    st.session_state.setdefault("ai_batch", [])
    st.session_state.setdefault("user_profile", "秋招 · AI/产品方向 · 优先江浙沪 · 关注产品经理/管培/运营")
    st.session_state.setdefault("resume_text", "")
    st.session_state.setdefault("resume_name", "")
    st.session_state.setdefault("resume_format", "")
    st.session_state.setdefault("resume_matches", {})


def _render_resume_match(note: dict) -> None:
    if not note:
        return
    score = note.get("score") or 0
    strengths = "".join(f"<li>{html.escape(x)}</li>" for x in (note.get("strengths") or []))
    gaps = "".join(f"<li>{html.escape(x)}</li>" for x in (note.get("gaps") or []))
    tips = "".join(f"<li>{html.escape(x)}</li>" for x in (note.get("suggestions") or []))
    kws = "、".join(html.escape(x) for x in (note.get("keywords_to_add") or []))
    st.markdown(
        f'<div class="blueprint">'
        f'<div class="hd"><div class="nm">📄 简历×岗位 · {html.escape(str(note.get("company") or ""))} · '
        f'{html.escape(str(note.get("title") or ""))}</div>'
        f'<div class="rl">{html.escape(str(note.get("verdict") or ""))} · {score}/100</div></div>'
        f'<div class="bd">'
        f'<b>总评</b>：{html.escape(str(note.get("summary") or "—"))}<br/>'
        f'<b>优先修改</b>：{html.escape(str(note.get("priority_edits") or "—"))}<br/>'
        f'<b>建议关键词</b>：{kws or "—"}'
        f'<br/><br/><b>匹配优势</b><ul>{strengths or "<li>—</li>"}</ul>'
        f'<b>缺口风险</b><ul>{gaps or "<li>—</li>"}</ul>'
        f'<b>优化建议</b><ul>{tips or "<li>—</li>"}</ul>'
        f"</div></div>",
        unsafe_allow_html=True,
    )


def _render_resume_panel(jobs: list, key_prefix: str = "main") -> None:
    """简历上传后的匹配面板：可选检索岗位或手动粘贴 JD。"""
    st.caption("上传 PDF/Word 后，对照岗位 JD 做匹配评价，并给出简历优化建议")
    has_resume = bool(st.session_state.get("resume_text"))
    if not has_resume:
        st.info("请先在左侧上传简历（PDF 或 .docx；扫描件图片 PDF 无法抽字）")
    else:
        st.success(
            f"已加载：{st.session_state.get('resume_name')} "
            f"（{st.session_state.get('resume_format')} · {len(st.session_state.resume_text)} 字）"
        )
        with st.expander("预览简历正文（节选）"):
            st.text(
                st.session_state.resume_text[:2500]
                + ("…" if len(st.session_state.resume_text) > 2500 else "")
            )

    pick_labels = [f"{j.get('company') or ''} · {j.get('title') or '未命名'}" for j in (jobs or [])]
    opts = ["手动粘贴 JD"] + (["从检索结果选择"] if pick_labels else [])
    source = st.radio(
        "岗位来源",
        opts,
        horizontal=True,
        key=f"{key_prefix}_resume_job_source",
    )
    target_job = None
    if source == "从检索结果选择" and pick_labels:
        pick = st.selectbox("选择岗位", pick_labels, key=f"{key_prefix}_resume_job_pick")
        target_job = jobs[pick_labels.index(pick)]
    else:
        manual_co = st.text_input("公司名", value="目标公司", key=f"{key_prefix}_resume_manual_co")
        manual_ti = st.text_input("岗位名", value="目标岗位", key=f"{key_prefix}_resume_manual_ti")
        manual_jd = st.text_area("粘贴岗位描述 JD", height=180, key=f"{key_prefix}_resume_manual_jd")
        if manual_jd.strip():
            target_job = {
                "company": manual_co.strip() or "目标公司",
                "title": manual_ti.strip() or "目标岗位",
                "location": "",
                "jd": manual_jd.strip(),
            }

    can_run = has_resume and target_job is not None and _ai.ai_ready()
    if not _ai.ai_ready():
        st.error("请先配置 AGNES_API_KEY")
    if st.button(
        "开始简历×岗位匹配",
        use_container_width=True,
        disabled=not can_run,
        key=f"{key_prefix}_resume_run",
    ):
        st.session_state.active_stage = "ai"
        with st.spinner("Agnes 正在对比简历与 JD…"):
            try:
                match = _ai.match_resume_to_job(
                    st.session_state.resume_text,
                    target_job,
                    user_profile=st.session_state.get("user_profile") or "",
                )
                key = f"{match.get('company')}|{match.get('title')}"
                st.session_state.resume_matches[key] = match
                st.session_state.flash = (
                    f"匹配完成：{match.get('verdict')} · {match.get('score')}/100"
                )
                st.session_state.active_stage = "deliver"
                st.rerun()
            except Exception as e:
                st.error(str(e))

    for _key, match in list((st.session_state.get("resume_matches") or {}).items())[::-1]:
        _render_resume_match(match)


def _render_ai_card(note: dict) -> None:
    if not note:
        return
    score = note.get("score") or 0
    verdict = html.escape(str(note.get("verdict") or ""))
    st.markdown(
        f'<div class="blueprint">'
        f'<div class="hd"><div class="nm">✨ AI 点评 · {html.escape(str(note.get("company") or ""))} · '
        f'{html.escape(str(note.get("title") or ""))}</div>'
        f'<div class="rl">{verdict} · {score}/100</div></div>'
        f'<div class="bd">'
        f'<b>摘要</b>：{html.escape(str(note.get("summary") or "—"))}<br/>'
        f'<b>匹配</b>：{html.escape(str(note.get("fit") or "—"))}<br/>'
        f'<b>缺口</b>：{html.escape(str(note.get("gaps") or "—"))}<br/>'
        f'<b>行动</b>：{html.escape(str(note.get("action") or "—"))}'
        f"</div></div>",
        unsafe_allow_html=True,
    )


def _link(label: str, href: str, ghost: bool = False) -> str:
    if not href:
        return ""
    cls = "btnx ghost" if ghost else "btnx"
    return (
        f'<a class="{cls}" href="{html.escape(href, quote=True)}" '
        f'target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>'
    )


def _hero_html() -> str:
    mascot = (
        f'<img class="hero-mascot" src="{_URI_HERO}" alt="{html.escape(BRAND_DAVINA)} 小助手" />'
        if _URI_HERO
        else ""
    )
    return (
        f'<div class="hero"><div>'
        f'<p class="eyebrow">{html.escape(BRAND_EN)} · {html.escape(BRAND_DAVINA)}</p>'
        f'<h1>{html.escape(BRAND_NAME)} <span>{html.escape(BRAND_CN)}</span></h1>'
        f'<p>{html.escape(BRAND_TAGLINE)}</p></div>{mascot}</div>'
    )


def _rail_pipeline(active: str, trace: Optional[dict] = None) -> None:
    nodes = get_agent_pipeline()
    done_ids = set()
    if trace:
        for s in trace.get("steps") or []:
            if s.get("status") == "done":
                done_ids.add(s.get("id"))
    mascot = (
        f'<img class="side-mascot" src="{_URI_HERO}" alt="" />' if _URI_HERO else ""
    )
    items = [mascot]
    for i, n in enumerate(nodes, 1):
        nid = n["id"]
        cls = "step"
        if nid == active:
            cls += " on live" if active not in ("deliver", "listen") else " on"
        elif nid in done_ids or (active == "deliver"):
            cls += " on"
        emoji = _STEP_EMOJI.get(nid, "✨")
        items.append(
            f'<div class="{cls}"><div class="n">{emoji}</div>'
            f'<div><div class="t">{html.escape(n["name"])}</div>'
            f'<div class="d">{html.escape(n.get("role") or n.get("desc") or "")}</div></div></div>'
        )
    st.markdown(
        '<div class="panel davina-rail"><h3>小助手流程</h3>' + "".join(items) + "</div>",
        unsafe_allow_html=True,
    )
    st.caption("完整拆解见「工作流」")


def _flow_band(active: str) -> None:
    nodes = get_agent_pipeline()
    cards = []
    for i, n in enumerate(nodes, 1):
        on = " on" if n["id"] == active else ""
        emoji = _STEP_EMOJI.get(n["id"], "✨")
        cards.append(
            f'<div class="flow-node{on}">'
            f'<div class="emoji">{emoji}</div>'
            f'<div class="role">{i:02d} · {html.escape(n.get("role") or "")}</div>'
            f'<div class="name">{html.escape(n["name"])}</div>'
            f'<div class="desc">{html.escape(n.get("desc") or "")}</div></div>'
        )
    st.markdown('<div class="flow-band">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def _render_blueprint() -> None:
    st.markdown("##### 小助手怎么工作")
    st.caption("每一步做什么、用哪些能力；跑完检索后可在「运行回放」看真实数据。")
    if _URI_STEPS:
        st.markdown(
            f'<img class="crew-banner" src="{_URI_STEPS}" alt="TalentRadar × Davina Agent 流程角色" />',
            unsafe_allow_html=True,
        )
    _flow_band(st.session_state.active_stage)
    for n in get_agent_pipeline():
        tools = "".join(
            f'<span class="met">{html.escape(t)}</span>' for t in (n.get("tools") or [])
        )
        emoji = _STEP_EMOJI.get(n["id"], "✨")
        st.markdown(
            f'<div class="blueprint"><div class="hd">'
            f'<div class="nm">{emoji} {html.escape(n["name"])}</div>'
            f'<div class="rl">{html.escape(n.get("role") or "")}</div></div>'
            f'<div class="bd">{html.escape(n.get("detail") or n.get("desc") or "")}</div>'
            f'<div class="tools">{tools}</div></div>',
            unsafe_allow_html=True,
        )


def _render_trace(trace: Optional[dict]) -> None:
    if not trace or not (trace.get("steps") or []):
        st.info("还没有运行记录。点「开始检索」后，这里会按时间轴回放每一步。")
        return

    meta_bits = []
    if trace.get("company"):
        meta_bits.append(str(trace["company"]))
    if trace.get("ats"):
        meta_bits.append(f"ATS · {trace['ats']}")
    if trace.get("portal"):
        meta_bits.append(str(trace["portal"]))
    if trace.get("mode") == "track":
        meta_bits.append(f"赛道扫描 · {trace.get('target') or ''}")
    st.caption(" · ".join(meta_bits) if meta_bits else "最近一次运行")

    # 漏斗摘要
    raw = matched = None
    for s in trace.get("steps") or []:
        m = s.get("metrics") or {}
        if s.get("id") == "fetch" and m.get("raw") is not None:
            raw = m.get("raw")
        if s.get("id") == "deliver" and m.get("matched") is not None:
            matched = m.get("matched")
    if raw is not None and matched is not None:
        st.markdown(
            f'<div class="stat-row" style="margin-top:.2rem">'
            f'<div class="stat-card"><div class="k">原始采集</div><div class="v">{raw}</div></div>'
            f'<div class="stat-card"><div class="k">最终命中</div><div class="v">{matched}</div></div>'
            f'<div class="stat-card"><div class="k">过滤掉</div><div class="v">{max(int(raw)-int(matched),0)}</div></div>'
            f'<div class="stat-card"><div class="k">步骤数</div><div class="v">{len(trace.get("steps") or [])}</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )

    rows = []
    for s in trace.get("steps") or []:
        status = s.get("status") or ""
        mets = []
        for k, v in (s.get("metrics") or {}).items():
            if k in ("stage", "source", "portal", "location_mode") and isinstance(v, str) and len(v) > 24:
                v = v[:24] + "…"
            cls = "met"
            if status == "error":
                cls += " err"
            elif k in ("matched", "after", "raw", "with_jd") and isinstance(v, (int, float)):
                cls += " ok"
            mets.append(f'<span class="{cls}">{html.escape(str(k))}={html.escape(str(v))}</span>')
        rows.append(
            f'<div class="trace-item"><div class="clock">{int(s.get("ms") or 0)}ms</div>'
            f'<div><div class="ttl">{html.escape(s.get("title") or "")}</div>'
            f'<div class="dtl">{html.escape(s.get("detail") or "")}</div>'
            f'<div class="mets">{"".join(mets)}</div></div></div>'
        )
    st.markdown(
        '<div class="panel" style="padding: .4rem 1rem 1rem"><h3>运行回放</h3>'
        + "".join(rows)
        + "</div>",
        unsafe_allow_html=True,
    )

    # 批量时展示各公司子轨迹摘要
    children = trace.get("company_traces") or []
    if children:
        st.markdown("##### 各公司子流程")
        for ct in children:
            co = ct.get("company") or ct.get("target") or "公司"
            steps = ct.get("steps") or []
            last = steps[-1] if steps else {}
            st.markdown(
                f"**{co}** · {ct.get('ats') or ''} · "
                f"{(last.get('metrics') or {}).get('matched', '—')} 命中"
            )
            with st.expander(f"展开 {co} 明细"):
                for s in steps:
                    st.write(f"`{s.get('ms')}ms` {s.get('title')} — {s.get('detail')}")


def _rail_interested() -> None:
    favs = list_interested_jobs()
    st.markdown(f'<div class="panel"><h3>感兴趣 · {len(favs)}</h3></div>', unsafe_allow_html=True)
    if not favs:
        st.caption("在岗位卡片点「加入感兴趣」")
        return
    for item in favs[:8]:
        st.markdown(
            f'<div class="fav"><div class="t">{html.escape(item.get("company") or "")} · '
            f'{html.escape(item.get("title") or "")}</div>'
            f'<div class="m">{html.escape(item.get("status") or "感兴趣")} · '
            f'{html.escape(item.get("location") or "")} · {html.escape(item.get("added_at") or "")}</div></div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        url = item.get("url") or item.get("portal_url") or ""
        if url:
            c1.markdown(_link("打开", url), unsafe_allow_html=True)
        if c2.button("移除", key=f"rm_side_{item.get('uid')}", use_container_width=True):
            remove_interested_job(item.get("uid") or "")
            st.rerun()
    if len(favs) > 8:
        st.caption(f"还有 {len(favs) - 8} 条，见「感兴趣」页")


def main() -> None:
    _init()
    tracks = list_profile_tracks()

    with st.sidebar:
        if _URI_HERO:
            st.markdown(
                f'<img class="side-mascot" src="{_URI_HERO}" alt="Davina" />',
                unsafe_allow_html=True,
            )
        st.markdown(f"### {BRAND_NAME}")
        st.caption(f"{BRAND_CN} · {BRAND_DAVINA}")
        app_view = render_sidebar_nav()
        st.divider()
        mode = "单公司精查"
        track = DEFAULT_TRACK if DEFAULT_TRACK in tracks else (tracks[0] if tracks else "")
        location_mode = DEFAULT_LOCATION_MODE
        recent_days = 0
        catalog = {"enabled": [], "enabled_count": 0, "system_total": 0, "available_to_add": [], "wishlist": []}
        meta = {}
        keyword = "产品"
        run_track = False
        target = ""
        max_companies = 1
        do_search = False

        if app_view != "prd":
            if _ai.ai_ready():
                st.success(f"Agnes 已接入 · {_ai.get_model()}")
            else:
                st.warning("未配置 AGNES_API_KEY（见 dashboard/.env）")
            st.text_area(
                "我的画像（给 AI 点评用）",
                key="user_profile",
                height=80,
                help="背景、目标岗位、城市偏好等，AI 会据此打分",
            )
            st.markdown("**上传简历（PDF / Word）**")
            up = st.file_uploader(
                "选择文件",
                type=["pdf", "docx"],
                accept_multiple_files=False,
                label_visibility="collapsed",
                key="resume_uploader",
            )
            if up is not None:
                try:
                    text, fmt = _resume.extract_resume_text(up.name, up.getvalue())
                    st.session_state.resume_text = text
                    st.session_state.resume_name = up.name
                    st.session_state.resume_format = fmt
                    st.success(f"已解析 {fmt} · {len(text)} 字")
                except Exception as e:
                    st.error(str(e))
            if st.session_state.get("resume_text"):
                st.caption(
                    f"当前简历：{st.session_state.get('resume_name') or '已上传'} · "
                    f"{len(st.session_state.resume_text)} 字"
                )
                if st.button("清除简历", use_container_width=True):
                    st.session_state.resume_text = ""
                    st.session_state.resume_name = ""
                    st.session_state.resume_format = ""
                    st.session_state.resume_matches = {}
                    st.rerun()
            mode = st.radio(
                "查询方式",
                ["单公司精查", "按赛道批量扫"],
                index=0 if DEFAULT_QUERY_MODE == "单公司精查" else 1,
            )
            track = st.selectbox(
                "赛道",
                tracks,
                index=tracks.index(DEFAULT_TRACK) if DEFAULT_TRACK in tracks else 0,
            )
            location_mode = st.radio(
                "地点",
                ["江浙沪优先", "不限地点"],
                index=0 if DEFAULT_LOCATION_MODE == "江浙沪优先" else 1,
            )
            recent_days = st.number_input("近 N 天（0=不限）", 0, 365, 0)

            catalog = track_company_catalog(track)
            meta = profile_track_meta(track)
            st.caption(f"已可检索 {catalog['enabled_count']} 家 · 全库 {catalog['system_total']} 家")

            keyword = st.text_input("关键词", value=meta.get("keywords") or "产品", key=f"kw_{track}_{mode}")
            run_track = mode == "按赛道批量扫"
            target = ""
            max_companies = 1

            if run_track:
                max_companies = st.slider(
                    "最多扫几家",
                    3,
                    min(15, max(3, catalog["enabled_count"] or 3)),
                    min(6, catalog["enabled_count"] or 3),
                )
            else:
                pick_source = st.radio("选公司", ["本赛道", "全库", "手动输入"], horizontal=True)
                if pick_source == "本赛道":
                    labels = [c["label"] for c in catalog["enabled"]] or ["（暂无）"]
                    idx = next((i for i, c in enumerate(catalog["enabled"]) if c["key"] == "shlab"), 0)
                    pick = st.selectbox("公司", labels, index=min(idx, max(len(labels) - 1, 0)))
                    target = next((c["key"] for c in catalog["enabled"] if c["label"] == pick), "")
                elif pick_source == "全库":
                    key_map = {c["label"]: c["key"] for c in catalog["enabled"] + catalog["available_to_add"]}
                    pick = st.selectbox("公司", sorted(key_map.keys()))
                    target = key_map.get(pick, "")
                else:
                    manual = st.text_input("公司名或 key", placeholder="智谱 / shlab / 中芯国际")
                    if manual.strip():
                        resolved = resolve_company_key(manual)
                        if resolved:
                            target = resolved
                            st.success(f"可检索：{company_display_name(resolved)}")
                        else:
                            st.warning("库中暂无此公司，无法自动拉岗。")
                            if st.button("登记到待接入并搜官网", use_container_width=True):
                                ret = try_add_company(track, manual.strip())
                                tip = {
                                    "message": ret.get("message"),
                                    "item": ret.get("item"),
                                    "suggest": suggest_scrapable(track, 5),
                                }
                                st.session_state.pending_tip = tip
                                st.session_state.flash = ret.get("message") or "已登记"
                                st.rerun()

            do_search = st.button("开始检索", use_container_width=True)

            with st.expander("公司池管理", expanded=False):
                st.markdown("**可自动拉岗**")
                st.markdown(
                    "<div>"
                    + "".join(f'<span class="chip chip-ok">{html.escape(c["name"])}</span>' for c in catalog["enabled"][:40])
                    + (" …" if len(catalog["enabled"]) > 40 else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )

                st.markdown("**粘贴门户链接 → 接入自动拉岗**")
                st.caption(
                    "搜到官网后，打开校招/社招页面，复制地址栏链接。"
                    "仅支持飞书（*.jobs.feishu.cn）、Moka（app.mokahr.com）、北森（*.zhiye.com）。"
                )
                conn_name = st.text_input("公司名称", key=f"conn_name_{track}", placeholder="例如：商汤科技")
                conn_url = st.text_input(
                    "招聘门户链接",
                    key=f"conn_url_{track}",
                    placeholder="https://xxx.jobs.feishu.cn 或 app.mokahr.com/…",
                )
                if conn_url.strip():
                    preview = parse_ats_portal_url(conn_url)
                    if preview:
                        st.success(f"已识别：{preview['type']} · {preview['arg1']}" + (f" / {preview['arg2']}" if preview.get("arg2") else ""))
                    else:
                        st.warning("链接格式暂不支持，请确认是飞书 / Moka / 北森门户页")
                if st.button("接入并加入本赛道", disabled=not (conn_name.strip() and conn_url.strip()), key=f"conn_btn_{track}"):
                    try:
                        ret = connect_company_from_url(track, conn_name.strip(), conn_url.strip())
                        st.session_state.flash = ret.get("message") or "已接入"
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

                wish = catalog.get("wishlist") or []
                st.markdown(f"**待接入（{len(wish)}）** — 先搜官网，再把门户链接贴到上方接入")
                for w in wish[:12]:
                    name = w.get("name") or ""
                    hint = w.get("search_hint") or w.get("url") or ""
                    st.markdown(
                        f'<span class="chip chip-miss">{html.escape(name)}</span>',
                        unsafe_allow_html=True,
                    )
                    b1, b2, b3 = st.columns([1, 1, 1.2])
                    if hint:
                        b1.markdown(_link("搜官网", hint, ghost=True), unsafe_allow_html=True)
                    wish_url = b3.text_input(
                        "门户链接",
                        key=f"wish_url_{track}_{name}",
                        placeholder="粘贴门户 URL",
                        label_visibility="collapsed",
                    )
                    if b2.button("接入", key=f"wish_conn_{track}_{name}", disabled=not wish_url.strip()):
                        try:
                            ret = connect_company_from_url(track, name, wish_url.strip())
                            st.session_state.flash = ret.get("message") or "已接入"
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    if st.button("删除登记", key=f"del_wish_{name}"):
                        remove_wishlist_by_name(track, name)
                        st.rerun()

                picked = st.multiselect(
                    "从全库加入本赛道（加入后可直接检索）",
                    [c["label"] for c in catalog["available_to_add"]],
                    key=f"add_{track}",
                )
                if st.button("确认加入本赛道", disabled=not picked):
                    keys = [c["key"] for c in catalog["available_to_add"] if c["label"] in picked]
                    added = add_keys_to_track(track, keys)
                    st.session_state.flash = f"已加入 {len(added)} 家，请在「本赛道」里选择并检索"
                    st.rerun()

    if app_view == "prd":
        render_prd_view()
        return

    if st.session_state.flash:
        st.toast(st.session_state.flash)
        st.session_state.flash = ""

    tip = st.session_state.pending_tip
    if tip:
        with st.container():
            st.info(tip.get("message") or "")
            item = tip.get("item") or {}
            if item.get("search_hint"):
                st.markdown(_link("打开招聘官网搜索", item["search_hint"]), unsafe_allow_html=True)
            suggests = tip.get("suggest") or []
            if suggests:
                st.caption("本赛道已可自动检索的公司（可直接选）：")
                st.write(" · ".join(s["name"] for s in suggests))
            if st.button("知道了"):
                st.session_state.pending_tip = None
                st.rerun()

    main_col, right_col = st.columns([1.85, 0.7], gap="large")

    with right_col:
        active = st.session_state.active_stage
        if do_search:
            active = "fetch"
        elif st.session_state.result:
            active = "deliver"
        trace = (st.session_state.result or {}).get("trace") if st.session_state.result else None
        _rail_pipeline(active, trace)
        _rail_interested()

    with main_col:
        st.markdown(_hero_html(), unsafe_allow_html=True)
        st.caption("手机端：关掉左侧栏后，点左上角橙色「菜单」按钮可再打开")
        if st.button("阅读本产品 PRD 文档 →", key="open_prd_main"):
            st.session_state.app_view = "prd"
            st.rerun()

        if do_search:
            st.session_state.error = None
            st.session_state.active_stage = "fetch"
            st.session_state.live_trace = []
            bar = st.progress(0.0, text="检索中…")
            live_box = st.empty()

            def _emit(row: dict) -> None:
                st.session_state.live_trace.append(row)
                st.session_state.active_stage = row.get("id") or "fetch"
                lines = []
                for s in st.session_state.live_trace[-6:]:
                    lines.append(f"· {s.get('title')} — {s.get('detail')}")
                live_box.markdown(
                    '<div class="panel"><h3>Agent 实时</h3>'
                    + "<br/>".join(html.escape(x) for x in lines)
                    + "</div>",
                    unsafe_allow_html=True,
                )

            try:
                if run_track:
                    def _cb(name: str, i: int, n: int) -> None:
                        bar.progress(i / max(n, 1), text=f"{name}（{i}/{n}）")
                        st.session_state.active_stage = "fetch"

                    st.session_state.result = search_track(
                        track_name=track,
                        keyword=keyword,
                        location_mode=location_mode,
                        recent_days=int(recent_days),
                        max_companies=int(max_companies),
                        progress_cb=_cb,
                        emit=_emit,
                    )
                else:
                    if not target:
                        raise ValueError("请先选择可检索的公司")
                    bar.progress(0.35, text=company_display_name(target))
                    st.session_state.result = search_jobs(
                        mode="local",
                        target=target,
                        keyword=keyword,
                        recent_days=int(recent_days),
                        location_mode=location_mode,
                        emit=_emit,
                    )
                st.session_state.active_stage = "deliver"
                bar.progress(1.0, text="完成")
            except Exception as e:
                st.session_state.result = None
                st.session_state.error = str(e)
                st.session_state.active_stage = "choose"
            finally:
                bar.empty()
                live_box.empty()

        if st.session_state.error:
            st.error(st.session_state.error)

        result = st.session_state.result
        if not result:
            search_img = (
                f'<img src="{_URI_SEARCH}" alt="Davina 正在找岗" />' if _URI_SEARCH else ""
            )
            st.markdown(
                f'<div class="empty">{search_img}'
                f'<div class="t">嗨，我是 {html.escape(BRAND_DAVINA)} · {html.escape(BRAND_NAME)} 小助手</div>'
                "打开左侧选公司点 <strong>开始检索</strong>；也可先上传简历，用手动 JD 做匹配。</div>",
                unsafe_allow_html=True,
            )
            st.markdown("##### 简历 × 岗位匹配")
            _render_resume_panel([], key_prefix="home")
            st.divider()
            _render_blueprint()
            return

        jobs = result.get("jobs") or []
        stats = result.get("stats") or {}
        kw_show = html.escape(str(result.get("keyword_used") or keyword)[:16])
        st.markdown(
            '<div class="stat-row">'
            f'<div class="stat-card"><div class="k">采集</div><div class="v">{result.get("total", 0)}</div></div>'
            f'<div class="stat-card"><div class="k">命中</div><div class="v">{result.get("matched", 0)}</div></div>'
            f'<div class="stat-card"><div class="k">含 JD</div><div class="v">{stats.get("with_jd", 0)}</div></div>'
            f'<div class="stat-card"><div class="k">关键词</div><div class="v" style="font-size:.95rem;padding-top:.4rem">{kw_show}</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )
        for err in result.get("errors") or []:
            st.warning(err)

        tab_jobs, tab_resume, tab_ai, tab_flow, tab_fav, tab_table, tab_export = st.tabs(
            ["岗位", "简历匹配", "AI 点评", "工作流", "感兴趣", "表格", "导出"]
        )

        with tab_resume:
            _render_resume_panel(jobs, key_prefix="tab")

        with tab_ai:

            st.caption("调用 Agnes 2.5 Flash：结合左侧「我的画像」对岗位打分与投递建议")
            if not _ai.ai_ready():
                st.error("请先在 dashboard/.env 配置 AGNES_API_KEY")
            else:
                n = st.slider("点评前 N 条命中岗位", 1, min(8, max(1, len(jobs) or 1)), min(3, max(1, len(jobs) or 1)))
                if st.button("开始 AI 批量点评", use_container_width=True, disabled=not jobs):
                    st.session_state.active_stage = "ai"
                    with st.spinner("Agnes 分析中…"):
                        batch = _ai.analyze_jobs_batch(
                            jobs,
                            user_profile=st.session_state.get("user_profile") or "",
                            limit=int(n),
                        )
                    st.session_state.ai_batch = batch
                    for item in batch:
                        uid_key = f"{item.get('company')}|{item.get('title')}"
                        st.session_state.ai_notes[uid_key] = item
                    st.session_state.flash = f"已完成 {len(batch)} 条 AI 点评"
                    st.session_state.active_stage = "deliver"
                    st.rerun()
            for note in st.session_state.get("ai_batch") or []:
                _render_ai_card(note)

        with tab_flow:
            st.markdown("##### 本次运行回放")
            _render_trace(result.get("trace"))
            st.divider()
            _render_blueprint()

        with tab_jobs:
            if not jobs:
                st.warning("无命中岗位。可放宽地点或缩短关键词。可到「工作流」看过滤掉了多少。")
            else:
                show_n = st.slider("展示条数", 5, min(60, len(jobs)), min(12, len(jobs)))
                interested_uids = {x.get("uid") for x in list_interested_jobs()}
                for idx, job in enumerate(jobs[:show_n]):
                    company = job.get("company") or ""
                    title = job.get("title") or "未命名"
                    loc = job.get("location") or ""
                    typ = job.get("type") or ""
                    date = job.get("date_fmt") or ""
                    bits = " · ".join(x for x in [loc, typ, date] if x)
                    jd = (job.get("jd") or "").strip()
                    jd_preview = (jd[:260] + "…") if len(jd) > 260 else (jd or "暂无完整 JD")
                    delay = min(idx * 0.035, 0.3)
                    st.markdown(
                        f'<div class="job-card" style="animation-delay:{delay:.2f}s">'
                        f'<div class="co">{html.escape(company)}</div>'
                        f'<h3 class="ti">{html.escape(title)}</h3>'
                        f'<div class="meta">{html.escape(bits)}</div>'
                        f'<div class="jd">{html.escape(jd_preview)}</div></div>',
                        unsafe_allow_html=True,
                    )
                    job_url = (job.get("url") or "").strip()
                    apply_url = (job.get("apply_url") or "").strip()
                    portal = (job.get("portal_url") or "").strip()
                    st.markdown(
                        _link("岗位详情", job_url)
                        + _link("备用", apply_url if apply_url != job_url else "", ghost=True)
                        + _link("招聘首页", portal, ghost=True),
                        unsafe_allow_html=True,
                    )
                    uid = _svc._job_uid(job)
                    already = uid in interested_uids
                    note_key = f"{company}|{title}"
                    c1, c2, c3, c4 = st.columns([1.0, 1.0, 1.0, 1.4])
                    if c1.button(
                        "已加入" if already else "加入感兴趣",
                        key=f"fav_{idx}_{uid}",
                        disabled=already,
                        use_container_width=True,
                    ):
                        add_interested_job(job)
                        st.session_state.flash = "已加入感兴趣清单"
                        st.rerun()
                    if c2.button("AI 点评", key=f"ai_{idx}_{uid}", use_container_width=True):
                        if not _ai.ai_ready():
                            st.session_state.flash = "未配置 AGNES_API_KEY"
                        else:
                            st.session_state.active_stage = "ai"
                            with st.spinner("Agnes 分析中…"):
                                note = _ai.analyze_job(
                                    job,
                                    user_profile=st.session_state.get("user_profile") or "",
                                )
                            st.session_state.ai_notes[note_key] = note
                            st.session_state.ai_batch = [note] + [
                                x
                                for x in (st.session_state.ai_batch or [])
                                if f"{x.get('company')}|{x.get('title')}" != note_key
                            ]
                            st.session_state.flash = "AI 点评完成，见「AI 点评」页"
                            st.session_state.active_stage = "deliver"
                            st.rerun()
                    if c3.button(
                        "简历匹配",
                        key=f"rm_{idx}_{uid}",
                        use_container_width=True,
                        disabled=not st.session_state.get("resume_text"),
                    ):
                        if not _ai.ai_ready():
                            st.session_state.flash = "未配置 AGNES_API_KEY"
                        elif not st.session_state.get("resume_text"):
                            st.session_state.flash = "请先在左侧上传简历"
                        else:
                            st.session_state.active_stage = "ai"
                            with st.spinner("简历×JD 匹配中…"):
                                match = _ai.match_resume_to_job(
                                    st.session_state.resume_text,
                                    job,
                                    user_profile=st.session_state.get("user_profile") or "",
                                )
                            st.session_state.resume_matches[note_key] = match
                            st.session_state.flash = "简历匹配完成，见「简历匹配」页"
                            st.session_state.active_stage = "deliver"
                            st.rerun()
                    if jd and len(jd) > 260:
                        with c4.expander("完整 JD"):
                            st.text(jd)
                    if note_key in (st.session_state.ai_notes or {}):
                        _render_ai_card(st.session_state.ai_notes[note_key])
                    if note_key in (st.session_state.resume_matches or {}):
                        _render_resume_match(st.session_state.resume_matches[note_key])

        with tab_fav:
            favs = list_interested_jobs()
            st.caption(f"共 {len(favs)} 条，保存在本地")
            if not favs:
                st.info("还没有感兴趣岗位。")
            for item in favs:
                st.markdown(f"**{item.get('company')} · {item.get('title')}**")
                st.caption(f"{item.get('location') or ''} · {item.get('added_at') or ''}")
                status = st.selectbox(
                    "状态",
                    ["感兴趣", "准备投递", "已投递", "面试中", "暂缓"],
                    index=["感兴趣", "准备投递", "已投递", "面试中", "暂缓"].index(item.get("status") or "感兴趣")
                    if (item.get("status") or "感兴趣") in ["感兴趣", "准备投递", "已投递", "面试中", "暂缓"]
                    else 0,
                    key=f"st_{item.get('uid')}",
                )
                note = st.text_input("备注", value=item.get("note") or "", key=f"note_{item.get('uid')}")
                if st.button("保存", key=f"save_{item.get('uid')}"):
                    update_interested_job(item.get("uid") or "", status=status, note=note)
                    st.session_state.flash = "已保存"
                    st.rerun()
                r1, r2 = st.columns(2)
                if item.get("url"):
                    r1.markdown(_link("打开岗位", item["url"]), unsafe_allow_html=True)
                if r2.button("移除", key=f"favtab_rm_{item.get('uid')}"):
                    remove_interested_job(item.get("uid") or "")
                    st.rerun()
                if item.get("jd"):
                    with st.expander("查看 JD"):
                        st.text(item["jd"])
                st.divider()
            if favs and st.button("清空感兴趣清单"):
                clear_interested_jobs()
                st.rerun()

        with tab_table:
            df = pd.DataFrame(
                [
                    {
                        "公司": j.get("company", ""),
                        "岗位": j.get("title", ""),
                        "地点": j.get("location", ""),
                        "类型": j.get("type", ""),
                        "日期": j.get("date_fmt", ""),
                        "链接": j.get("url") or "",
                    }
                    for j in jobs
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True, height=480)

        with tab_export:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                "下载检索结果 JSON",
                data=json.dumps(
                    {"product": BRAND_NAME, "jobs": jobs, "interested": list_interested_jobs()},
                    ensure_ascii=False,
                    indent=2,
                ),
                file_name=f"davina_{stamp}.json",
                mime="application/json",
                use_container_width=True,
            )
            st.download_button(
                "下载感兴趣清单",
                data=json.dumps(list_interested_jobs(), ensure_ascii=False, indent=2),
                file_name=f"davina_interested_{stamp}.json",
                mime="application/json",
                use_container_width=True,
            )
            csv_df = pd.DataFrame(
                [
                    {
                        "company": j.get("company", ""),
                        "title": j.get("title", ""),
                        "location": j.get("location", ""),
                        "url": j.get("url") or "",
                        "jd": j.get("jd", ""),
                    }
                    for j in jobs
                ]
            )
            st.download_button(
                "下载 CSV",
                data=csv_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"davina_{stamp}.csv",
                mime="text/csv",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
