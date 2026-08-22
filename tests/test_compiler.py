from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from knowledge_compiler import compile_claim  # noqa: E402
from knowledge_compiler.protocols import VALIDATORS  # noqa: E402
from knowledge_compiler.registry import load_json  # noqa: E402


def anchor(text: str, fragment: str) -> dict[str, object]:
    start = text.index(fragment)
    return {"text": fragment, "start": start, "end": start + len(fragment)}


def fact_payload() -> dict[str, object]:
    claim = "Widget supports signed exports."
    evidence_text = "The official record states: Widget supports signed exports."
    supported = "Widget supports signed exports"
    return {
        "claim_ir": {
            "claim_id": "FACT-1",
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
                "claim_id": "FACT-1",
                "evidence_id": "E1",
                "relation": "ENTAILS",
                "claim_fragment": supported,
                "evidence_fragment": supported,
                "missing_bridge": "",
            }
        ],
    }


def operator_payload(
    operator: str,
    claim: str,
    subject: str,
    predicate: str,
    obj: str,
    evidence_fragment: str,
    *,
    source_kind: str = "official_record",
) -> dict[str, object]:
    claim_fragment = claim.rstrip(".")
    evidence_text = evidence_fragment + "."
    anchors = {
        "subject": anchor(claim, subject),
        "predicate": anchor(claim, predicate),
        "object": anchor(claim, obj),
    }
    if operator in {"CAUSE", "PRESCRIBE", "THRESHOLD", "LEGAL_RULE"}:
        anchors["operator"] = anchor(claim, predicate)
    return {
        "claim_ir": {
            "claim_id": f"{operator}-1",
            "source_text": claim,
            "operator": operator,
            "subject": subject,
            "predicate": predicate,
            "object": obj,
            "polarity": "POSITIVE",
            "quantifier": "UNSPECIFIED",
            "modality": "ASSERTED",
            "scope": {},
            "anchors": anchors,
        },
        "evidence": [
            {
                "evidence_id": "E1",
                "source_id": "S1",
                "source_kind": source_kind,
                "source_text": evidence_text,
                "quote": anchor(evidence_text, evidence_fragment),
            }
        ],
        "semantic_reviews": [
            {
                "claim_id": f"{operator}-1",
                "evidence_id": "E1",
                "relation": "ENTAILS",
                "claim_fragment": claim_fragment,
                "evidence_fragment": evidence_fragment,
                "missing_bridge": "",
            }
        ],
    }


class AdmissionRegressionTests(unittest.TestCase):
    def test_valid_fact_admits(self) -> None:
        certificate = compile_claim(fact_payload())
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(certificate["unresolved"], [])

    def test_invalid_ir_never_admits(self) -> None:
        payload = fact_payload()
        del payload["claim_ir"]["anchors"]["subject"]
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIn("STRUCTURAL_OR_REFERENCE_VALIDATION_FAILED", certificate["decisive_reasons"])

    def test_broken_quote_never_admits(self) -> None:
        payload = fact_payload()
        payload["evidence"][0]["quote"]["start"] = 0
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")

    def test_forbidden_confidence_never_admits(self) -> None:
        payload = fact_payload()
        payload["semantic_reviews"][0]["confidence"] = 0.99
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertTrue(certificate["semantic_summary"]["errors"])

    def test_partial_support_never_full_admits(self) -> None:
        payload = fact_payload()
        payload["semantic_reviews"][0]["relation"] = "PARTIAL"
        payload["semantic_reviews"][0]["missing_bridge"] = "support is limited to signed exports"
        payload["supported_components"] = [
            {
                "component_id": "FACT-1-a",
                "text": "Widget supports signed exports",
                "claim_fragment": "signed exports",
                "evidence_ids": ["E1"],
            }
        ]
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT_COMPONENTS_ONLY")
        self.assertIsNone(certificate["canonical_claim"])
        self.assertIsNone(certificate["normalized_ir"])

    def test_appropriate_contradiction_rejects(self) -> None:
        payload = fact_payload()
        payload["semantic_reviews"][0]["relation"] = "CONTRADICTS"
        payload["semantic_reviews"][0]["missing_bridge"] = ""
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "REJECT")
        self.assertIsNone(certificate["canonical_claim"])
        self.assertIsNone(certificate["normalized_ir"])

    def test_unrelated_evidence_holds(self) -> None:
        payload = fact_payload()
        payload["semantic_reviews"][0]["relation"] = "UNRELATED"
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIsNone(certificate["canonical_claim"])
        self.assertIsNone(certificate["normalized_ir"])

    def test_insufficient_source_cannot_admit(self) -> None:
        payload = fact_payload()
        payload["evidence"][0]["source_kind"] = "marketing_copy"
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(certificate["source_authority"]["code"], "NO_APPROPRIATE_SOURCE")

    def test_unknown_source_class_holds(self) -> None:
        payload = fact_payload()
        payload["evidence"][0]["source_kind"] = "mystery_source"
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(certificate["source_authority"]["unclassified_evidence_ids"], ["E1"])

    def test_unknown_top_level_field_holds(self) -> None:
        payload = fact_payload()
        payload["confidence"] = 1
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")


