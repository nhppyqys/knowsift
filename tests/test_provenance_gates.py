"""Tests for the locator-authority and snapshot-integrity gates."""

from __future__ import annotations

import copy
import glob
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from knowledge_compiler import compile_claim  # noqa: E402
from knowledge_compiler.registry import load_json  # noqa: E402
from knowledge_compiler.validation import classify_locator  # noqa: E402

from test_compiler import fact_payload  # noqa: E402


REGISTRY = load_json("source-kinds.json")
GOV = "https://www.nrta.gov.cn/art/2026/7/31/art_1588_73827.html"
BILI_VIDEO = "https://www.bilibili.com/video/BV1n3Vz6LEVS/"
BILI_RULES = "https://www.bilibili.com/blackboard/charge-privacy.html"


def located(locator: str, source_kind: str | None = None) -> dict[str, object]:
    payload = fact_payload()
    payload["evidence"][0]["locator"] = locator
    if source_kind:
        payload["evidence"][0]["source_kind"] = source_kind
    return payload


class LocatorClassificationTests(unittest.TestCase):
    def test_path_decides_who_is_speaking_on_one_host(self) -> None:
        self.assertIn("OFFICIAL", classify_locator(BILI_RULES, REGISTRY)["permits"])
        self.assertNotIn("OFFICIAL", classify_locator(BILI_VIDEO, REGISTRY)["permits"])

    def test_subdomains_inherit_the_host_rule(self) -> None:
        verdict = classify_locator("https://m.bilibili.com/video/BV1x/", REGISTRY)
        self.assertEqual(verdict["status"], "CLASSIFIED")
        self.assertNotIn("OFFICIAL", verdict["permits"])

    def test_www_prefix_is_ignored(self) -> None:
        bare = classify_locator("https://youtube.com/watch?v=x", REGISTRY)
        prefixed = classify_locator("https://www.youtube.com/watch?v=x", REGISTRY)
        self.assertEqual(bare["permits"], prefixed["permits"])

    def test_a_blog_path_cannot_speak_for_the_organisation(self) -> None:
        verdict = classify_locator("https://support.google.com/blog/whatever", REGISTRY)
        self.assertNotIn("OFFICIAL", verdict["permits"])
        self.assertTrue(verdict["demotions_applied"])

    def test_unknown_host_is_unverifiable_not_innocent(self) -> None:
        verdict = classify_locator("https://example.invalid/whitepaper", REGISTRY)
        self.assertEqual(verdict["code"], "UNKNOWN_HOST")
        self.assertIsNone(verdict["permits"])

    def test_non_http_locator_is_unverifiable(self) -> None:
        for locator in ("file:///tmp/x.txt", "internal wiki page", "doi:10.1000/xyz", ""):
            with self.subTest(locator=locator):
                self.assertEqual(classify_locator(locator, REGISTRY)["status"], "UNVERIFIABLE")

    def test_every_registry_source_kind_has_a_class(self) -> None:
        classified = {k for kinds in REGISTRY["kind_classes"].values() for k in kinds}
        declared: set[str] = set()

        def walk(node: object) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in ("preferred_sources", "insufficient_as_sole_source"):
                        declared.update(value)
                    else:
                        walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(load_json("domain-registry.json"))
        self.assertEqual(declared - classified, set())


class LocatorGateTests(unittest.TestCase):
    def test_consistent_locator_still_admits(self) -> None:
        certificate = compile_claim(located(GOV))
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(certificate["locator_authority"]["code"], "LOCATOR_SUPPORTS_DECLARED_ROLE")

    def test_a_user_video_cannot_be_relabelled_official(self) -> None:
        certificate = compile_claim(located(BILI_VIDEO, "official_documentation"))
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(
            certificate["decisive_reasons"],
            ["LOCATOR_GATE:SOURCE_KIND_CONTRADICTED_BY_LOCATOR"],
        )
        violation = certificate["locator_authority"]["violations"][0]
        self.assertEqual(violation["declared_class"], "OFFICIAL")
        self.assertNotIn("OFFICIAL", violation["locator_permits"])

    def test_platform_rules_path_is_allowed_to_be_official(self) -> None:
        certificate = compile_claim(located(BILI_RULES, "official_documentation"))
        self.assertEqual(certificate["admission"], "ADMIT")

    def test_missing_locator_is_tolerated_by_default(self) -> None:
        certificate = compile_claim(fact_payload())
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(certificate["locator_authority"]["status"], "SKIPPED")

    def test_required_policy_rejects_an_unverifiable_source(self) -> None:
        certificate = compile_claim(fact_payload(), locator_policy="required")
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(
            certificate["decisive_reasons"], ["LOCATOR_GATE:LOCATOR_NOT_VERIFIABLE"]
        )

    def test_policy_off_disables_the_gate(self) -> None:
        payload = located(BILI_VIDEO, "official_documentation")
        certificate = compile_claim(payload, locator_policy="off")
        self.assertEqual(certificate["locator_authority"]["status"], "SKIPPED")

    def test_payload_cannot_relax_the_host_policy(self) -> None:
        payload = fact_payload()
        payload["locator_policy"] = "off"
        certificate = compile_claim(payload, locator_policy="required")
        self.assertEqual(certificate["admission"], "HOLD")

    def test_environment_can_raise_the_policy(self) -> None:
        os.environ["KNOWSIFT_LOCATOR_POLICY"] = "required"
        try:
            certificate = compile_claim(fact_payload())
        finally:
            del os.environ["KNOWSIFT_LOCATOR_POLICY"]
        self.assertEqual(certificate["admission"], "HOLD")

    def test_gate_never_softens_a_reject(self) -> None:
        payload = located(BILI_VIDEO, "official_documentation")
        payload["semantic_reviews"][0]["relation"] = "CONTRADICTS"
        self.assertEqual(compile_claim(payload)["admission"], "REJECT")

    def test_gate_blocks_the_components_shortcut(self) -> None:
        payload = located(BILI_VIDEO, "official_documentation")
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
        self.assertEqual(compile_claim(payload)["admission"], "HOLD")


