# -*- coding: utf-8 -*-
"""
秋招情报雷达 · Streamlit 看板
基于 Hiring Radar 数据源，可视化查询公司在招岗位。
启动：streamlit run app.py
"""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

import radar_service as svc

st.set_page_config(
    page_title="秋招情报雷达",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- 视觉 ----------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Syne:wght@600;700;800&display=swap');

html, body, [class*="css"] {
  font-family: 'DM Sans', sans-serif;
}
.stApp {
  background:
    radial-gradient(1200px 600px at 10% -10%, #d8efe8 0%, transparent 55%),
    radial-gradient(900px 500px at 95% 0%, #f0e6d8 0%, transparent 50%),
    linear-gradient(180deg, #f7f4ef 0%, #eef2f0 100%);
}
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }

.hero {
  padding: 1.6rem 0 0.4rem 0;
}
.brand {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: clamp(2rem, 4vw, 2.75rem);
  letter-spacing: -0.03em;
  color: #14352f;
  margin: 0;
  line-height: 1.1;
}
.brand span { color: #1f7a66; }
.tagline {
  margin: 0.55rem 0 0;
  color: #4a5c57;
  font-size: 1.05rem;
  max-width: 36rem;
}
.panel {
  background: rgba(255,255,255,0.72);
  border: 1px solid rgba(20,53,47,0.08);
  border-radius: 16px;
  padding: 1.1rem 1.2rem;
  backdrop-filter: blur(8px);
}
.stat-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin: 0.8rem 0 1rem;
}
.stat {
  background: #14352f;
  color: #f4faf7;
  border-radius: 12px;
  padding: 0.7rem 1rem;
  min-width: 7.5rem;
}
.stat .n {
  font-family: 'Syne', sans-serif;
  font-size: 1.45rem;
  font-weight: 700;
  line-height: 1;
}
.stat .l {
  font-size: 0.78rem;
  opacity: 0.75;
  margin-top: 0.25rem;
}
.chip {
  display: inline-block;
  background: #e6f2ee;
  color: #1f5c4e;
  border-radius: 8px;
  padding: 0.25rem 0.55rem;
  margin: 0.15rem 0.25rem 0.15rem 0;
  font-size: 0.82rem;
}
.job-card {
  background: #fff;
  border: 1px solid rgba(20,53,47,0.08);
  border-radius: 14px;
  padding: 1rem 1.1rem;
  margin-bottom: 0.75rem;
}
.job-card h3 {
  font-family: 'Syne', sans-serif;
  font-size: 1.05rem;
  margin: 0 0 0.35rem;
  color: #14352f;
}
.meta { color: #5a6b66; font-size: 0.88rem; }
.jd {
  margin-top: 0.65rem;
  color: #2c3d38;
  font-size: 0.9rem;
  white-space: pre-wrap;
  line-height: 1.55;
  max-height: 220px;
  overflow: auto;
  background: #f6f8f7;
  border-radius: 10px;
  padding: 0.75rem;
}
a.cta {
  display: inline-block;
  margin-top: 0.55rem;
  color: #1f7a66;
  font-weight: 600;
  text-decoration: none;
}
div[data-testid="stSidebar"] {
  background: #102924;
}
div[data-testid="stSidebar"] * { color: #e8f2ee !important; }
div[data-testid="stSidebar"] .stSelectbox label,
div[data-testid="stSidebar"] .stTextInput label,
div[data-testid="stSidebar"] .stNumberInput label,
div[data-testid="stSidebar"] .stSlider label {
  color: #b7d0c8 !important;
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def _options():
    return svc.company_options(prefer_local=True)


def _init_state():
    if "result" not in st.session_state:
        st.session_state.result = None
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""


def run_search(company_key: str, keyword: str, recent_days: int):
    with st.spinner("正在拉取官方招聘接口，通常需要 20～60 秒…"):
        result = svc.search_jobs(company_key, keyword=keyword, recent_days=recent_days)
    st.session_state.result = result
    st.session_state.last_query = f"{company_key}|{keyword}|{recent_days}"


def main():
    _init_state()
    options = _options()
    label_to_key = {label: key for label, key in options}
    labels = [label for label, _ in options]

    # ---- 侧边栏：查询条件 ----
    with st.sidebar:
        st.markdown("### 查询条件")
        company_label = st.selectbox("目标公司", labels, index=0)
        company_key = label_to_key[company_label]
        keyword = st.text_input("关键词（逗号=或）", placeholder="产品,AI,校招")
        recent_days = st.slider("仅近 N 天（0=不限）", 0, 90, 0)
        limit_view = st.number_input("页面展示条数", min_value=5, max_value=200, value=20, step=5)
        search = st.button("开始检索", type="primary", use_container_width=True)
        st.caption("数据来自企业官方招聘门户公开接口 · 本机运行不上传")

    # ---- 主区 Hero ----
    st.markdown(
        """
<div class="hero">
  <h1 class="brand">秋招情报<span>雷达</span></h1>
  <p class="tagline">把分散在各公司官网的在招岗位，聚合成一张可检索、可导出的情报看板。</p>
</div>
""",
        unsafe_allow_html=True,
    )

    if search:
        run_search(company_key, keyword.strip(), int(recent_days))

    result = st.session_state.result
    if result is None:
        st.markdown(
            """
<div class="panel">
  <p style="margin:0;color:#4a5c57;">在左侧选择公司与关键词，点击「开始检索」。</p>
  <p style="margin:0.6rem 0 0;color:#6a7d77;font-size:0.92rem;">
    推荐先试：智谱AI · 关键词「产品」；或 月之暗面 · 关键词「算法」。
  </p>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    if not result["ok"]:
        st.error(f"查询失败：{result['error']}")
        st.info("可换一家公司重试；中国公司查询较慢属正常。")
        return

    jobs = result["jobs"]
    # ---- 摘要 ----
    st.markdown(
        f"""
<div class="stat-row">
  <div class="stat"><div class="n">{result['total']}</div><div class="l">在招总数</div></div>
  <div class="stat"><div class="n">{result['matched']}</div><div class="l">关键词命中</div></div>
  <div class="stat"><div class="n">{sum(1 for j in jobs if j.get('jd'))}</div><div class="l">含完整 JD</div></div>
  <div class="stat"><div class="n">{result['source']}</div><div class="l">数据源</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    if result["loc_top"] or result["dept_top"]:
        chips = []
        for k, v in result["loc_top"][:6]:
            chips.append(f'<span class="chip">📍 {k} ×{v}</span>')
        for k, v in result["dept_top"][:4]:
            chips.append(f'<span class="chip">🏷 {k} ×{v}</span>')
        st.markdown("".join(chips), unsafe_allow_html=True)

    # ---- 表格 + 卡片 ----
    rows = svc.jobs_to_rows(jobs, limit=int(limit_view))
    if not rows:
        st.warning("当前条件下没有命中岗位，试试换关键词或把「近 N 天」调为 0。")
        return

    tab_cards, tab_table, tab_export = st.tabs(["岗位卡片", "表格视图", "导出"])

    with tab_cards:
        for r in rows:
            title = r["岗位"] or "未命名岗位"
            company = r["公司"] or "—"
            loc = r["地点"] or "地点未知"
            typ = r["类型"] or ""
            dept = r["部门"] or ""
            date = r["日期"] or ""
            link = r["链接"]
            jd = (r["JD"] or "").strip()
            jd_preview = jd[:1200] + ("…" if len(jd) > 1200 else "")
            link_html = f'<a class="cta" href="{link}" target="_blank" rel="noopener">查看官网 JD →</a>' if link else ""
            st.markdown(
                f"""
<div class="job-card">
  <h3>{company} · {title}</h3>
  <div class="meta">{loc}{' · ' + typ if typ else ''}{' · ' + dept if dept else ''}{' · ' + str(date) if date else ''}</div>
  {f'<div class="jd">{jd_preview}</div>' if jd_preview else ''}
  {link_html}
</div>
""",
                unsafe_allow_html=True,
            )

    with tab_table:
        df = pd.DataFrame(rows)
        show = df.drop(columns=["JD"], errors="ignore")
        st.dataframe(show, use_container_width=True, hide_index=True)

    with tab_export:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        df_all = pd.DataFrame(svc.jobs_to_rows(jobs))
        csv_bytes = df_all.to_csv(index=False).encode("utf-8-sig")
        json_bytes = json.dumps(
            {
                "source": result["source"],
                "total": result["total"],
                "matched": result["matched"],
                "jobs": jobs,
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "下载 CSV（Excel 可开）",
                data=csv_bytes,
                file_name=f"jobs_{ts}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "下载 JSON（喂给 Agent）",
                data=json_bytes,
                file_name=f"jobs_{ts}.json",
                mime="application/json",
                use_container_width=True,
            )
        st.caption("导出内容在你本机生成，不会上传到任何服务器。")


if __name__ == "__main__":
    main()