class ScopeAndDomainTests(unittest.TestCase):
    def test_unsupported_universal_is_safely_narrowed(self) -> None:
        claim = "All widgets support signed exports."
        evidence_text = "In version 4.2, widgets support signed exports."
        payload = {
            "claim_ir": {
                "claim_id": "GEN-1",
                "source_text": claim,
                "operator": "FACT",
                "subject": "widgets",
                "predicate": "support",
                "object": "signed exports",
                "polarity": "POSITIVE",
                "quantifier": "ALL",
                "modality": "ASSERTED",
                "scope": {},
                "anchors": {
                    "subject": anchor(claim, "widgets"),
                    "predicate": anchor(claim, "support"),
                    "object": anchor(claim, "signed exports"),
                    "quantifier": anchor(claim, "All"),
                },
            },
            "evidence": [
                {
                    "evidence_id": "E1",
                    "source_id": "S1",
                    "source_kind": "official_record",
                    "source_text": evidence_text,
                    "quote": anchor(evidence_text, "widgets support signed exports"),
                    "scope": {"version": "4.2"},
                }
            ],
            "semantic_reviews": [
                {
                    "claim_id": "GEN-1",
                    "evidence_id": "E1",
                    "relation": "ENTAILS",
                    "claim_fragment": "widgets support signed exports",
                    "evidence_fragment": "widgets support signed exports",
                    "missing_bridge": "",
                }
            ],
            "verified_scope": {
                "version": {
                    "value": "4.2",
                    "evidence_ids": ["E1"],
                    "evidence_fragments": {"E1": "version 4.2"},
                }
            },
        }
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT_SCOPED")
        self.assertEqual(certificate["normalized_ir"]["quantifier"], "UNSPECIFIED")
        self.assertEqual(certificate["normalized_ir"]["scope"]["version"], "4.2")

    def test_universal_without_safe_scope_holds(self) -> None:
        payload = fact_payload()
        payload["claim_ir"]["source_text"] = "All widgets support signed exports."
        payload["claim_ir"]["subject"] = "widgets"
        payload["claim_ir"]["predicate"] = "support"
        payload["claim_ir"]["quantifier"] = "ALL"
        payload["claim_ir"]["anchors"] = {
            "subject": anchor(payload["claim_ir"]["source_text"], "widgets"),
            "predicate": anchor(payload["claim_ir"]["source_text"], "support"),
            "object": anchor(payload["claim_ir"]["source_text"], "signed exports"),
            "quantifier": anchor(payload["claim_ir"]["source_text"], "All"),
        }
        payload["semantic_reviews"][0]["claim_fragment"] = "widgets support signed exports"
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(certificate["protocol_results"]["GENERALIZATION"]["status"], "HOLD")

    def test_version_sensitive_claim_admits_when_versions_match(self) -> None:
        claim = "Widget 4.2 supports signed exports."
        evidence_text = "In version 4.2, Widget supports signed exports."
        payload = fact_payload()
        payload["domain"] = "SOFTWARE"
        payload["claim_ir"].update(
            {
                "source_text": claim,
                "subject": "Widget 4.2",
                "scope": {"version": "4.2"},
                "anchors": {
                    "subject": anchor(claim, "Widget 4.2"),
                    "predicate": anchor(claim, "supports"),
                    "object": anchor(claim, "signed exports"),
                    "scope": anchor(claim, "4.2"),
                },
            }
        )
        payload["evidence"][0].update(
            {
                "source_kind": "official_documentation",
                "source_text": evidence_text,
                "quote": anchor(evidence_text, "Widget supports signed exports"),
                "version": "4.2",
                "scope": {"version": "4.2"},
            }
        )
        payload["semantic_reviews"][0].update(
            {
                "claim_fragment": "Widget 4.2 supports signed exports",
                "evidence_fragment": "Widget supports signed exports",
            }
        )
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(certificate["protocol_results"]["VERSIONED_TECHNICAL_SPEC"]["status"], "PASS")

    def test_versioned_partial_support_can_admit_only_component(self) -> None:
        claim = "Widget 4.2 supports signed exports and all legacy formats."
        evidence_text = "In version 4.2, Widget supports signed exports."
        payload = {
            "claim_ir": {
                "claim_id": "VERSIONED-COMPONENT-1",
                "source_text": claim,
                "operator": "FACT",
                "subject": "Widget 4.2",
                "predicate": "supports",
                "object": "signed exports and all legacy formats",
                "polarity": "POSITIVE",
                "quantifier": "UNSPECIFIED",
                "modality": "ASSERTED",
                "scope": {"version": "4.2"},
                "anchors": {
                    "subject": anchor(claim, "Widget 4.2"),
                    "predicate": anchor(claim, "supports"),
                    "object": anchor(claim, "signed exports and all legacy formats"),
                    "scope": anchor(claim, "4.2"),
                },
            },
            "domain": "SOFTWARE",
            "claim_class": "API_BEHAVIOR",
            "evidence": [
                {
                    "evidence_id": "E1",
                    "source_id": "DOC-4.2",
                    "source_kind": "official_documentation",
                    "source_text": evidence_text,
                    "quote": anchor(evidence_text, "Widget supports signed exports"),
                    "version": "4.2",
                    "scope": {"version": "4.2"},
                }
            ],
            "semantic_reviews": [
                {
                    "claim_id": "VERSIONED-COMPONENT-1",
                    "evidence_id": "E1",
                    "relation": "PARTIAL",
                    "claim_fragment": "Widget 4.2 supports signed exports and all legacy formats",
                    "evidence_fragment": "Widget supports signed exports",
                    "missing_bridge": "the evidence does not mention legacy formats",
                }
            ],
            "verified_scope": {
                "version": {
                    "value": "4.2",
                    "evidence_ids": ["E1"],
                    "evidence_fragments": {"E1": "version 4.2"},
                }
            },
            "supported_components": [
                {
                    "component_id": "VERSIONED-COMPONENT-1-A",
                    "text": "Widget 4.2 supports signed exports",
                    "claim_fragment": "signed exports",
                    "evidence_ids": ["E1"],
                }
            ],
        }
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT_COMPONENTS_ONLY")
        self.assertEqual(
            certificate["protocol_results"]["VERSIONED_TECHNICAL_SPEC"]["status"], "PASS"
        )
        self.assertIsNone(certificate["canonical_claim"])

    def test_chinese_claim_renders_in_chinese(self) -> None:
        claim = "净澈A2空气净化器标称适用面积为40平方米。"
        evidence_text = "净澈A2说明书：本产品标称适用面积为40平方米。"
        payload = {
            "claim_ir": {
                "claim_id": "ZH-1",
                "source_text": claim,
                "operator": "FACT",
                "subject": "净澈A2空气净化器",
                "predicate": "标称适用面积为",
                "object": "40平方米",
                "polarity": "POSITIVE",
                "quantifier": "UNSPECIFIED",
                "modality": "ASSERTED",
                "scope": {"model": "净澈A2"},
                "anchors": {
                    "subject": anchor(claim, "净澈A2空气净化器"),
                    "predicate": anchor(claim, "标称适用面积为"),
                    "object": anchor(claim, "40平方米"),
                    "scope": anchor(claim, "净澈A2"),
                },
            },
            "evidence": [
                {
                    "evidence_id": "E1",
                    "source_id": "MANUAL-A2",
                    "source_kind": "official_documentation",
                    "source_text": evidence_text,
                    "quote": anchor(evidence_text, "本产品标称适用面积为40平方米"),
                    "scope": {"model": "净澈A2"},
                }
            ],
            "semantic_reviews": [
                {
                    "claim_id": "ZH-1",
                    "evidence_id": "E1",
                    "relation": "ENTAILS",
                    "claim_fragment": "净澈A2空气净化器标称适用面积为40平方米",
                    "evidence_fragment": "本产品标称适用面积为40平方米",
                    "missing_bridge": "",
                }
            ],
        }
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(
            certificate["canonical_claim"],
            "适用范围：型号：净澈A2。结论：净澈A2空气净化器标称适用面积为40平方米。",
        )

    def test_version_mismatch_holds(self) -> None:
        payload = fact_payload()
        claim = "Widget 4.2 supports signed exports."
        payload["domain"] = "SOFTWARE"
        payload["claim_ir"].update(
            {
                "source_text": claim,
                "subject": "Widget 4.2",
                "scope": {"version": "4.2"},
                "anchors": {
                    "subject": anchor(claim, "Widget 4.2"),
                    "predicate": anchor(claim, "supports"),
                    "object": anchor(claim, "signed exports"),
                    "scope": anchor(claim, "4.2"),
                },
            }
        )
        payload["evidence"][0]["source_kind"] = "official_documentation"
        payload["evidence"][0]["version"] = "5.0"
        payload["semantic_reviews"][0]["claim_fragment"] = "Widget 4.2 supports signed exports"
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(certificate["protocol_results"]["VERSIONED_TECHNICAL_SPEC"]["status"], "HOLD")


