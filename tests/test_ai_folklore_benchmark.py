"""Locks the shipped AI folklore benchmark against silent drift."""

from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CASE = SKILL_ROOT / "examples" / "ai-folklore-benchmark"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from knowledge_compiler import compile_claim, validate_source_bundle  # noqa: E402
from knowledge_compiler.knowledge_document import (  # noqa: E402
    render_knowledge_document,
    validate_document_plan,
)
from knowledge_compiler.registry import load_json  # noqa: E402
from knowledge_compiler.validation import classify_locator  # noqa: E402


def read(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


class AIFolkloreBenchmarkTests(unittest.TestCase):
    def test_bundle_holds_eleven_captured_sources(self) -> None:
        bundle = read(CASE / "source-bundle.json")
        self.assertEqual(len(validate_source_bundle(bundle, CASE)["sources"]), 11)

    def test_layer_counts_are_seven_four_six(self) -> None:
        plan = read(CASE / "knowledge-document.json")
        counts = Counter(record["layer"] for record in plan["records"])
        self.assertEqual(counts["SUPPORTED_KNOWLEDGE"], 7)
        self.assertEqual(counts["DISPUTED_OR_UNRESOLVED"], 4)
        self.assertEqual(counts["REJECTED"], 6)
        self.assertEqual(sum(counts.values()), 17)

    def test_document_plan_still_validates_and_renders(self) -> None:
        plan = read(CASE / "knowledge-document.json")
        validate_document_plan(plan, CASE)
        rendered = render_knowledge_document(plan, CASE)
        self.assertEqual(rendered, (CASE / "RESULT.md").read_text(encoding="utf-8"))

    def test_every_certificate_recompiles_to_the_same_admission(self) -> None:
        for claim_file in sorted((CASE / "claims").glob("*.json")):
            with self.subTest(claim=claim_file.stem):
                committed = read(CASE / "certificates" / claim_file.name)
                fresh = compile_claim(read(claim_file), locator_policy="required")
                self.assertEqual(fresh["admission"], committed["admission"])

    def test_no_source_kind_contradicts_its_locator(self) -> None:
        registry = load_json("source-kinds.json")
        class_of = {k: c for c, ks in registry["kind_classes"].items() for k in ks}
        checked = 0
        for claim_file in sorted((CASE / "claims").glob("*.json")):
            for item in read(claim_file)["evidence"]:
                verdict = classify_locator(item["locator"], registry)
                self.assertEqual(verdict["status"], "CLASSIFIED", item["locator"])
                self.assertIn(class_of[item["source_kind"]], verdict["permits"])
                checked += 1
        self.assertEqual(checked, 18)

    def test_a_second_reviewer_read_every_claim(self) -> None:
        for claim_file in sorted((CASE / "claims").glob("*.json")):
            with self.subTest(claim=claim_file.stem):
                certificate = read(CASE / "certificates" / claim_file.name)
                summary = certificate["adversarial_summary"]
                self.assertEqual(summary["policy"], "required")
                self.assertEqual(summary["reviewer_ids"], ["claude-haiku-4-5-20251001"])
                for entry in summary["independence"].values():
                    self.assertEqual(entry["declared"], "SAME_FAMILY")

    def test_the_four_reviewer_disagreements_are_recorded(self) -> None:
        disputed = {
            claim_file.stem
            for claim_file in sorted((CASE / "claims").glob("*.json"))
            if read(CASE / "certificates" / claim_file.name)["adversarial_summary"]["disagreements"]
        }
        self.assertEqual(
            disputed, {"AI-COT-001", "AI-SELF-001", "AI-SELF-003", "AI-EMO-001"}
        )

    def test_every_falsifier_is_recorded_for_a_human_to_check(self) -> None:
        for claim_file in sorted((CASE / "claims").glob("*.json")):
            with self.subTest(claim=claim_file.stem):
                falsifiers = read(CASE / "certificates" / claim_file.name)[
                    "adversarial_summary"
                ]["falsifiers"]
                self.assertTrue(falsifiers)
                for item in falsifiers:
                    self.assertTrue(item["what_would_falsify"].strip())


if __name__ == "__main__":
    unittest.main()
