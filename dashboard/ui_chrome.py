# -*- coding: utf-8 -*-
"""共享页面外观：主题 CSS + 隐藏 Deploy + 手机侧栏菜单按钮。"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_ASSETS = Path(__file__).resolve().parent / "assets"

_SIDEBAR_JS = """
<script>
(function () {
  const root = window.parent.document;

  const killDeploy = () => {
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

  const clickOpen = () => {
    const candidates = [
      root.querySelector('[data-testid="stSidebarCollapsedControl"] button'),
      root.querySelector('[data-testid="stExpandSidebarButton"]'),
      root.querySelector('button[kind="header"]'),
      root.querySelector('button[data-testid="baseButton-header"]'),
      root.querySelector('[data-testid="stBaseButton-headerNoPadding"]'),
    ].filter(Boolean);
    for (const b of candidates) {
      try { b.click(); return true; } catch (e) {}
    }
    // last resort: keyboard / aria
    const any = root.querySelector('[aria-label*="keyboard"], [aria-label*="sidebar"], [aria-label*="Sidebar"]');
    if (any && any.click) { try { any.click(); return true; } catch (e) {} }
    return false;
  };

  const sidebarOpen = () => {
    const side = root.querySelector('[data-testid="stSidebar"]');
    if (!side) return false;
    const r = side.getBoundingClientRect();
    return r.width > 60 && r.left > -20;
  };

  const styleNativeCollapsed = () => {
    const wrap = root.querySelector('[data-testid="stSidebarCollapsedControl"]');
    if (!wrap) return;
    wrap.style.cssText = [
      'display:flex',
      'visibility:visible',
      'opacity:1',
      'position:fixed',
      'top:12px',
      'left:12px',
      'z-index:2147483646',
      'pointer-events:auto',
    ].join(' !important;') + ' !important;';
    const btn = wrap.querySelector('button') || wrap;
    if (btn && btn.style) {
      btn.style.cssText = [
        'display:flex',
        'align-items:center',
        'justify-content:center',
        'width:46px',
        'height:46px',
        'border-radius:999px',
        'background:#FF6B4A',
        'color:#fff',
        'border:none',
        'box-shadow:0 8px 20px rgba(255,107,74,.4)',
        'cursor:pointer',
      ].join(' !important;') + ' !important;';
    }
  };

  const ensureFab = () => {
    let fab = root.getElementById('davina-sidebar-fab');
    if (sidebarOpen()) {
      if (fab) fab.style.display = 'none';
      return;
    }
    styleNativeCollapsed();
    if (!fab) {
      fab = root.createElement('button');
      fab.id = 'davina-sidebar-fab';
      fab.type = 'button';
      fab.setAttribute('aria-label', '打开菜单');
      fab.textContent = '菜单';
      fab.onclick = function (e) {
        e.preventDefault();
        e.stopPropagation();
        clickOpen();
        setTimeout(tick, 200);
      };
      root.body.appendChild(fab);
    }
    fab.style.cssText = [
      'position:fixed',
      'top:12px',
      'left:12px',
      'z-index:2147483647',
      'display:inline-flex',
      'align-items:center',
      'justify-content:center',
      'min-width:52px',
      'height:44px',
      'padding:0 14px',
      'border:none',
      'border-radius:999px',
      'background:linear-gradient(135deg,#FF6B4A,#FF8F6B)',
      'color:#fff',
      'font-weight:800',
      'font-size:14px',
      'font-family:Nunito,Noto Sans SC,sans-serif',
      'box-shadow:0 8px 22px rgba(255,107,74,.45)',
      'cursor:pointer',
      'pointer-events:auto',
    ].join(';');
  };

  const tick = () => {
    killDeploy();
    ensureFab();
  };

  tick();
  setInterval(tick, 800);
  new MutationObserver(tick).observe(root.body, { childList: true, subtree: true });
})();
</script>
"""


def apply_chrome() -> None:
    components.html(_SIDEBAR_JS, height=0)
    css_path = _ASSETS / "theme.css"
    if css_path.is_file():
        css = css_path.read_text(encoding="utf-8")
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

/* 手机：强制露出侧栏展开控件 */
[data-testid="stSidebarCollapsedControl"] {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  position: fixed !important;
  top: 12px !important;
  left: 12px !important;
  z-index: 999999 !important;
  pointer-events: auto !important;
}
header[data-testid="stHeader"] {
  background: transparent !important;
  height: auto !important;
  min-height: 3.25rem !important;
}
</style>
""",
            unsafe_allow_html=True,
        )
