from __future__ import annotations

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from .schemas import AnalyzeRequest

load_dotenv()

SYSTEM_PROMPT = """
你是 ClaimPilot，一个多模态维权证据链 Agent。你的任务不是煽动用户，而是把分散材料整理为事实清楚、证据明确、诉求合理的申诉材料。
请输出严格 JSON，字段包括 summary, extracted_facts, timeline, risk_points, claim_strategy, short_appeal_150, full_letter, next_actions。
timeline 每项包含 time, event, evidence。short_appeal_150 必须不超过 150 个中文字符。
""".strip()


def llm_enabled() -> bool:
    return os.getenv("USE_LLM", "false").lower() == "true" and bool(os.getenv("MIMO_API_KEY"))


def build_user_prompt(req: AnalyzeRequest) -> str:
    materials = "\n\n".join(f"### {m.name}\n{m.content}" for m in req.materials)
    return f"""
案例标题：{req.case_title}
用户目标：{req.goal}

材料：
{materials}

请像一个证据链整理 Agent 一样输出 JSON。
""".strip()


async def call_mimo(req: AnalyzeRequest) -> dict[str, Any]:
    base_url = os.getenv("MIMO_BASE_URL", "").rstrip("/")
    api_key = os.getenv("MIMO_API_KEY", "")
    model = os.getenv("MIMO_MODEL", "mimo-agent-model")
    if not base_url or not api_key:
        raise RuntimeError("MIMO_BASE_URL 或 MIMO_API_KEY 未配置")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(req)},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    parsed["mode"] = "llm"
    return parsed
