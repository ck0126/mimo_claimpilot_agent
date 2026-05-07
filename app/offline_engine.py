from __future__ import annotations

import re
from collections import OrderedDict
from typing import Iterable, List

from .schemas import AnalyzeRequest, TimelineItem

TIME_PATTERNS = [
    r"\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?\s*\d{0,2}:?\d{0,2}",
    r"\d{1,2}月\d{1,2}日\s*\d{0,2}:?\d{0,2}",
    r"\d{1,2}:\d{2}",
    r"昨天|今天|前天|上午|下午|晚上|中午|凌晨",
]
MONEY_PATTERN = r"(?:¥|￥)?\s*\d+(?:\.\d+)?\s*元?"
PROMISE_WORDS = ["答应", "承诺", "保证", "同意", "可以", "特快", "加急", "顺丰", "当天", "次日"]
BREACH_WORDS = ["未", "没有", "没", "延误", "标快", "拒绝", "退回", "丢失", "损失", "差价", "补偿"]


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"[。！？；;\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def extract_times(text: str) -> List[str]:
    result: list[str] = []
    for pat in TIME_PATTERNS:
        result.extend(re.findall(pat, text))
    return result


def extract_money(text: str) -> List[str]:
    return [m.strip() for m in re.findall(MONEY_PATTERN, text) if re.search(r"\d", m)]


def unique_keep_order(items: Iterable[str]) -> List[str]:
    return list(OrderedDict.fromkeys([i.strip() for i in items if i.strip()]))


def extract_facts(req: AnalyzeRequest) -> List[str]:
    facts: list[str] = []
    for material in req.materials:
        for sent in split_sentences(material.content):
            hit = any(w in sent for w in PROMISE_WORDS + BREACH_WORDS) or re.search(MONEY_PATTERN, sent)
            if hit:
                facts.append(f"【{material.name}】{sent}")
    if not facts:
        facts.append("已收到材料，但文本中缺少明显的时间、金额、承诺或违约关键词，建议补充聊天记录、订单页、物流页。")
    return unique_keep_order(facts)[:12]


def build_timeline(req: AnalyzeRequest) -> List[TimelineItem]:
    items: list[TimelineItem] = []
    for material in req.materials:
        sentences = split_sentences(material.content)
        for sent in sentences:
            times = extract_times(sent)
            if times:
                items.append(TimelineItem(time=times[0], event=sent[:80], evidence=material.name))
    if not items:
        for idx, material in enumerate(req.materials[:5], start=1):
            items.append(TimelineItem(time=f"材料{idx}", event=split_sentences(material.content)[0][:80] if split_sentences(material.content) else "待补充", evidence=material.name))
    return items[:8]


def analyze_risks(req: AnalyzeRequest) -> List[str]:
    all_text = "\n".join(m.content for m in req.materials)
    risks: list[str] = []
    if any(w in all_text for w in ["答应", "承诺", "同意", "可以"]):
        risks.append("存在明确承诺或确认记录，可作为平台判断商家/服务方责任的重要依据。")
    if "特快" in all_text and "标快" in all_text:
        risks.append("材料中同时出现“特快”和“标快”，可突出承诺服务与实际履约不一致。")
    if re.search(MONEY_PATTERN, all_text):
        risks.append("材料中包含金额信息，应把差价、额外支出、直接损失分别列清。")
    if any(w in all_text for w in ["急用", "比赛", "考试", "就医", "出行"]):
        risks.append("存在紧急使用场景，可说明延误造成的实际影响，但诉求仍建议围绕直接损失展开。")
    if not risks:
        risks.append("目前证据链偏弱，建议补充：对方承诺截图、实际履约截图、付款凭证、损失凭证。")
    return risks


def short_appeal(req: AnalyzeRequest, facts: List[str]) -> str:
    base = (
        f"本人就“{req.case_title}”申请平台介入。材料显示，对方存在承诺与实际履约不一致，"
        f"并造成额外费用或时间损失。请平台核实聊天记录、订单/物流/付款凭证，支持我的合理诉求：{req.goal}。"
    )
    return base[:150]


def full_letter(req: AnalyzeRequest, facts: List[str], risks: List[str]) -> str:
    fact_text = "\n".join(f"{i+1}. {f}" for i, f in enumerate(facts[:8]))
    risk_text = "\n".join(f"{i+1}. {r}" for i, r in enumerate(risks[:6]))
    return f"""投诉/申诉说明

一、基本情况
本人就“{req.case_title}”申请平台协助处理。我的核心诉求是：{req.goal}。

二、主要证据与事实
{fact_text}

三、责任与影响说明
{risk_text}

四、处理诉求
请平台结合聊天记录、订单记录、物流记录、付款凭证等材料，核实对方是否存在承诺未履行、服务不一致、额外费用由消费者承担等问题。本人希望平台支持合理退款、退还差价、补偿直接损失或要求对方给出明确处理方案。

五、补充说明
本人愿意继续提供原始截图、订单编号、物流编号、付款记录等材料。希望平台尽快介入，避免争议继续扩大。"""


def run_offline(req: AnalyzeRequest) -> dict:
    facts = extract_facts(req)
    timeline = build_timeline(req)
    risks = analyze_risks(req)
    return {
        "summary": f"已将“{req.case_title}”整理为可提交的证据链草案。当前重点是证明承诺、实际履约、损失金额与诉求之间的对应关系。",
        "extracted_facts": facts,
        "timeline": timeline,
        "risk_points": risks,
        "claim_strategy": "先要求平台核实承诺与实际履约是否一致；诉求优先写直接损失和差价，避免夸大间接损失；如果平台拒绝，再补充原始截图和费用凭证进行二次申诉。",
        "short_appeal_150": short_appeal(req, facts),
        "full_letter": full_letter(req, facts, risks),
        "next_actions": [
            "补充原始聊天截图，保留对方承诺的上下文。",
            "补充订单页、物流页、付款凭证，形成闭环证据。",
            "将诉求拆成：退差价、补偿直接损失、要求书面说明。",
            "提交时避免情绪化措辞，突出事实、时间、金额和证据。",
        ],
        "mode": "offline",
    }
