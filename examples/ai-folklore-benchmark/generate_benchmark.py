#!/usr/bin/env python3
"""Compile 16 widely repeated AI-engineering claims against their actual sources."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

CASE_DIR = Path(__file__).resolve().parent
SKILL_ROOT = CASE_DIR.parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(CASE_DIR))

from knowledge_compiler import compile_claim  # noqa: E402
from knowledge_compiler.knowledge_document import (  # noqa: E402
    render_knowledge_document,
    validate_source_bundle,
)
from sources import CAPTURE_DATE, SOURCES  # noqa: E402

REVIEW_DIR = CASE_DIR / "adversarial-reviews"
FIRST_PASS_REVIEWER = "claude-opus-5"


def anchor(text: str, fragment: str) -> Dict[str, Any]:
    start = text.index(fragment)
    return {"text": fragment, "start": start, "end": start + len(fragment)}


def ir(
    claim_id: str,
    text: str,
    subject: str,
    predicate: str,
    object_: str,
    claimed_scope: str | None = None,
) -> Dict[str, Any]:
    anchors = {
        "subject": anchor(text, subject),
        "predicate": anchor(text, predicate),
        "object": anchor(text, object_),
    }
    if claimed_scope:
        anchors["scope"] = anchor(text, claimed_scope)
    return {
        "claim_id": claim_id,
        "source_text": text,
        "operator": "FACT",
        "subject": subject,
        "predicate": predicate,
        "object": object_,
        "polarity": "POSITIVE",
        "quantifier": "UNSPECIFIED",
        "modality": "ASSERTED",
        "scope": {"version": claimed_scope} if claimed_scope else {},
        "anchors": anchors,
    }


def evidence(evidence_id: str, source_id: str, kind: str, fragment: str) -> Dict[str, Any]:
    source_text = SOURCES[source_id]["text"]
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_kind": kind,
        "locator": SOURCES[source_id]["locator"],
        "source_text": source_text,
        "quote": anchor(source_text, fragment),
        "date": SOURCES[source_id]["published_at"],
        "derived_from": [],
        "cites": [],
    }


def build_claim(
    *,
    claim_id: str,
    text: str,
    subject: str,
    predicate: str,
    object_: str,
    readings: List[Dict[str, Any]],
    scope: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    claim_fragment = text.rstrip("。")
    payload: Dict[str, Any] = {
        "claim_ir": ir(
            claim_id, text, subject, predicate, object_,
            (scope or {}).get("claimed"),
        ),
        "evidence": [],
        "semantic_reviews": [],
    }
    for index, reading in enumerate(readings, start=1):
        evidence_id = f"E-{claim_id}-{index}"
        payload["evidence"].append(
            evidence(evidence_id, reading["source_id"], reading["kind"], reading["fragment"])
        )
        payload["semantic_reviews"].append(
            {
                "claim_id": claim_id,
                "evidence_id": evidence_id,
                "relation": reading["relation"],
                "reviewer_id": FIRST_PASS_REVIEWER,
                "claim_fragment": claim_fragment,
                "evidence_fragment": reading["fragment"],
                "missing_bridge": reading.get("missing_bridge", ""),
            }
        )
    review_file = REVIEW_DIR / f"{claim_id}.json"
    if review_file.exists():
        payload["adversarial_reviews"] = json.loads(review_file.read_text(encoding="utf-8"))
        payload["adversarial_policy"] = "required"
    if scope:
        payload["verified_scope"] = {
            "version": {
                "value": scope["value"],
                "evidence_ids": [f"E-{claim_id}-1"],
                "evidence_fragments": {f"E-{claim_id}-1": scope["fragment"]},
            }
        }
    return payload


PAPER = "research_paper"
DOCS = "official_documentation"


def entails(source_id: str, fragment: str, kind: str = PAPER) -> Dict[str, Any]:
    return {"source_id": source_id, "kind": kind, "fragment": fragment, "relation": "ENTAILS"}


def contradicts(source_id: str, fragment: str, kind: str = PAPER) -> Dict[str, Any]:
    return {"source_id": source_id, "kind": kind, "fragment": fragment, "relation": "CONTRADICTS"}


CLAIMS: List[Dict[str, Any]] = [
    dict(
        claim_id="AI-COT-001",
        text="对任意大模型，加一句「Let's think step by step」都能显著提升算术与符号推理的零样本准确率。",
        subject="加一句「Let's think step by step」",
        predicate="都能显著提升",
        object_="算术与符号推理的零样本准确率",
        readings=[entails("PAPER-COT-ZEROSHOT",
            "significantly outperforms zero-shot LLM performances on diverse benchmark reasoning tasks")],
        scope={"claimed": "任意大模型",
               "value": "text-davinci-002 与 540B PaLM，2022 年测得",
               "fragment": "large InstructGPT model (text-davinci-002)"},
    ),
    dict(
        claim_id="AI-COT-002",
        text="思维链提示能普遍提升大模型在各类任务上的表现。",
        subject="思维链提示",
        predicate="能普遍提升",
        object_="大模型在各类任务上的表现",
        readings=[contradicts("PAPER-COT-METAANALYSIS",
            "CoT gives strong performance benefits primarily on tasks involving math or logic, with much smaller gains on other types of tasks")],
    ),
    dict(
        claim_id="AI-COT-003",
        text="思维链主要在数学与逻辑类任务上带来明显收益，在其他类型任务上收益小得多。",
        subject="思维链",
        predicate="主要在数学与逻辑类任务上带来明显收益",
        object_="在其他类型任务上收益小得多",
        readings=[entails("PAPER-COT-METAANALYSIS",
            "CoT gives strong performance benefits primarily on tasks involving math or logic, with much smaller gains on other types of tasks")],
    ),
    dict(
        claim_id="AI-COT-004",
        text="思维链带来的推理能力提升出现在足够大的语言模型上。",
        subject="思维链带来的推理能力提升",
        predicate="出现在",
        object_="足够大的语言模型上",
        readings=[entails("PAPER-COT-WEI",
            "such reasoning abilities emerge naturally in sufficiently large language models")],
    ),
    dict(
        claim_id="AI-CTX-001",
        text="大模型能够稳定利用超长上下文中任意位置的信息。",
        subject="大模型",
        predicate="能够稳定利用",
        object_="超长上下文中任意位置的信息",
        readings=[contradicts("PAPER-LOST-MIDDLE",
            "current language models do not robustly make use of information in long input contexts")],
    ),
    dict(
        claim_id="AI-CTX-002",
        text="相关信息出现在上下文开头或结尾时模型表现最好，出现在中间时明显下降。",
        subject="相关信息出现在上下文开头或结尾时模型表现最好",
        predicate="出现在中间时",
        object_="明显下降",
        readings=[entails("PAPER-LOST-MIDDLE",
            "performance is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle of long contexts")],
    ),
    dict(
        claim_id="AI-VOTE-001",
        text="对同一问题采样多条推理路径再取最一致的答案，能提升思维链在算术与常识推理基准上的表现。",
        subject="对同一问题采样多条推理路径再取最一致的答案",
        predicate="能提升",
        object_="思维链在算术与常识推理基准上的表现",
        readings=[entails("PAPER-SELF-CONSISTENCY",
            "self-consistency boosts the performance of chain-of-thought prompting with a striking margin on a range of popular arithmetic and commonsense reasoning benchmarks")],
    ),
    dict(
        claim_id="AI-SELF-001",
        text="对任意模型，让它对自己的输出给出反馈并迭代修改，产出都会优于一次成文。",
        subject="让它对自己的输出给出反馈并迭代修改",
        predicate="产出都会优于",
        object_="一次成文",
        readings=[entails("PAPER-SELF-REFINE",
            "outputs generated with Self-Refine are preferred by humans and automatic metrics over those generated with the same LLM using conventional one-step generation")],
        scope={"claimed": "任意模型",
               "value": "GPT-3.5、ChatGPT 与 GPT-4，7 类任务，2023 年测得",
               "fragment": "(GPT-3.5, ChatGPT, and GPT-4)"},
    ),
    dict(
        claim_id="AI-SELF-002",
        text="模型在没有外部反馈时能够自我纠正推理错误。",
        subject="模型",
        predicate="在没有外部反馈时能够",
        object_="自我纠正推理错误",
        readings=[contradicts("PAPER-NO-SELF-CORRECT",
            "LLMs struggle to self-correct their responses without external feedback, and at times, their performance even degrades after self-correction")],
    ),
    dict(
        claim_id="AI-SELF-003",
        text="让模型自己检查一遍并修改，总能得到更好的结果。",
        subject="让模型自己检查一遍并修改",
        predicate="总能得到",
        object_="更好的结果",
        readings=[
            entails("PAPER-SELF-REFINE", "improving by ~20% absolute on average in task performance"),
            contradicts("PAPER-NO-SELF-CORRECT",
                "their performance even degrades after self-correction"),
        ],
    ),
    dict(
        claim_id="AI-EMO-001",
        text="对任意模型，在提示词里加入情绪化表达都可以提升它的表现。",
        subject="在提示词里加入情绪化表达",
        predicate="都可以提升",
        object_="它的表现",
        readings=[entails("PAPER-EMOTION-PROMPT",
            "their performance can be improved with emotional prompts")],
        scope={"claimed": "任意模型",
               "value": "Flan-T5-Large、Vicuna、Llama 2、BLOOM、ChatGPT 与 GPT-4，45 项任务，2023 年测得",
               "fragment": "Flan-T5-Large, Vicuna, Llama 2, BLOOM, ChatGPT, and GPT-4"},
    ),
    dict(
        claim_id="AI-RAG-001",
        text="接上检索增强就能消除大模型的幻觉。",
        subject="接上检索增强",
        predicate="就能消除",
        object_="大模型的幻觉",
        readings=[contradicts("PAPER-CLASHEVAL",
            "LLMs are susceptible to adopting incorrect retrieved content, overriding their own correct prior knowledge over 60% of the time")],
    ),
    dict(
        claim_id="AI-RAG-002",
        text="检索到的内容出错时，模型有很高比例会跟着错，而不是坚持自己原本正确的答案。",
        subject="检索到的内容出错时",
        predicate="模型有很高比例会跟着错",
        object_="而不是坚持自己原本正确的答案",
        readings=[entails("PAPER-CLASHEVAL",
            "overriding their own correct prior knowledge over 60% of the time")],
    ),
    dict(
        claim_id="AI-CACHE-001",
        text="只要开启提示缓存就一定比不开更便宜。",
        subject="只要开启提示缓存",
        predicate="就一定比不开",
        object_="更便宜",
        readings=[contradicts("DOC-PROMPT-CACHING",
            "5-minute cache write tokens are 1.25 times the base input tokens price", DOCS)],
    ),
    dict(
        claim_id="AI-CACHE-002",
        text="命中缓存的读取按基础输入价格的十分之一计费。",
        subject="命中缓存的读取",
        predicate="按基础输入价格的十分之一",
        object_="计费",
        readings=[entails("DOC-PROMPT-CACHING",
            "Cache read tokens are 0.1 times the base input tokens price", DOCS)],
    ),
    dict(
        claim_id="AI-CACHE-003",
        text="任意长度的提示词都可以被缓存。",
        subject="任意长度的提示词",
        predicate="都可以",
        object_="被缓存",
        readings=[contradicts("DOC-PROMPT-CACHING",
            "the minimum cacheable prompt length is", DOCS)],
    ),
    dict(
        claim_id="AI-XML-001",
        text="用XML标签把提示词里不同类型的内容分开可以减少模型的误解。",
        subject="用XML标签把提示词里不同类型的内容分开",
        predicate="可以减少",
        object_="模型的误解",
        readings=[entails("DOC-PROMPTING-BEST-PRACTICES",
            "Wrapping each type of content in its own tag (for example, <instructions>, <context>, <input>) reduces misinterpretation", DOCS)],
    ),
]


def build_source_bundle() -> Dict[str, Any]:
    return {
        "bundle_version": "1.0",
        "topic": "提示工程、长上下文、RAG 与 Agent 领域被反复转述的说法",
        "question": "AI 圈流传最广的那些提示与检索技巧，哪些有论文或官方文档支持，哪些只是互相抄？",
        "language": "zh-CN",
        "source_boundary": (
            f"检索日为{CAPTURE_DATE}。来源为 9 篇 arXiv 论文的摘要原文与 2 页 Claude 平台官方文档，"
            "全部按逐字原文捕获，未做改写。只使用摘要与文档正文，未读全文，"
            "因此论文正文中可能存在的更细致条件不在本次核验范围内。"
        ),
        "sources": [
            {
                "source_id": source_id,
                "title": source["title"],
                "source_type": (
                    "OFFICIAL_DOCUMENTATION" if source_id.startswith("DOC-") else "RESEARCH"
                ),
                "medium": "DOCUMENT" if source_id.startswith("DOC-") else "PAPER",
                "locator": source["locator"],
                "captured_at": CAPTURE_DATE,
                "content": source["text"],
                **({"published_at": source["published_at"]} if source["published_at"] else {}),
            }
            for source_id, source in SOURCES.items()
        ],
    }


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


EXPLANATIONS = {
    "AI-COT-001": ("思维链", "零样本思维链论文报告了这一提升。", ["只在论文测试的模型与基准上验证过。"], ["2022 年的模型；换成今天的推理模型结论未必成立。"]),
    "AI-COT-002": ("思维链", "覆盖 100 多篇论文的元分析与「普遍提升」直接冲突。", [], ["元分析并不否定思维链有用，只否定它对各类任务普遍有用。"]),
    "AI-COT-003": ("思维链", "元分析给出的正是这个范围。", [], ["基于摘要中给出的结论，未读全文的分任务细节。"]),
    "AI-COT-004": ("思维链", "原始论文明确把这种能力的出现绑定在足够大的模型上。", [], ["「足够大」在论文里没有给出统一阈值。"]),
    "AI-CTX-001": ("长上下文", "长上下文论文与「任意位置都能稳定利用」直接冲突。", [], ["测的是多文档问答与键值检索两类任务。"]),
    "AI-CTX-002": ("长上下文", "论文给出的正是这个位置效应。", [], ["不同模型的下降幅度不同，论文包含明确长上下文模型。"]),
    "AI-VOTE-001": ("采样与投票", "自一致性论文报告了这个提升。", [], ["需要多次采样，成本相应上升。"]),
    "AI-SELF-001": ("自我修改", "Self-Refine 论文报告产出优于一次成文。", ["只在论文测试的模型与 7 类任务上验证过。"], ["评测由人类偏好与自动指标给出，任务范围含对话生成。"]),
    "AI-SELF-002": ("自我修改", "另一篇论文与「无外部反馈也能自我纠错」直接冲突。", [], ["该结论限定在推理任务与内在自我纠正。"]),
    "AI-SELF-003": ("自我修改", "两篇论文对同一说法给出相反证据，本工具不替读者选边。", [], ["两者范围并不完全重叠：一篇覆盖 7 类任务，一篇限定推理任务且不许外部反馈。差异本身就是答案的一部分。"]),
    "AI-EMO-001": ("情绪化提示", "EmotionPrompt 论文报告了这个提升。", ["只在论文列出的模型与 45 项任务上验证过。"], ["2023 年的模型；相对提升幅度按任务差异很大。"]),
    "AI-RAG-001": ("检索增强", "ClashEval 与「消除幻觉」直接冲突。", [], ["不否定 RAG 有用，只否定它能消除幻觉。"]),
    "AI-RAG-002": ("检索增强", "ClashEval 给出的正是这个比例。", [], ["在该论文构造的冲突数据集上测得。"]),
    "AI-CACHE-001": ("提示缓存", "官方定价与「一定更便宜」直接冲突：写入比基础输入更贵。", [], ["缓存要被复用足够次数才划算，用一次就是净亏。"]),
    "AI-CACHE-002": ("提示缓存", "官方文档给出这个倍率。", [], ["倍率会变，用前应重新核对官方页面。"]),
    "AI-CACHE-003": ("提示缓存", "官方文档规定了最小可缓存长度，与「任意长度」冲突。", [], ["不同模型的最小长度不同。"]),
    "AI-XML-001": ("提示结构", "官方提示工程文档直接给出这个建议。", [], ["这是 Claude 官方对自家模型的说明，不自动适用于其他厂商的模型。"]),
}


def main() -> int:
    bundle = build_source_bundle()
    validate_source_bundle(bundle, CASE_DIR)
    write_json(CASE_DIR / "source-bundle.json", bundle)

    claim_dir = CASE_DIR / "claims"
    certificate_dir = CASE_DIR / "certificates"
    claim_dir.mkdir(exist_ok=True)
    certificate_dir.mkdir(exist_ok=True)

    records = []
    tally: Dict[str, int] = {}
    before: Dict[str, int] = {}
    changed: List[tuple] = []
    for spec in CLAIMS:
        payload = build_claim(**spec)
        claim_id = spec["claim_id"]
        write_json(claim_dir / f"{claim_id}.json", payload)
        certificate = compile_claim(payload, locator_policy="required")
        first_pass = compile_claim(
            {k: v for k, v in payload.items()
             if k not in ("adversarial_reviews", "adversarial_policy")},
            locator_policy="required",
        )
        before[first_pass["admission"]] = before.get(first_pass["admission"], 0) + 1
        if first_pass["admission"] != certificate["admission"]:
            changed.append((claim_id, first_pass["admission"], certificate["admission"]))
        write_json(certificate_dir / f"{claim_id}.json", certificate)
        admission = certificate["admission"]
        tally[admission] = tally.get(admission, 0) + 1

        layer = {
            "ADMIT": "SUPPORTED_KNOWLEDGE",
            "ADMIT_SCOPED": "CONDITIONAL_KNOWLEDGE",
            "ADMIT_COMPONENTS_ONLY": "SUPPORTED_COMPONENT",
            "HOLD": "DISPUTED_OR_UNRESOLVED",
            "REJECT": "REJECTED",
        }[admission]
        topic, explanation, conditions, limitations = EXPLANATIONS[claim_id]
        records.append(
            {
                "record_id": f"DOC-{claim_id}",
                "topic": topic,
                "layer": layer,
                "text": certificate["canonical_claim"] or certificate["claim_text"],
                "explanation": explanation,
                "source_ids": [item["source_id"] for item in payload["evidence"]],
                "conditions": conditions,
                "limitations": limitations,
                "certificate_file": f"certificates/{claim_id}.json",
            }
        )

    plan = {
        "document_version": "1.0",
        "title": "AI 圈流行说法核验：哪些有证据，哪些只是互相抄",
        "question": bundle["question"],
        "language": "zh-CN",
        "source_boundary": bundle["source_boundary"],
        "sources": [
            {k: s[k] for k in ("source_id", "title", "source_type", "medium", "locator")}
            for s in bundle["sources"]
        ],
        "records": records,
        "open_questions": [
            "这些 2022–2024 年的结论，在 2026 年的推理模型上还成立吗？多数论文没有被重测。",
            "思维链、自一致性、情绪化提示的收益，在扣除额外 token 成本后是否仍然为正？",
            "自我修改在什么条件下有效、什么条件下有害？两篇论文的范围差异需要一个直接对照实验来解决。",
            "RAG 在检索内容正确时的收益，与检索出错时的损害，净值是多少？",
        ],
    }
    write_json(CASE_DIR / "knowledge-document.json", plan)
    (CASE_DIR / "RESULT.md").write_text(
        render_knowledge_document(plan, CASE_DIR), encoding="utf-8"
    )
    print("一个审阅者时:", dict(sorted(before.items())))
    print("加入第二审阅者后:", dict(sorted(tally.items())))
    for claim_id, was, now in changed:
        print(f"  {claim_id}: {was} -> {now}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
