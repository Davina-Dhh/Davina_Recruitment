# -*- coding: utf-8 -*-
"""TalentRadar · 产品 PRD（独立 pages 入口，可选）"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_DASHBOARD = Path(__file__).resolve().parent.parent
if str(_DASHBOARD) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD))

from ui_chrome import apply_chrome, render_prd_view  # noqa: E402

st.set_page_config(
    page_title="PRD · TalentRadar",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

apply_chrome()
st.session_state["app_view"] = "prd"
render_prd_view()
