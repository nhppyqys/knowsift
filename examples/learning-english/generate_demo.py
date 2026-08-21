#!/usr/bin/env python3
"""Generate the complete, fictional learning-English knowledge-document demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


EXAMPLE_DIR = Path(__file__).resolve().parent
SKILL_ROOT = EXAMPLE_DIR.parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from knowledge_compiler import compile_claim  # noqa: E402
from knowledge_compiler.knowledge_document import (  # noqa: E402
    render_knowledge_document,
    validate_source_bundle,
)


def anchor(text: str, fragment: str) -> Dict[str, Any]:
    start = text.index(fragment)
    return {"text": fragment, "start": start, "end": start + len(fragment)}


def claim_ir(
    claim_id: str,
    text: str,
    operator: str,
    subject: str,
    predicate: str,
    object_: str,
) -> Dict[str, Any]:
    return {
        "claim_id": claim_id,
        "source_text": text,
        "operator": operator,
        "subject": subject,
        "predicate": predicate,
        "object": object_,
        "polarity": "POSITIVE",
        "quantifier": "UNSPECIFIED",
        "modality": "ASSERTED",
        "scope": {},
        "anchors": {
            "subject": anchor(text, subject),
            "predicate": anchor(text, predicate),
            "object": anchor(text, object_),
        },
    }


def evidence(
    evidence_id: str,
    source_id: str,
    source_kind: str,
    source_text: str,
    fragment: str,
) -> Dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_kind": source_kind,
        "source_text": source_text,
        "quote": anchor(source_text, fragment),
        "derived_from": [],
        "cites": [],
    }


def review(
    claim_id: str,
    evidence_id: str,
    relation: str,
    claim_fragment: str,
    evidence_fragment: str,
    missing_bridge: str = "",
) -> Dict[str, str]:
    return {
        "claim_id": claim_id,
        "evidence_id": evidence_id,
        "relation": relation,
        "claim_fragment": claim_fragment,
        "evidence_fragment": evidence_fragment,
        "missing_bridge": missing_bridge,
    }


def build_source_bundle() -> Dict[str, Any]:
    return {
        "bundle_version": "1.0",
        "topic": "成年人如何学习英语",
        "question": "这些材料真正支持哪些学习结论？哪些只是观点、经历或营销承诺？",
        "language": "zh-CN",
        "source_boundary": (
            "演示用的 1 份研究摘要、3 段视频字幕和 1 个课程销售页。"
            "全部来源均为虚构样本，只用于展示过滤流程，不构成真实学习建议。"
        ),
        "sources": [
            {
                "source_id": "PAPER-1",
                "title": "分散学习与集中学习：演示研究摘要",
                "source_type": "RESEARCH",
                "medium": "PAPER",
                "locator": "demo://paper-1",
                "content": (
                    "示例研究摘要：在本综述纳入的词汇记忆任务中，分散安排复习的"
                    "延迟测试成绩高于一次性集中复习。摘要没有比较口语能力，也没有"
                    "证明这一结果适用于所有年龄、水平和学习目标。"
                ),
            },
            {
                "source_id": "VIDEO-A",
                "title": "讲师甲：不要背单词",
                "source_type": "OPINION",
                "medium": "VIDEO",
                "locator": "demo://video-a#t=03:12",
                "content": "视频字幕：讲师甲主张成年人绝对不应该背单词。",
            },
            {
                "source_id": "VIDEO-B",
                "title": "讲师乙：基础阶段仍要记词汇",
                "source_type": "PRACTITIONER_EXPERIENCE",
                "medium": "VIDEO",
                "locator": "demo://video-b#t=05:40",
                "content": "视频字幕：讲师乙主张基础词汇不足时仍需要系统记忆单词。",
            },
            {
                "source_id": "VIDEO-C",
                "title": "学习者丙的三个月经历",
                "source_type": "ANECDOTE",
                "medium": "VIDEO",
                "locator": "demo://video-c#t=00:48",
                "content": "视频字幕：学习者丙自述自己在三个月内从零基础达到流利。",
            },
            {
                "source_id": "SALES-1",
                "title": "三十天母语水平课程销售页",
                "source_type": "MARKETING",
                "medium": "ARTICLE",
                "locator": "demo://sales-1",
                "content": "销售页宣称：任何成年人每天学习十分钟都能在三十天达到母语水平。",
            },
        ],
    }


def build_claims(bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
    texts = {source["source_id"]: source["content"] for source in bundle["sources"]}

    research_claim = "在本综述纳入的词汇记忆任务中，分散安排复习的延迟测试成绩高于一次性集中复习。"
    research_fragment = research_claim.rstrip("。")
    research_scope = "本综述纳入的词汇记忆任务"
    research_ir = claim_ir(
        "LEARN-001",
        research_claim,
        "FACT",
        "分散安排复习的延迟测试成绩",
        "高于",
        "一次性集中复习",
    )
    research_ir["scope"] = {"study": research_scope}
    research_ir["anchors"]["scope"] = anchor(research_claim, research_scope)
    research_evidence = evidence(
        "E-PAPER-1",
        "PAPER-1",
        "peer_reviewed_study",
        texts["PAPER-1"],
        research_fragment,
    )
    research_evidence["scope"] = {"study": research_scope}
    research = {
        "claim_ir": research_ir,
        "evidence": [research_evidence],
        "semantic_reviews": [
            review(
                "LEARN-001",
                "E-PAPER-1",
                "ENTAILS",
                research_fragment,
                research_fragment,
            )
        ],
        "verified_scope": {
            "study": {
                "value": research_scope,
                "evidence_ids": ["E-PAPER-1"],
                "evidence_fragments": {"E-PAPER-1": research_scope},
            }
        },
    }

    observe_specs = [
        (
            "LEARN-002",
            "VIDEO-A",
            "讲师甲主张成年人绝对不应该背单词。",
            "讲师甲",
            "主张",
            "成年人绝对不应该背单词",
        ),
        (
            "LEARN-003",
            "VIDEO-B",
            "讲师乙主张基础词汇不足时仍需要系统记忆单词。",
            "讲师乙",
            "主张",
            "基础词汇不足时仍需要系统记忆单词",
        ),
        (
            "LEARN-004",
            "VIDEO-C",
            "学习者丙自述自己在三个月内从零基础达到流利。",
            "学习者丙",
            "自述",
            "自己在三个月内从零基础达到流利",
        ),
    ]
    observations = []
    for index, (claim_id, source_id, text, subject, predicate, object_) in enumerate(
        observe_specs, start=1
    ):
        fragment = text.rstrip("。")
        evidence_id = f"E-VIDEO-{index}"
        observations.append(
            {
                "claim_ir": claim_ir(
                    claim_id, text, "OBSERVE", subject, predicate, object_
                ),
                "evidence": [
                    evidence(
                        evidence_id,
                        source_id,
                        "primary_source",
                        texts[source_id],
                        fragment,
                    )
                ],
                "semantic_reviews": [
                    review(claim_id, evidence_id, "ENTAILS", fragment, fragment)
                ],
            }
        )

    dispute_claim = "成年人绝对不应该背单词。"
    dispute_fragment = dispute_claim.rstrip("。")
    support_fragment = "成年人绝对不应该背单词"
    contradiction_fragment = "基础词汇不足时仍需要系统记忆单词"
    dispute = {
        "claim_ir": claim_ir(
            "LEARN-005",
            dispute_claim,
            "FACT",
            "成年人",
            "绝对不应该",
            "背单词",
        ),
        "evidence": [
            evidence(
                "E-DISPUTE-A",
                "VIDEO-A",
                "primary_source",
                texts["VIDEO-A"],
                support_fragment,
            ),
            evidence(
                "E-DISPUTE-B",
                "VIDEO-B",
                "primary_source",
                texts["VIDEO-B"],
                contradiction_fragment,
            ),
        ],
        "semantic_reviews": [
            review(
                "LEARN-005",
                "E-DISPUTE-A",
                "ENTAILS",
                dispute_fragment,
                support_fragment,
            ),
            review(
                "LEARN-005",
                "E-DISPUTE-B",
                "CONTRADICTS",
                dispute_fragment,
                contradiction_fragment,
                "讲师乙的建议与绝对化说法冲突",
            ),
        ],
    }

    marketing_claim = "任何成年人每天学习十分钟都能在三十天达到母语水平。"
    marketing_fragment = marketing_claim.rstrip("。")
    marketing = {
        "claim_ir": claim_ir(
            "LEARN-006",
            marketing_claim,
            "FACT",
            "任何成年人",
            "每天学习十分钟都能在三十天达到",
            "母语水平",
        ),
        "evidence": [
            evidence(
                "E-SALES-1",
                "SALES-1",
                "marketing_copy",
                texts["SALES-1"],
                marketing_fragment,
            )
        ],
        "semantic_reviews": [
            review(
                "LEARN-006",
                "E-SALES-1",
                "ENTAILS",
                marketing_fragment,
                marketing_fragment,
            )
        ],
    }

    return [research, *observations, dispute, marketing]


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    bundle = build_source_bundle()
    validate_source_bundle(bundle, EXAMPLE_DIR)
    write_json(EXAMPLE_DIR / "source-bundle.json", bundle)

    claim_dir = EXAMPLE_DIR / "claims"
    certificate_dir = EXAMPLE_DIR / "certificates"
    claim_dir.mkdir(exist_ok=True)
    certificate_dir.mkdir(exist_ok=True)

    certificates: Dict[str, Dict[str, Any]] = {}
    for payload in build_claims(bundle):
        claim_id = payload["claim_ir"]["claim_id"]
        write_json(claim_dir / f"{claim_id}.json", payload)
        certificate = compile_claim(payload)
        certificates[claim_id] = certificate
        write_json(certificate_dir / f"{claim_id}.json", certificate)

    plan_sources = [
        {
            key: source[key]
            for key in ("source_id", "title", "source_type", "medium", "locator")
        }
        for source in bundle["sources"]
    ]

    records = [
        {
            "record_id": "DOC-001",
            "topic": "复习安排",
            "layer": "SUPPORTED_KNOWLEDGE",
            "text": certificates["LEARN-001"]["canonical_claim"],
            "explanation": "研究摘要直接支持这个较窄的比较结论。",
            "source_ids": ["PAPER-1"],
            "conditions": ["仅限该综述纳入的词汇记忆任务与延迟测试。"],
            "limitations": ["不能外推为口语效果，也不能外推到所有学习者。"],
            "certificate_file": "certificates/LEARN-001.json",
        },
        {
            "record_id": "DOC-002",
            "topic": "背单词",
            "layer": "PRACTICE_OR_VIEWPOINT",
            "text": certificates["LEARN-002"]["canonical_claim"],
            "explanation": "证书只确认讲师甲说过这句话，不确认建议普遍正确。",
            "source_ids": ["VIDEO-A"],
            "conditions": [],
            "limitations": ["这是个人主张，不是世界事实。"],
            "certificate_file": "certificates/LEARN-002.json",
        },
        {
            "record_id": "DOC-003",
            "topic": "背单词",
            "layer": "PRACTICE_OR_VIEWPOINT",
            "text": certificates["LEARN-003"]["canonical_claim"],
            "explanation": "证书只确认讲师乙提出了带条件的实践建议。",
            "source_ids": ["VIDEO-B"],
            "conditions": ["讲师乙把建议限定在基础词汇不足的情况。"],
            "limitations": ["从业经验不能单独证明对所有学习者有效。"],
            "certificate_file": "certificates/LEARN-003.json",
        },
        {
            "record_id": "DOC-004",
            "topic": "学习结果",
            "layer": "PRACTICE_OR_VIEWPOINT",
            "text": certificates["LEARN-004"]["canonical_claim"],
            "explanation": "证书确认这是学习者丙的自述，而不是可复制的普遍结果。",
            "source_ids": ["VIDEO-C"],
            "conditions": [],
            "limitations": ["单一个人故事不能说明典型效果，也缺少独立验证。"],
            "certificate_file": "certificates/LEARN-004.json",
        },
        {
            "record_id": "DOC-005",
            "topic": "背单词",
            "layer": "DISPUTED_OR_UNRESOLVED",
            "text": "成年人绝对不应该背单词。",
            "explanation": "两段视频给出冲突主张，而且材料不足以裁定哪个适用于谁。",
            "source_ids": ["VIDEO-A", "VIDEO-B"],
            "conditions": [],
            "limitations": ["需要更强的研究证据和明确的人群、目标与基础条件。"],
            "certificate_file": "certificates/LEARN-005.json",
        },
        {
            "record_id": "DOC-006",
            "topic": "课程效果",
            "layer": "DISPUTED_OR_UNRESOLVED",
            "text": "任何成年人每天学习十分钟都能在三十天达到母语水平。",
            "explanation": "唯一依据是销售页重复自己的承诺，没有独立结果证据。",
            "source_ids": ["SALES-1"],
            "conditions": [],
            "limitations": ["人群、母语水平定义、测量方法和失败案例均未知。"],
            "certificate_file": "certificates/LEARN-006.json",
        },
    ]

    plan = {
        "document_version": "1.0",
        "title": "怎样学英语：一份经过过滤的材料地图（演示）",
        "question": bundle["question"],
        "language": "zh-CN",
        "source_boundary": bundle["source_boundary"],
        "sources": plan_sources,
        "records": records,
        "open_questions": [
            "对不同英语基础与学习目标，分散复习的效果是否相同？",
            "词汇记忆、阅读理解与口语表达需要怎样组合训练？",
            "视频中关于背单词的冲突建议，是否能由更高质量研究裁定？",
        ],
    }
    write_json(EXAMPLE_DIR / "knowledge-document.json", plan)
    (EXAMPLE_DIR / "RESULT.md").write_text(
        render_knowledge_document(plan, EXAMPLE_DIR), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
