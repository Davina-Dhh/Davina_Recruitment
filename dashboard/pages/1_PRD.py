# -*- coding: utf-8 -*-
"""Davina 秋招 · 产品 PRD 页"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_DASHBOARD = Path(__file__).resolve().parent.parent
if str(_DASHBOARD) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD))

from my_targets import BRAND_NAME, BRAND_TAGLINE  # noqa: E402
from ui_chrome import apply_chrome  # noqa: E402

st.set_page_config(
    page_title=f"PRD · {BRAND_NAME}",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

apply_chrome()

with st.sidebar:
    st.markdown(f"### {BRAND_NAME}")
    st.caption(BRAND_TAGLINE)
    st.page_link("davina_workbench.py", label="返回工作台", icon="🏠")
    st.page_link("pages/1_PRD.py", label="产品 PRD", icon="📄")
    st.divider()
    prd_path = _DASHBOARD / "docs" / "PRD.md"
    if prd_path.is_file():
        st.download_button(
            "下载 PRD Markdown",
            data=prd_path.read_text(encoding="utf-8"),
            file_name="Davina_秋招_PRD.md",
            mime="text/markdown",
            use_container_width=True,
        )

st.markdown(
    f'<div class="hero" style="grid-template-columns:1fr">'
    f'<div><p class="eyebrow">PRODUCT REQUIREMENTS</p>'
    f'<h1>{BRAND_NAME} <span>产品 PRD</span></h1>'
    f'<p>系统内可读的产品需求文档 · 可下载 Markdown</p></div></div>',
    unsafe_allow_html=True,
)

st.page_link("davina_workbench.py", label="← 返回 Davina 秋招工作台")

prd_file = _DASHBOARD / "docs" / "PRD.md"
if not prd_file.is_file():
    st.error("未找到 docs/PRD.md")
else:
    body = prd_file.read_text(encoding="utf-8")
    st.markdown('<div class="prd-wrap prd-card">', unsafe_allow_html=True)
    st.markdown(body)
    st.markdown("</div>", unsafe_allow_html=True)
