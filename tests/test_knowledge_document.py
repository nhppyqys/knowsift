from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from knowledge_compiler import compile_claim  # noqa: E402
from knowledge_compiler.knowledge_document import (  # noqa: E402
    KnowledgeDocumentError,
    render_knowledge_document,
    validate_document_plan,
    validate_source_bundle,
)


def anchor(text: str, fragment: str) -> dict[str, object]:
    start = text.index(fragment)
    return {"text": fragment, "start": start, "end": start + len(fragment)}


def fact_payload() -> dict[str, object]:
    claim = "Widget supports signed exports."
    evidence_text = "The official record states: Widget supports signed exports."
    supported = "Widget supports signed exports"
    return {
        "claim_ir": {
            "claim_id": "DOC-FACT-1",
            "source_text": claim,
            "operator": "FACT",
            "subject": "Widget",
            "predicate": "supports",
            "object": "signed exports",
            "polarity": "POSITIVE",
            "quantifier": "UNSPECIFIED",
            "modality": "ASSERTED",
            "scope": {},
            "anchors": {
                "subject": anchor(claim, "Widget"),
                "predicate": anchor(claim, "supports"),
                "object": anchor(claim, "signed exports"),
            },
        },
        "evidence": [
            {
                "evidence_id": "E1",
                "source_id": "S1",
                "source_kind": "official_record",
                "source_text": evidence_text,
                "quote": anchor(evidence_text, supported),
                "derived_from": [],
                "cites": [],
            }
        ],
        "semantic_reviews": [
            {
                "claim_id": "DOC-FACT-1",
                "evidence_id": "E1",
                "relation": "ENTAILS",
                "claim_fragment": supported,
                "evidence_fragment": supported,
                "missing_bridge": "",
            }
        ],
    }


def observe_payload() -> dict[str, object]:
    claim = "讲师甲主张成年人不应该背单词。"
    evidence_text = "视频字幕：讲师甲主张成年人不应该背单词。"
    fragment = "讲师甲主张成年人不应该背单词"
    return {
        "claim_ir": {
            "claim_id": "DOC-OBSERVE-1",
            "source_text": claim,
            "operator": "OBSERVE",
            "subject": "讲师甲",
            "predicate": "主张",
            "object": "成年人不应该背单词",
            "polarity": "POSITIVE",
            "quantifier": "UNSPECIFIED",
            "modality": "ASSERTED",
            "scope": {},
            "anchors": {
                "subject": anchor(claim, "讲师甲"),
                "predicate": anchor(claim, "主张"),
                "object": anchor(claim, "成年人不应该背单词"),
            },
        },
        "evidence": [
            {
                "evidence_id": "E-VIDEO",
                "source_id": "VIDEO-A",
                "source_kind": "primary_source",
                "source_text": evidence_text,
                "quote": anchor(evidence_text, fragment),
                "derived_from": [],
                "cites": [],
            }
        ],
        "semantic_reviews": [
            {
                "claim_id": "DOC-OBSERVE-1",
                "evidence_id": "E-VIDEO",
                "relation": "ENTAILS",
                "claim_fragment": fragment,
                "evidence_fragment": fragment,
                "missing_bridge": "",
            }
        ],
    }


def component_payload() -> dict[str, object]:
    claim = "Widget supports signed exports and every legacy format."
    evidence_text = "The official record states: Widget supports signed exports."
    evidence_fragment = "Widget supports signed exports"
    return {
        "claim_ir": {
            "claim_id": "DOC-COMPONENT-1",
            "source_text": claim,
            "operator": "FACT",
            "subject": "Widget",
            "predicate": "supports",
            "object": "signed exports and every legacy format",
            "polarity": "POSITIVE",
            "quantifier": "UNSPECIFIED",
            "modality": "ASSERTED",
            "scope": {},
            "anchors": {
                "subject": anchor(claim, "Widget"),
                "predicate": anchor(claim, "supports"),
                "object": anchor(claim, "signed exports and every legacy format"),
            },
        },
        "evidence": [
            {
                "evidence_id": "E1",
                "source_id": "S1",
                "source_kind": "official_record",
                "source_text": evidence_text,
                "quote": anchor(evidence_text, evidence_fragment),
                "derived_from": [],
                "cites": [],
            }
        ],
        "semantic_reviews": [
            {
                "claim_id": "DOC-COMPONENT-1",
                "evidence_id": "E1",
                "relation": "PARTIAL",
                "claim_fragment": "Widget supports signed exports and every legacy format",
                "evidence_fragment": evidence_fragment,
                "missing_bridge": "the evidence does not mention legacy formats",
            }
        ],
        "supported_components": [
            {
                "component_id": "DOC-COMPONENT-1-A",
                "text": "Widget supports signed exports",
                "claim_fragment": "signed exports",
                "evidence_ids": ["E1"],
            }
        ],
    }