class ShippedBenchmarkLocatorTests(unittest.TestCase):
    """The rules have to agree with 17 hand-audited real sources, not just toy ones."""

    def test_no_shipped_source_contradicts_its_locator(self) -> None:
        bundle = json.loads(
            (SKILL_ROOT / "examples/short-drama-benchmark/source-bundle.json").read_text(
                encoding="utf-8"
            )
        )
        locators = {source["source_id"]: source["locator"] for source in bundle["sources"]}
        class_of = {k: c for c, ks in REGISTRY["kind_classes"].items() for k in ks}

        contradictions = []
        classified = 0
        for path in glob.glob(str(SKILL_ROOT / "examples/short-drama-benchmark/claims/*.json")):
            for item in json.loads(Path(path).read_text(encoding="utf-8"))["evidence"]:
                locator = locators.get(item["source_id"])
                verdict = classify_locator(locator, REGISTRY)
                if verdict["status"] != "CLASSIFIED":
                    continue
                classified += 1
                if class_of.get(item["source_kind"]) not in verdict["permits"]:
                    contradictions.append((item["source_id"], item["source_kind"]))
        self.assertEqual(contradictions, [])
        self.assertGreater(classified, 20)


class SnapshotGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.text = "The official record states: Widget supports signed exports."
        self.file = self.root / "record.txt"
        self.file.write_text(self.text, encoding="utf-8")
        self.digest = hashlib.sha256(self.file.read_bytes()).hexdigest()
        self.addCleanup(self._dir.cleanup)

    def snapshotted(self, **overrides: object) -> dict[str, object]:
        payload = fact_payload()
        snapshot = {"path": "record.txt", "sha256": self.digest}
        snapshot.update(overrides)
        payload["evidence"][0]["snapshot"] = snapshot
        return payload

    def test_quoted_text_found_in_capture_admits(self) -> None:
        certificate = compile_claim(self.snapshotted(), snapshot_root=self.root)
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(certificate["snapshot_integrity"]["code"], "QUOTED_TEXT_MATCHES_CAPTURE")

    def test_text_added_after_capture_is_caught(self) -> None:
        payload = self.snapshotted()
        payload["evidence"][0]["source_text"] = self.text + " And it always works."
        certificate = compile_claim(payload, snapshot_root=self.root)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIn(
            "snapshot:E1:source_text_not_in_snapshot",
            certificate["snapshot_integrity"]["errors"],
        )

    def test_edited_capture_is_caught(self) -> None:
        self.file.write_text(self.text + " edited", encoding="utf-8")
        certificate = compile_claim(self.snapshotted(), snapshot_root=self.root)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIn("snapshot:E1:sha256_mismatch", certificate["snapshot_integrity"]["errors"])

    def test_path_cannot_escape_the_root(self) -> None:
        payload = self.snapshotted(path="../outside.txt")
        certificate = compile_claim(payload, snapshot_root=self.root)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIn(
            "snapshot:E1:path_escapes_snapshot_root",
            certificate["snapshot_integrity"]["errors"],
        )

    def test_missing_file_is_caught(self) -> None:
        payload = self.snapshotted(path="gone.txt")
        certificate = compile_claim(payload, snapshot_root=self.root)
        self.assertEqual(certificate["admission"], "HOLD")

    def test_snapshot_without_a_root_is_not_silently_accepted(self) -> None:
        certificate = compile_claim(self.snapshotted())
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIn(
            "snapshot:E1:no_snapshot_root_configured",
            certificate["snapshot_integrity"]["errors"],
        )

    def test_binary_capture_is_rejected_rather_than_guessed(self) -> None:
        blob = self.root / "blob.bin"
        blob.write_bytes(b"\xff\xfe\x00binary")
        payload = self.snapshotted(
            path="blob.bin", sha256=hashlib.sha256(blob.read_bytes()).hexdigest()
        )
        certificate = compile_claim(payload, snapshot_root=self.root)
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIn("snapshot:E1:snapshot_not_utf8", certificate["snapshot_integrity"]["errors"])

    def test_required_policy_needs_every_item_captured(self) -> None:
        certificate = compile_claim(fact_payload(), snapshot_policy="required")
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(certificate["decisive_reasons"], ["SNAPSHOT_GATE:SNAPSHOT_REQUIRED"])

    def test_absent_snapshot_is_tolerated_by_default(self) -> None:
        self.assertEqual(compile_claim(fact_payload())["admission"], "ADMIT")

    def test_environment_supplies_the_root(self) -> None:
        os.environ["KNOWSIFT_SNAPSHOT_ROOT"] = str(self.root)
        try:
            certificate = compile_claim(self.snapshotted())
        finally:
            del os.environ["KNOWSIFT_SNAPSHOT_ROOT"]
        self.assertEqual(certificate["admission"], "ADMIT")


if __name__ == "__main__":
    unittest.main()