class SpecializedProtocolTests(unittest.TestCase):
    def test_incomplete_causal_claim_admits_only_components(self) -> None:
        claim = "Lowering ROI target causes GMV to increase."
        evidence_text = "ROI target was lowered and GMV increased afterward."
        payload = {
            "claim_ir": {
                "claim_id": "CAUSE-1",
                "source_text": claim,
                "operator": "CAUSE",
                "subject": "Lowering ROI target",
                "predicate": "causes",
                "object": "GMV to increase",
                "polarity": "POSITIVE",
                "quantifier": "UNSPECIFIED",
                "modality": "ASSERTED",
                "scope": {},
                "anchors": {
                    "subject": anchor(claim, "Lowering ROI target"),
                    "predicate": anchor(claim, "causes"),
                    "operator": anchor(claim, "causes"),
                    "object": anchor(claim, "GMV to increase"),
                },
            },
            "evidence": [
                {
                    "evidence_id": "E1",
                    "source_id": "S1",
                    "source_kind": "official_record",
                    "source_text": evidence_text,
                    "quote": anchor(evidence_text, evidence_text[:-1]),
                }
            ],
            "semantic_reviews": [
                {
                    "claim_id": "CAUSE-1",
                    "evidence_id": "E1",
                    "relation": "PARTIAL",
                    "claim_fragment": "Lowering ROI target causes GMV to increase",
                    "evidence_fragment": "ROI target was lowered and GMV increased afterward",
                    "missing_bridge": "causal identification",
                }
            ],
            "supported_components": [
                {
                    "component_id": "CAUSE-1-a",
                    "text": "GMV increased afterward",
                    "claim_fragment": "GMV to increase",
                    "evidence_ids": ["E1"],
                }
            ],
        }
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT_COMPONENTS_ONLY")

    def test_complete_causal_design_admits(self) -> None:
        claim = "Treatment A causes outcome Y."
        evidence_text = "Randomized treatment A reduced outcome Y compared with control."
        evidence_fragment = "Randomized treatment A reduced outcome Y compared with control"
        assumptions = {
            name: {
                "method": f"audited {name}",
                "evidence_id": "E1",
                "evidence_fragment": evidence_fragment,
            }
            for name in ("allocation_integrity", "noncompliance_impact", "outcome_measure_validity")
        }
        payload = {
            "claim_ir": {
                "claim_id": "CAUSE-2",
                "source_text": claim,
                "operator": "CAUSE",
                "subject": "Treatment A",
                "predicate": "causes",
                "object": "outcome Y",
                "polarity": "POSITIVE",
                "quantifier": "UNSPECIFIED",
                "modality": "ASSERTED",
                "scope": {},
                "anchors": {
                    "subject": anchor(claim, "Treatment A"),
                    "predicate": anchor(claim, "causes"),
                    "operator": anchor(claim, "causes"),
                    "object": anchor(claim, "outcome Y"),
                },
            },
            "evidence": [
                {
                    "evidence_id": "E1",
                    "source_id": "S1",
                    "source_kind": "official_record",
                    "source_text": evidence_text,
                    "quote": anchor(evidence_text, evidence_fragment),
                }
            ],
            "semantic_reviews": [
                {
                    "claim_id": "CAUSE-2",
                    "evidence_id": "E1",
                    "relation": "ENTAILS",
                    "claim_fragment": "Treatment A causes outcome Y",
                    "evidence_fragment": evidence_fragment,
                    "missing_bridge": "",
                }
            ],
            "protocol_inputs": {
                "causal_inference": {
                    "design_type": "RCT",
                    "record": {
                        "random_assignment_record": "allocation log",
                        "treatment_definition": "Treatment A",
                        "outcome_definition": "Outcome Y",
                        "attrition_reported": "2%",
                    },
                    "assumptions": assumptions,
                }
            },
        }
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT")

    def test_statistical_claim_requires_statistical_record(self) -> None:
        claim = "Group A has higher scores than Group B."
        evidence_text = "Group A had higher scores than Group B in the registered analysis."
        payload = {
            "claim_ir": {
                "claim_id": "STAT-1",
                "source_text": claim,
                "operator": "COMPARE",
                "subject": "Group A",
                "predicate": "has higher scores than",
                "object": "Group B",
                "polarity": "POSITIVE",
                "quantifier": "UNSPECIFIED",
                "modality": "ASSERTED",
                "scope": {},
                "anchors": {
                    "subject": anchor(claim, "Group A"),
                    "predicate": anchor(claim, "has higher scores than"),
                    "object": anchor(claim, "Group B"),
                },
            },
            "evidence": [
                {
                    "evidence_id": "E1",
                    "source_id": "S1",
                    "source_kind": "official_record",
                    "source_text": evidence_text,
                    "quote": anchor(evidence_text, "Group A had higher scores than Group B"),
                }
            ],
            "semantic_reviews": [
                {
                    "claim_id": "STAT-1",
                    "evidence_id": "E1",
                    "relation": "ENTAILS",
                    "claim_fragment": "Group A has higher scores than Group B",
                    "evidence_fragment": "Group A had higher scores than Group B",
                    "missing_bridge": "",
                }
            ],
        }
        self.assertEqual(compile_claim(payload)["admission"], "HOLD")
        payload["protocol_inputs"] = {
            "statistical_inference": {
                "effect_measure": "mean_difference",
                "estimate": 2.1,
                "standard_error": 0.4,
                "comparison": "Group A minus Group B",
                "evidence_ids": ["E1"],
            }
        }
        self.assertEqual(compile_claim(payload)["admission"], "ADMIT")

    def test_meta_analysis_recomputes(self) -> None:
        payload = fact_payload()
        second_text = "Study two reports a compatible signed-export effect."
        payload["evidence"].append(
            {
                "evidence_id": "E2",
                "source_id": "S2",
                "source_kind": "official_record",
                "source_text": second_text,
                "quote": anchor(second_text, "compatible signed-export effect"),
            }
        )
        payload["protocol_inputs"] = {
            "evidence_synthesis": {
                "synthesis_type": "random_effects_meta_analysis",
                "search_strategy": "registered database search",
                "inclusion_criteria": "registered criteria",
                "study_records": [
                    {"study_id": "STUDY-1", "evidence_id": "E1", "effect_estimate": 0.1, "variance": 0.01},
                    {"study_id": "STUDY-2", "evidence_id": "E2", "effect_estimate": 0.2, "variance": 0.02},
                ],
                "effect_measure": "standardized_mean_difference",
                "compatibility_method": "same estimator and direction",
                "dependence_method": "one independent estimate per study",
                "model_choice_rationale": "between-study variation is plausible",
            }
        }
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(certificate["protocol_results"]["EVIDENCE_SYNTHESIS"]["status"], "PASS")
        self.assertEqual(
            certificate["protocol_results"]["EVIDENCE_SYNTHESIS"]["derived"]["model"],
            "random_effects_DL",
        )


