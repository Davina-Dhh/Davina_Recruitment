# -*- coding: utf-8 -*-
"""共享页面外观：主题 CSS + 隐藏 Deploy。"""
from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_ASSETS = Path(__file__).resolve().parent / "assets"


def apply_chrome() -> None:
    components.html(
        """
<script>
(function () {
  const root = window.parent.document;
  const kill = () => {
    const sels = [
      '[data-testid="stToolbar"]',
      '[data-testid="stAppDeployButton"]',
      '[data-testid="stDecoration"]',
      '[data-testid="stStatusWidget"]',
      '.stDeployButton', '.stAppDeployButton',
      '#MainMenu', 'footer',
      'div[data-testid="stToolbarActions"]',
      'a[href*="share.streamlit"]',
      'a[href*="deploy"]',
    ];
    sels.forEach((s) => root.querySelectorAll(s).forEach((el) => { el.style.display = 'none'; }));
  };
  kill();
  new MutationObserver(kill).observe(root.body, { childList: true, subtree: true });
})();
</script>
""",
        height=0,
    )
    css_path = _ASSETS / "theme.css"
    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8")
        import streamlit as st

        st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)
        st.markdown(
            """
<style>
.prd-wrap { max-width: 820px; margin: 0 auto; }
.prd-wrap h2 {
  font-family: "Fredoka", "Noto Sans SC", sans-serif !important;
  color: #3F2A22; font-size: 1.35rem; margin: 1.4rem 0 .55rem;
}
.prd-wrap h3 {
  font-family: "Fredoka", "Noto Sans SC", sans-serif !important;
  color: #FF6B4A; font-size: 1.05rem; margin: 1rem 0 .4rem;
}
.prd-wrap p, .prd-wrap li { color: #5C4038; line-height: 1.65; font-size: .95rem; }
.prd-wrap table { width: 100%; border-collapse: collapse; margin: .5rem 0 1rem; font-size: .88rem; }
.prd-wrap th, .prd-wrap td {
  border: 2px solid rgba(63,42,34,.08); padding: .55rem .65rem; text-align: left;
  background: #FFFBF7;
}
.prd-wrap th { background: #FFE8D6; color: #3F2A22; font-weight: 800; }
.prd-card {
  background: rgba(255,251,247,.94); border: 2.5px solid rgba(63,42,34,.08);
  border-radius: 24px; padding: 1.1rem 1.25rem; margin: .7rem 0;
  box-shadow: 0 8px 0 rgba(63,42,34,.06), 0 12px 28px rgba(255,107,74,.12);
}
</style>
""",
            unsafe_allow_html=True,
        )
