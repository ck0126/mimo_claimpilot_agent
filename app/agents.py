from __future__ import annotations

from .llm_client import call_mimo, llm_enabled
from .offline_engine import run_offline
from .schemas import AnalyzeRequest, AnalyzeResponse


async def analyze_case(req: AnalyzeRequest) -> AnalyzeResponse:
    if llm_enabled():
        try:
            data = await call_mimo(req)
            return AnalyzeResponse(**data)
        except Exception as exc:  # fallback keeps demo stable
            data = run_offline(req)
            data["summary"] += f"（LLM 调用失败，已自动切换离线模式：{exc}）"
            return AnalyzeResponse(**data)
    return AnalyzeResponse(**run_offline(req))