class RemainingProtocolTests(unittest.TestCase):
    def test_formal_proof_requires_passing_artifact(self) -> None:
        payload = operator_payload(
            "FORMAL",
            "The theorem follows from axioms A and B.",
            "The theorem",
            "follows from",
            "axioms A and B",
            "The theorem follows from axioms A and B",
        )
        payload["protocol_inputs"] = {
            "formal_proof": {
                "method": "proof checker 2.0",
                "artifact_reference": "proof-17",
                "result": "FAIL",
                "evidence_ids": ["E1"],
            }
        }
        self.assertEqual(compile_claim(payload)["admission"], "REJECT")
        payload["protocol_inputs"]["formal_proof"]["result"] = "PASS"
        self.assertEqual(compile_claim(payload)["admission"], "ADMIT")

    def test_predictive_validation_requires_out_of_sample_record(self) -> None:
        payload = operator_payload(
            "PREDICT",
            "Model A predicts outcome Y.",
            "Model A",
            "predicts",
            "outcome Y",
            "Model A predicts outcome Y",
        )
        payload["protocol_inputs"] = {
            "predictive_validation": {
                "metric": "AUROC",
                "baseline": "logistic baseline",
                "evaluation_scope": "held-out 2026 cohort",
                "out_of_sample": False,
                "evidence_ids": ["E1"],
            }
        }
        self.assertEqual(compile_claim(payload)["admission"], "HOLD")
        payload["protocol_inputs"]["predictive_validation"]["out_of_sample"] = True
        self.assertEqual(compile_claim(payload)["admission"], "ADMIT")

    def test_prescriptive_decision_tracks_values_and_tradeoffs(self) -> None:
        payload = operator_payload(
            "PRESCRIBE",
            "Team should adopt option A.",
            "Team",
            "adopt",
            "option A",
            "Team should adopt option A",
        )
        payload["claim_ir"]["modality"] = "SHOULD"
        payload["claim_ir"]["anchors"]["modality"] = anchor(
            payload["claim_ir"]["source_text"], "should"
        )
        payload["protocol_inputs"] = {
            "prescriptive_decision": {
                "objective": "reduce latency",
                "alternatives": ["option A", "option B"],
                "constraints": ["budget"],
                "tradeoffs": ["speed versus cost"],
                "evidence_ids": ["E1"],
            }
        }
        self.assertEqual(compile_claim(payload)["admission"], "ADMIT")

    def test_conditional_phenomenon_attaches_literal_conditions(self) -> None:
        claim = "Compound X changes phase above 80 C."
        evidence_text = "Observed compound X changes phase above 80 C."
        payload = operator_payload(
            "THRESHOLD",
            claim,
            "Compound X",
            "changes phase above",
            "80 C",
            "compound X changes phase above 80 C",
        )
        payload["claim_ir"]["anchors"]["operator"] = anchor(claim, "above")
        payload["evidence"][0]["source_text"] = evidence_text
        payload["evidence"][0]["quote"] = anchor(
            evidence_text, "compound X changes phase above 80 C"
        )
        payload["semantic_reviews"][0]["evidence_fragment"] = "compound X changes phase above 80 C"
        payload["verified_conditions"] = {
            "temperature": {
                "value": "above 80 C",
                "evidence_ids": ["E1"],
                "evidence_fragments": {"E1": "above 80 C"},
            }
        }
        payload["protocol_inputs"] = {
            "conditional_phenomenon": {
                "operational_outcome": "phase change",
                "comparison_baseline": "80 C or below",
                "evidence_ids": ["E1"],
            }
        }
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT_SCOPED")
        self.assertEqual(
            certificate["normalized_ir"]["scope"]["conditions"]["temperature"],
            "above 80 C",
        )

    def test_history_domain_characterizes_sources(self) -> None:
        payload = fact_payload()
        payload["domain"] = "HISTORY"
        payload["evidence"][0]["source_kind"] = "peer_reviewed_history"
        payload["protocol_inputs"] = {
            "historical_source_criticism": {
                "event_year": 221,
                "source_records": [
                    {"evidence_id": "E1", "source_year": 230, "document_type": "chronicle"}
                ],
            }
        }
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT")
        derived = certificate["protocol_results"]["HISTORICAL_SOURCE_CRITICISM"]["derived"]
        self.assertEqual(derived["sources"][0]["temporal_distance_years"], 9)

    def test_practitioner_heuristic_is_always_scoped(self) -> None:
        payload = fact_payload()
        payload["protocol_inputs"] = {
            "practitioner_heuristic": {
                "context": "one production account in Q2",
                "limitations": ["not randomized"],
                "evidence_ids": ["E1"],
            }
        }
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT_SCOPED")
        self.assertEqual(
            certificate["normalized_ir"]["scope"]["practice_context"],
            "one production account in Q2",
        )

    def test_legal_exceptions_narrow_absolute_rule(self) -> None:
        claim = "Hearsay is always inadmissible in federal court."
        evidence_text = (
            "Rule 802 states hearsay is inadmissible in federal court, "
            "except as provided by the rules."
        )
        payload = operator_payload(
            "LEGAL_RULE",
            claim,
            "Hearsay",
            "is always inadmissible in",
            "federal court",
            "hearsay is inadmissible in federal court",
            source_kind="official_rule",
        )
        payload["domain"] = "LAW"
        payload["claim_ir"]["quantifier"] = "ALL"
        payload["claim_ir"]["scope"] = {"geography": "federal court"}
        payload["claim_ir"]["anchors"]["quantifier"] = anchor(claim, "always")
        payload["claim_ir"]["anchors"]["scope"] = anchor(claim, "federal court")
        payload["evidence"][0].update(
            {
                "source_text": evidence_text,
                "quote": anchor(evidence_text, "hearsay is inadmissible in federal court"),
                "version": "2026",
                "scope": {"geography": "federal court"},
            }
        )
        payload["semantic_reviews"][0].update(
            {
                "claim_fragment": "Hearsay is always inadmissible in federal court",
                "evidence_fragment": "hearsay is inadmissible in federal court",
            }
        )
        payload["verified_scope"] = {
            "geography": {
                "value": "federal court",
                "evidence_ids": ["E1"],
                "evidence_fragments": {"E1": "federal court"},
            }
        }
        exception_text = "except as provided by the rules"
        payload["verified_exceptions"] = [
            {
                "text": exception_text,
                "evidence_id": "E1",
                "quote": anchor(evidence_text, exception_text),
            }
        ]
        payload["protocol_inputs"] = {
            "legal_authority": {
                "jurisdiction": "U.S. federal courts",
                "authority_type": "official_rule",
                "citation": "Rule 802",
                "effective_date_or_version": "2026",
                "operative_evidence_id": "E1",
            },
            "versioned_technical_spec": {"version": "2026", "evidence_ids": ["E1"]},
        }
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT_SCOPED")
        self.assertIn("ADD_VERIFIED_LEGAL_EXCEPTIONS", certificate["transformations"])

    def test_traceable_generalization_can_pass(self) -> None:
        payload = fact_payload()
        claim = "All widgets support signed exports."
        payload["claim_ir"].update(
            {
                "source_text": claim,
                "subject": "widgets",
                "predicate": "support",
                "quantifier": "ALL",
                "anchors": {
                    "subject": anchor(claim, "widgets"),
                    "predicate": anchor(claim, "support"),
                    "object": anchor(claim, "signed exports"),
                    "quantifier": anchor(claim, "All"),
                },
            }
        )
        payload["semantic_reviews"][0]["claim_fragment"] = "widgets support signed exports"
        payload["protocol_inputs"] = {
            "generalization": {
                "target_scope": {"population": "all registered widgets"},
                "observed_scopes": [{"population": "representative registered sample"}],
                "transport_basis": {
                    "method": "registered representative sampling design",
                    "evidence_ids": ["E1"],
                    "evidence_fragments": {"E1": "Widget supports signed exports"},
                },
            }
        }
        self.assertEqual(compile_claim(payload)["admission"], "ADMIT")


