from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class Material(BaseModel):
    name: str = Field(..., description="材料名称，如聊天截图、订单截图、物流记录")
    content: str = Field(..., description="OCR 后的文本、手动粘贴文本或文件摘要")


class AnalyzeRequest(BaseModel):
    case_title: str = Field(default="未命名维权案例")
    goal: str = Field(default="希望整理证据并生成合理申诉材料")
    materials: List[Material]


class TimelineItem(BaseModel):
    time: str
    event: str
    evidence: str


class AnalyzeResponse(BaseModel):
    summary: str
    extracted_facts: List[str]
    timeline: List[TimelineItem]
    risk_points: List[str]
    claim_strategy: str
    short_appeal_150: str
    full_letter: str
    next_actions: List[str]
    mode: str = Field(description="offline 或 llm")
