# -*- coding: utf-8 -*-
"""Davina · Agnes AI 接入（OpenAI 兼容 Chat Completions）"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

_DASHBOARD = Path(__file__).resolve().parent
_ENV_PATH = _DASHBOARD / ".env"

DEFAULT_BASE_URL = "https://apihub.agnes-ai.com/v1"
DEFAULT_MODEL = "agnes-2.5-flash"


def _load_dotenv() -> None:
    if not _ENV_PATH.is_file():
        return
    try:
        for ln in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except Exception:
        pass


_load_dotenv()


def _secret(name: str, default: str = "") -> str:
    v = (os.environ.get(name) or "").strip()
    if v:
        return v
    try:
        import streamlit as st

        if hasattr(st, "secrets") and name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return default


def get_api_key() -> str:
    return _secret("AGNES_API_KEY") or _secret("OPENAI_API_KEY")


def get_base_url() -> str:
    return _secret("AGNES_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def get_model() -> str:
    return _secret("AGNES_MODEL", DEFAULT_MODEL)


def ai_ready() -> bool:
    return bool(get_api_key())


def chat(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0.4,
    max_tokens: int = 800,
    timeout: int = 90,
) -> str:
    key = get_api_key()
    if not key:
        raise ValueError("未配置 AGNES_API_KEY。请在 dashboard/.env 写入密钥。")

    payload = {
        "model": get_model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        f"{get_base_url()}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"Agnes API HTTP {e.code}: {body}") from e
    except Exception as e:
        raise RuntimeError(f"Agnes API 请求失败: {e}") from e

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"Agnes 返回空结果: {str(data)[:200]}")
    msg = choices[0].get("message") or {}
    content = (msg.get("content") or "").strip()
    if not content:
        raise RuntimeError("Agnes 返回空内容")
    return content


def analyze_job(job: Dict[str, Any], user_profile: str = "") -> Dict[str, Any]:
    """对单个岗位做匹配点评：匹配度、亮点、风险、是否建议投。"""
    company = job.get("company") or ""
    title = job.get("title") or ""
    loc = job.get("location") or ""
    jd = (job.get("jd") or "")[:1800]
    profile = (user_profile or "").strip() or "秋招求职者，关注产品/AI 相关岗位，优先江浙沪。"

    system = (
        "你是秋招求职顾问 Agent。根据用户画像与岗位信息，用简洁中文给出可执行建议。"
        "不要编造 JD 里没有的福利或要求。输出严格 JSON，不要 markdown。"
    )
    user = {
        "画像": profile,
        "公司": company,
        "岗位": title,
        "地点": loc,
        "JD节选": jd or "（无完整 JD，请只根据标题与公司判断，并标明信息不足）",
        "输出字段": {
            "score": "0-100整数，匹配度",
            "verdict": "建议投|可关注|暂不建议 三选一",
            "fit": "匹配点，一句话",
            "gaps": "缺口或风险，一句话",
            "action": "下一步行动，一句话",
            "summary": "岗位一句话摘要",
        },
    }
    raw = chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0.3,
        max_tokens=600,
    )
    parsed = _parse_json_obj(raw)
    return {
        "score": int(parsed.get("score") or 0),
        "verdict": str(parsed.get("verdict") or ""),
        "fit": str(parsed.get("fit") or ""),
        "gaps": str(parsed.get("gaps") or ""),
        "action": str(parsed.get("action") or ""),
        "summary": str(parsed.get("summary") or ""),
        "raw": raw,
        "model": get_model(),
        "company": company,
        "title": title,
    }


def match_resume_to_job(
    resume_text: str,
    job: Dict[str, Any],
    user_profile: str = "",
) -> Dict[str, Any]:
    """简历全文 × 岗位 JD → 匹配度 + 优化建议。"""
    resume = (resume_text or "").strip()
    if len(resume) < 40:
        raise ValueError("简历正文太短，请重新上传可提取文字的 PDF/Word")

    company = job.get("company") or ""
    title = job.get("title") or ""
    loc = job.get("location") or ""
    jd = (job.get("jd") or "").strip()
    if not jd:
        jd = f"（无完整 JD）岗位标题：{title}；公司：{company}；地点：{loc}"

    # 控制 token：简历与 JD 截断
    resume_clip = resume[:6500]
    jd_clip = jd[:3500]
    profile = (user_profile or "").strip()

    system = (
        "你是资深校招简历顾问与岗位匹配专家。"
        "根据「简历正文」与「岗位描述」做匹配评估，并给出可执行的简历优化建议。"
        "不要编造简历里没有的经历；若信息不足请明确指出。"
        "输出严格 JSON，不要 markdown 代码块。"
    )
    user = {
        "求职画像补充": profile or "无",
        "目标公司": company,
        "目标岗位": title,
        "地点": loc,
        "岗位描述": jd_clip,
        "简历正文": resume_clip,
        "输出字段": {
            "score": "0-100整数，简历与该岗匹配度",
            "verdict": "高度匹配|部分匹配|匹配偏弱 三选一",
            "summary": "一句话总评",
            "strengths": ["匹配优势，2-4条短句"],
            "gaps": ["缺口/风险，2-4条短句"],
            "suggestions": ["简历优化建议，3-6条，具体可改"],
            "keywords_to_add": ["建议补进简历的关键词，3-8个"],
            "priority_edits": "最该先改的一处（一句话）",
        },
    }
    raw = chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0.35,
        max_tokens=1200,
    )
    parsed = _parse_json_obj(raw)

    def _list(key: str) -> List[str]:
        val = parsed.get(key)
        if isinstance(val, list):
            return [str(x).strip() for x in val if str(x).strip()]
        if isinstance(val, str) and val.strip():
            return [val.strip()]
        return []

    return {
        "score": int(parsed.get("score") or 0),
        "verdict": str(parsed.get("verdict") or ""),
        "summary": str(parsed.get("summary") or ""),
        "strengths": _list("strengths"),
        "gaps": _list("gaps"),
        "suggestions": _list("suggestions"),
        "keywords_to_add": _list("keywords_to_add"),
        "priority_edits": str(parsed.get("priority_edits") or ""),
        "company": company,
        "title": title,
        "model": get_model(),
        "raw": raw,
    }


def analyze_jobs_batch(
    jobs: List[Dict[str, Any]],
    user_profile: str = "",
    limit: int = 5,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for job in (jobs or [])[: max(1, min(limit, 8))]:
        try:
            out.append(analyze_job(job, user_profile))
        except Exception as e:
            out.append(
                {
                    "company": job.get("company") or "",
                    "title": job.get("title") or "",
                    "score": 0,
                    "verdict": "失败",
                    "fit": "",
                    "gaps": str(e),
                    "action": "稍后重试",
                    "summary": "",
                    "error": str(e),
                    "model": get_model(),
                }
            )
    return out


def _parse_json_obj(text: str) -> Dict[str, Any]:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[4:].strip()
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    # 尝试截取第一个 { ... }
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        try:
            obj = json.loads(t[i : j + 1])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return {
        "score": 60,
        "verdict": "可关注",
        "fit": "",
        "gaps": "",
        "action": "",
        "summary": t[:180],
    }