class KnowledgeDocumentTests(unittest.TestCase):
    def test_source_bundle_accepts_mixed_media_and_roles(self) -> None:
        payload = {
            "bundle_version": "1.0",
            "topic": "成年人学习英语",
            "question": "现有材料支持哪些学习方法？",
            "source_boundary": "一份研究摘要和一个视频字幕",
            "sources": [
                {
                    "source_id": "PAPER-1",
                    "title": "研究摘要",
                    "source_type": "RESEARCH",
                    "medium": "PAPER",
                    "locator": "demo://paper-1",
                    "content": "研究摘要内容。",
                },
                {
                    "source_id": "VIDEO-1",
                    "title": "讲师视频",
                    "source_type": "OPINION",
                    "medium": "VIDEO",
                    "locator": "demo://video-1",
                    "content": "视频字幕内容。",
                },
            ],
        }
        normalized = validate_source_bundle(payload, Path.cwd())
        self.assertEqual(len(normalized["sources"]), 2)

    def test_source_bundle_rejects_duplicate_ids(self) -> None:
        payload = {
            "bundle_version": "1.0",
            "topic": "T",
            "question": "Q",
            "source_boundary": "B",
            "sources": [
                {
                    "source_id": "S1",
                    "title": "One",
                    "source_type": "RESEARCH",
                    "medium": "PAPER",
                    "locator": "demo://one",
                    "content": "One",
                },
                {
                    "source_id": "S1",
                    "title": "Two",
                    "source_type": "OPINION",
                    "medium": "VIDEO",
                    "locator": "demo://two",
                    "content": "Two",
                },
            ],
        }
        with self.assertRaises(KnowledgeDocumentError):
            validate_source_bundle(payload, Path.cwd())

    def _base_plan(self, certificate_file: str, certificate: dict[str, object]) -> dict[str, object]:
        source_id = certificate["evidence_references"][0]["source_id"]
        return {
            "document_version": "1.0",
            "title": "示例知识文档",
            "question": "哪些内容可以保留？",
            "source_boundary": "仅限示例来源",
            "sources": [
                {
                    "source_id": source_id,
                    "title": "示例来源",
                    "source_type": "PRIMARY_EVIDENCE",
                    "medium": "DOCUMENT",
                    "locator": "demo://source",
                }
            ],
            "records": [],
            "open_questions": ["还需要哪些独立证据？"],
        }

    def test_supported_knowledge_renders_only_exact_canonical_claim(self) -> None:
        certificate = compile_claim(fact_payload())
        self.assertEqual(certificate["admission"], "ADMIT")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "fact.json").write_text(json.dumps(certificate), encoding="utf-8")
            plan = self._base_plan("fact.json", certificate)
            plan["records"] = [
                {
                    "record_id": "R1",
                    "topic": "产品能力",
                    "layer": "SUPPORTED_KNOWLEDGE",
                    "text": certificate["canonical_claim"],
                    "explanation": "正式记录直接支持这条说法。",
                    "source_ids": ["S1"],
                    "certificate_file": "fact.json",
                }
            ]
            rendered = render_knowledge_document(plan, root)
            self.assertIn("有证据支持的知识", rendered)
            self.assertIn(certificate["canonical_claim"], rendered)

            plan["records"][0]["text"] = "Widget supports everything."
            with self.assertRaises(KnowledgeDocumentError):
                validate_document_plan(plan, root)

    def test_hold_cannot_enter_supported_knowledge(self) -> None:
        payload = fact_payload()
        payload["semantic_reviews"][0]["relation"] = "AMBIGUOUS"
        payload["semantic_reviews"][0]["missing_bridge"] = "support is unclear"
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "hold.json").write_text(json.dumps(certificate), encoding="utf-8")
            plan = self._base_plan("hold.json", certificate)
            plan["records"] = [
                {
                    "record_id": "R1",
                    "topic": "产品能力",
                    "layer": "SUPPORTED_KNOWLEDGE",
                    "text": "Widget supports signed exports.",
                    "explanation": "不应该通过。",
                    "source_ids": ["S1"],
                    "certificate_file": "hold.json",
                }
            ]
            with self.assertRaises(KnowledgeDocumentError):
                validate_document_plan(plan, root)

            plan["records"][0]["layer"] = "DISPUTED_OR_UNRESOLVED"
            validate_document_plan(plan, root)
            plan["records"][0]["text"] = "An unrelated disputed claim."
            with self.assertRaises(KnowledgeDocumentError):
                validate_document_plan(plan, root)

    def test_component_layer_rejects_complete_claim_leak(self) -> None:
        certificate = compile_claim(component_payload())
        self.assertEqual(certificate["admission"], "ADMIT_COMPONENTS_ONLY")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "component.json").write_text(json.dumps(certificate), encoding="utf-8")
            plan = self._base_plan("component.json", certificate)
            plan["records"] = [
                {
                    "record_id": "R1",
                    "topic": "产品能力",
                    "layer": "SUPPORTED_COMPONENT",
                    "text": "Widget supports signed exports",
                    "component_id": "DOC-COMPONENT-1-A",
                    "explanation": "证据只支持这个部分。",
                    "source_ids": ["S1"],
                    "certificate_file": "component.json",
                }
            ]
            validate_document_plan(plan, root)
            plan["records"][0]["text"] = "Widget supports signed exports and every legacy format"
            with self.assertRaises(KnowledgeDocumentError):
                validate_document_plan(plan, root)

    def test_viewpoint_requires_observe_and_viewpoint_source_role(self) -> None:
        certificate = compile_claim(observe_payload())
        self.assertEqual(certificate["admission"], "ADMIT")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "observe.json").write_text(json.dumps(certificate), encoding="utf-8")
            plan = self._base_plan("observe.json", certificate)
            plan["sources"][0].update(
                {"source_id": "VIDEO-A", "source_type": "OPINION", "medium": "VIDEO"}
            )
            plan["records"] = [
                {
                    "record_id": "R1",
                    "topic": "词汇学习",
                    "layer": "PRACTICE_OR_VIEWPOINT",
                    "text": certificate["canonical_claim"],
                    "explanation": "这里只确认讲师表达了该观点。",
                    "source_ids": ["VIDEO-A"],
                    "certificate_file": "observe.json",
                }
            ]
            validate_document_plan(plan, root)
            plan["sources"][0]["source_type"] = "RESEARCH"
            with self.assertRaises(KnowledgeDocumentError):
                validate_document_plan(plan, root)

    def test_certificate_path_cannot_escape_plan_directory(self) -> None:
        certificate = compile_claim(fact_payload())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = self._base_plan("../outside.json", certificate)
            plan["records"] = [
                {
                    "record_id": "R1",
                    "topic": "产品能力",
                    "layer": "SUPPORTED_KNOWLEDGE",
                    "text": certificate["canonical_claim"],
                    "explanation": "路径必须保持在文档目录内。",
                    "source_ids": ["S1"],
                    "certificate_file": "../outside.json",
                }
            ]
            with self.assertRaises(KnowledgeDocumentError):
                validate_document_plan(plan, root)

    def test_shipped_learning_demo_preserves_layer_boundaries(self) -> None:
        demo = SKILL_ROOT / "examples" / "learning-english"
        plan = json.loads((demo / "knowledge-document.json").read_text(encoding="utf-8"))
        normalized = validate_document_plan(plan, demo)
        counts = {
            layer: sum(record["layer"] == layer for record in normalized["records"])
            for layer in {
                "SUPPORTED_KNOWLEDGE",
                "PRACTICE_OR_VIEWPOINT",
                "DISPUTED_OR_UNRESOLVED",
            }
        }
        self.assertEqual(
            counts,
            {
                "SUPPORTED_KNOWLEDGE": 1,
                "PRACTICE_OR_VIEWPOINT": 3,
                "DISPUTED_OR_UNRESOLVED": 2,
            },
        )
        rendered = render_knowledge_document(plan, demo)
        self.assertEqual(rendered, (demo / "RESULT.md").read_text(encoding="utf-8"))

    def test_short_drama_benchmark_preserves_audited_boundaries(self) -> None:
        demo = SKILL_ROOT / "examples" / "short-drama-benchmark"
        bundle = json.loads((demo / "source-bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(len(validate_source_bundle(bundle, demo)["sources"]), 17)

        plan = json.loads((demo / "knowledge-document.json").read_text(encoding="utf-8"))
        normalized = validate_document_plan(plan, demo)
        counts = {
            layer: sum(record["layer"] == layer for record in normalized["records"])
            for layer in {
                "SUPPORTED_KNOWLEDGE",
                "PRACTICE_OR_VIEWPOINT",
                "DISPUTED_OR_UNRESOLVED",
                "REJECTED",
            }
        }
        self.assertEqual(
            counts,
            {
                "SUPPORTED_KNOWLEDGE": 17,
                "PRACTICE_OR_VIEWPOINT": 5,
                "DISPUTED_OR_UNRESOLVED": 3,
                "REJECTED": 2,
            },
        )
        self.assertEqual(len(list((demo / "certificates").glob("*.json"))), 27)
        rendered = render_knowledge_document(plan, demo)
        self.assertEqual(rendered, (demo / "RESULT.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
