# -*- coding: utf-8 -*-
"""Windows 控制台常为 GBK，直接 print 含特殊 Unicode 的 JSON 会崩。统一 UTF-8 写 stdout。"""
from __future__ import annotations

import json
import sys
from typing import Any


def emit_json(obj: Any) -> None:
    raw = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
    except Exception:
        # 极少数环境无 buffer 时退回 ascii JSON
        print(json.dumps(obj, ensure_ascii=True))