class AdditionalFailureModeTests(unittest.TestCase):
    def test_malformed_json_shapes_fail_closed_without_crashing(self) -> None:
        malformed_payloads = [
            None,
            [],
            "claim",
            7,
            {},
            {"claim_ir": [], "evidence": [1], "semantic_reviews": [None]},
            {
                "claim_ir": {
                    "claim_id": "X",
                    "source_text": "X",
                    "operator": "FACT",
                    "subject": "X",
                    "predicate": "is",
                    "polarity": "POSITIVE",
                    "quantifier": "UNSPECIFIED",
                    "modality": "ASSERTED",
                    "scope": "wrong",
                    "anchors": [],
                },
                "evidence": [],
                "semantic_reviews": [],
            },
            {
                "claim_ir": fact_payload()["claim_ir"],
                "evidence": fact_payload()["evidence"],
                "semantic_reviews": fact_payload()["semantic_reviews"],
                "verified_scope": [],
                "protocol_inputs": [],
            },
        ]
        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                certificate = compile_claim(payload)
                self.assertEqual(certificate["admission"], "HOLD")
                self.assertEqual(certificate["certificate_version"], "4.1.0")

    def test_nonliteral_verified_scope_holds(self) -> None:
        payload = fact_payload()
        payload["verified_scope"] = {
            "version": {
                "value": "9.9",
                "evidence_ids": ["E1"],
                "evidence_fragments": {"E1": "not present in source"},
            }
        }
        self.assertEqual(compile_claim(payload)["admission"], "HOLD")

    def test_unknown_evidence_field_holds(self) -> None:
        payload = fact_payload()
        payload["evidence"][0]["confidence"] = 0.9
        self.assertEqual(compile_claim(payload)["admission"], "HOLD")

    def test_mixed_entailment_and_contradiction_holds(self) -> None:
        payload = fact_payload()
        second_text = "The second official record says Widget does not support signed exports."
        payload["evidence"].append(
            {
                "evidence_id": "E2",
                "source_id": "S2",
                "source_kind": "official_record",
                "source_text": second_text,
                "quote": anchor(second_text, "Widget does not support signed exports"),
            }
        )
        payload["semantic_reviews"].append(
            {
                "claim_id": "FACT-1",
                "evidence_id": "E2",
                "relation": "CONTRADICTS",
                "claim_fragment": "Widget supports signed exports",
                "evidence_fragment": "Widget does not support signed exports",
                "missing_bridge": "",
            }
        )
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(certificate["semantic_summary"]["code"], "SEMANTIC_CONFLICT")

    def test_unknown_domain_holds(self) -> None:
        payload = fact_payload()
        payload["domain"] = "MADE_UP_DOMAIN"
        self.assertEqual(compile_claim(payload)["admission"], "HOLD")

    def test_unknown_claim_class_holds(self) -> None:
        payload = fact_payload()
        payload["domain"] = "SOFTWARE"
        payload["claim_class"] = "MADE_UP_CLASS"
        payload["evidence"][0]["source_kind"] = "official_documentation"
        self.assertEqual(compile_claim(payload)["admission"], "HOLD")


