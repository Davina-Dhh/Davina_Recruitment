# -*- coding: utf-8 -*-
"""中文文件名兼容入口 —— 与 davina_workbench.py 同一套逻辑。

推荐启动：
  cd dashboard
  streamlit run davina_workbench.py
也可：
  streamlit run Davina秋招工作台.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_DASH = Path(__file__).resolve().parent
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

import davina_workbench as _app  # noqa: E402

if __name__ == "__main__":
    _app.main()