class ProvenanceAndPackagingTests(unittest.TestCase):
    def test_provenance_cycle_holds(self) -> None:
        payload = fact_payload()
        payload["evidence"][0]["derived_from"] = ["S2"]
        payload["evidence"].append(
            {
                "evidence_id": "E2",
                "source_id": "S2",
                "source_kind": "official_record",
                "source_text": "Source two repeats the claim.",
                "quote": anchor("Source two repeats the claim.", "repeats the claim"),
                "derived_from": ["S1"],
            }
        )
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(certificate["provenance"]["status"], "HOLD")

    def test_digest_is_reproducible(self) -> None:
        first = compile_claim(fact_payload())
        second = compile_claim(copy.deepcopy(fact_payload()))
        self.assertEqual(first["input_digest"], second["input_digest"])

    def test_registry_has_no_dangling_routes_or_validators(self) -> None:
        registry = load_json("protocol-registry.json")
        registered = set(registry["protocols"])
        routed = {item for values in registry["base_routes"].values() for item in values}
        routed.update(registry["input_augmentations"].values())
        domains = load_json("domain-registry.json")["domains"]
        for domain in domains.values():
            routed.update(domain["required_protocols"])
        self.assertEqual(routed - registered, set())
        missing_validators = {
            item["validator"] for item in registry["protocols"].values() if item["validator"] not in VALIDATORS
        }
        self.assertEqual(missing_validators, set())
        self.assertEqual(len(registry["protocols"]), 16)
        self.assertEqual(
            set(domains),
            {
                "AI_AGENTS",
                "ECOMMERCE",
                "EDUCATION_PSYCHOLOGY",
                "FINANCE_INVESTING",
                "FOOD_COOKING",
                "HISTORY",
                "LAW",
                "MEDICINE_HEALTH",
                "META_ADS",
                "NATURAL_SCIENCE",
                "SOCIAL_SCIENCE_ECONOMICS",
                "SOFTWARE",
                "SPORTS",
            },
        )

    def test_every_claim_operator_routes_without_runtime_error(self) -> None:
        registry = load_json("protocol-registry.json")
        for operator, expected in registry["base_routes"].items():
            with self.subTest(operator=operator):
                payload = operator_payload(
                    operator,
                    "System does action output.",
                    "System",
                    "does",
                    "action output",
                    "System does action output",
                )
                certificate = compile_claim(payload)
                self.assertTrue(set(expected).issubset(certificate["protocols_required"]))
                self.assertIn(
                    certificate["admission"],
                    {"ADMIT", "ADMIT_SCOPED", "ADMIT_COMPONENTS_ONLY", "HOLD", "REJECT"},
                )

    def test_certificate_matches_declared_top_level_schema(self) -> None:
        certificate = compile_claim(fact_payload())
        schema = load_json("certificate.schema.json")
        self.assertEqual(set(schema["required"]), set(certificate))
        self.assertEqual(certificate["certificate_version"], schema["properties"]["certificate_version"]["const"])

    def test_skill_has_clean_frontmatter_and_no_todos(self) -> None:
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\nname: knowsift\n"))
        self.assertNotIn("[TODO:", content)
        self.assertIn("description:", content.split("---", 2)[1])

    def test_all_skill_links_and_json_resources_are_valid(self) -> None:
        content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        links = re.findall(r"\[[^]]+\]\(([^)]+)\)", content)
        for link in links:
            self.assertTrue((SKILL_ROOT / link).is_file(), link)
        for path in (SKILL_ROOT / "references").glob("*.json"):
            with self.subTest(path=path.name):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_runtime_has_no_network_shell_or_dynamic_execution(self) -> None:
        forbidden = (
            "import requests",
            "import urllib",
            "import socket",
            "import subprocess",
            "os.system(",
            "eval(",
            "exec(",
        )
        runtime_files = [SKILL_ROOT / "scripts" / "compile_claim.py"] + list(
            (SKILL_ROOT / "scripts" / "knowledge_compiler").glob("*.py")
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in runtime_files)
        for token in forbidden:
            self.assertNotIn(token, combined)

    def test_cli_require_admission_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text(json.dumps(fact_payload()), encoding="utf-8")
            command = [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "compile_claim.py"),
                str(path),
                "--require-admission",
            ]
            admitted = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(admitted.returncode, 0, admitted.stderr)
            self.assertEqual(json.loads(admitted.stdout)["admission"], "ADMIT")

            held_payload = fact_payload()
            held_payload["semantic_reviews"] = []
            path.write_text(json.dumps(held_payload), encoding="utf-8")
            held = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(held.returncode, 3, held.stderr)
            self.assertEqual(json.loads(held.stdout)["admission"], "HOLD")

            output = Path(directory) / "certificate.json"
            output.write_text("preserve me", encoding="utf-8")
            overwrite = subprocess.run(
                command[:3] + ["--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(overwrite.returncode, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve me")

    def test_shipped_example_compiles(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "references" / "example-input.json").read_text(encoding="utf-8")
        )
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(certificate["canonical_claim"], "Within version=4.2, Widget 4.2 supports signed exports")


if __name__ == "__main__":
    unittest.main()
