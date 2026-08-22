"""Tests for the independent second-reviewer gate."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from knowledge_compiler import compile_claim  # noqa: E402
from knowledge_compiler.validation import resolve_adversarial_policy  # noqa: E402

from test_compiler import fact_payload  # noqa: E402

import adversarial_review  # noqa: E402


EVIDENCE_TEXT = "The official record states: Widget supports signed exports."
FRAGMENT = "Widget supports signed exports"


def counter_review(**overrides: object) -> dict[str, object]:
    review = {
        "claim_id": "FACT-1",
        "evidence_id": "E1",
        "relation": "ENTAILS",
        "reviewer_id": "gpt-5-review",
        "independence": "CROSS_FAMILY",
        "evidence_fragment": FRAGMENT,
        "strongest_counter_reading": "The record reports a capability, not its reliability.",
        "what_would_falsify": "A later revision of the same record dropping signed exports.",
    }
    review.update(overrides)
    return review


def reviewed_payload(**overrides: object) -> dict[str, object]:
    payload = fact_payload()
    payload["semantic_reviews"][0]["reviewer_id"] = "claude-opus-5"
    payload["adversarial_reviews"] = [counter_review(**overrides)]
    return payload


class PolicyResolutionTests(unittest.TestCase):
    def test_default_is_optional(self) -> None:
        self.assertEqual(resolve_adversarial_policy(None, None), ("optional", []))

    def test_payload_alone_can_disable(self) -> None:
        self.assertEqual(resolve_adversarial_policy("off", None), ("off", []))

    def test_payload_cannot_relax_the_host(self) -> None:
        policy, errors = resolve_adversarial_policy("off", "required")
        self.assertEqual(policy, "required")
        self.assertEqual(errors, [])

    def test_host_cannot_be_relaxed_by_optional_either(self) -> None:
        self.assertEqual(resolve_adversarial_policy("optional", "required")[0], "required")

    def test_invalid_values_are_reported(self) -> None:
        policy, errors = resolve_adversarial_policy("lenient", None)
        self.assertEqual(policy, "optional")
        self.assertEqual(errors, ["adversarial_policy:invalid_payload_value:lenient"])


class AdversarialGateTests(unittest.TestCase):
    def test_absent_review_is_backward_compatible(self) -> None:
        certificate = compile_claim(fact_payload())
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(certificate["adversarial_summary"]["status"], "SKIPPED")

    def test_required_policy_holds_without_a_second_reviewer(self) -> None:
        certificate = compile_claim(fact_payload(), adversarial_policy="required")
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(
            certificate["decisive_reasons"],
            ["ADVERSARIAL_GATE:ADVERSARIAL_REVIEW_REQUIRED"],
        )

    def test_agreement_admits(self) -> None:
        certificate = compile_claim(reviewed_payload(), adversarial_policy="required")
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(certificate["adversarial_summary"]["code"], "INDEPENDENT_REVIEW_AGREES")
        self.assertEqual(certificate["adversarial_summary"]["reviewer_ids"], ["gpt-5-review"])
        self.assertEqual(certificate["adversarial_summary"]["weakest_independence"], "CROSS_FAMILY")

    def test_disagreement_holds_even_when_review_is_optional(self) -> None:
        certificate = compile_claim(reviewed_payload(relation="PARTIAL"))
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(
            certificate["decisive_reasons"], ["ADVERSARIAL_GATE:REVIEWER_DISAGREEMENT"]
        )
        disagreement = certificate["adversarial_summary"]["disagreements"][0]
        self.assertEqual(disagreement["first_pass_relation"], "ENTAILS")
        self.assertEqual(disagreement["adversarial_relation"], "PARTIAL")

    def test_same_model_fresh_context_is_allowed_but_labelled(self) -> None:
        certificate = compile_claim(
            reviewed_payload(reviewer_id="claude-opus-5", independence="SAME_MODEL")
        )
        self.assertEqual(certificate["admission"], "ADMIT")
        self.assertEqual(
            certificate["adversarial_summary"]["weakest_independence"], "SAME_MODEL"
        )

    def test_a_reviewer_cannot_overclaim_its_own_independence(self) -> None:
        certificate = compile_claim(
            reviewed_payload(reviewer_id="claude-opus-5", independence="CROSS_FAMILY")
        )
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIn(
            "adversarial_reviews:independence_overclaimed:E1:CROSS_FAMILY_above_SAME_MODEL",
            certificate["adversarial_summary"]["errors"],
        )

    def test_same_family_cannot_pass_as_cross_family(self) -> None:
        certificate = compile_claim(
            reviewed_payload(reviewer_id="claude-haiku-4-5", independence="CROSS_FAMILY")
        )
        self.assertEqual(certificate["admission"], "HOLD")

    def test_an_unrecognised_model_id_caps_at_same_family(self) -> None:
        certificate = compile_claim(
            reviewed_payload(reviewer_id="my-private-model", independence="CROSS_FAMILY")
        )
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(
            compile_claim(
                reviewed_payload(reviewer_id="my-private-model", independence="SAME_FAMILY")
            )["admission"],
            "ADMIT",
        )

    def test_host_can_demand_a_stronger_tier(self) -> None:
        payload = reviewed_payload(reviewer_id="claude-opus-5", independence="SAME_MODEL")
        certificate = compile_claim(payload, adversarial_min_independence="CROSS_FAMILY")
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(
            certificate["decisive_reasons"],
            ["ADVERSARIAL_GATE:ADVERSARIAL_INDEPENDENCE_BELOW_MINIMUM"],
        )

    def test_same_context_is_never_review(self) -> None:
        certificate = compile_claim(
            reviewed_payload(reviewer_id="claude-opus-5", independence="SAME_CONTEXT")
        )
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIn(
            "adversarial_reviews[0]:same_context_is_not_review",
            certificate["adversarial_summary"]["errors"],
        )

    def test_independence_must_be_declared(self) -> None:
        payload = reviewed_payload()
        del payload["adversarial_reviews"][0]["independence"]
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")

    def test_invented_quote_never_admits(self) -> None:
        certificate = compile_claim(reviewed_payload(evidence_fragment="a line I made up"))
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIn(
            "adversarial_reviews[0]:evidence_fragment_not_literal",
            certificate["adversarial_summary"]["errors"],
        )

    def test_falsifier_and_counter_reading_are_mandatory(self) -> None:
        for field in ("what_would_falsify", "strongest_counter_reading"):
            with self.subTest(field=field):
                certificate = compile_claim(reviewed_payload(**{field: "   "}))
                self.assertEqual(certificate["admission"], "HOLD")
                self.assertIn(
                    f"adversarial_reviews[0]:empty_{field}",
                    certificate["adversarial_summary"]["errors"],
                )

    def test_confidence_scores_stay_forbidden(self) -> None:
        payload = reviewed_payload()
        payload["adversarial_reviews"][0]["confidence"] = 0.9
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "HOLD")

    def test_required_policy_needs_every_first_pass_review_covered(self) -> None:
        payload = reviewed_payload()
        payload["adversarial_reviews"] = []
        certificate = compile_claim(payload, adversarial_policy="required")
        self.assertEqual(certificate["admission"], "HOLD")
        summary = certificate["adversarial_summary"]
        self.assertEqual(summary["code"], "ADVERSARIAL_REVIEW_INCOMPLETE")
        self.assertEqual(summary["unreviewed_evidence_ids"], ["E1"])

    def test_required_policy_needs_a_first_pass_reviewer_id(self) -> None:
        payload = reviewed_payload()
        del payload["semantic_reviews"][0]["reviewer_id"]
        certificate = compile_claim(payload, adversarial_policy="required")
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertIn(
            "semantic_reviews:missing_reviewer_id:E1",
            certificate["adversarial_summary"]["errors"],
        )

    def test_orphan_review_is_an_error(self) -> None:
        certificate = compile_claim(reviewed_payload(evidence_id="E-NOPE"))
        self.assertEqual(certificate["admission"], "HOLD")

    def test_payload_policy_cannot_escape_the_host_requirement(self) -> None:
        payload = fact_payload()
        payload["adversarial_policy"] = "off"
        certificate = compile_claim(payload, adversarial_policy="required")
        self.assertEqual(certificate["admission"], "HOLD")
        self.assertEqual(certificate["adversarial_summary"]["policy"], "required")

    def test_environment_can_raise_the_policy(self) -> None:
        os.environ["KNOWSIFT_ADVERSARIAL_POLICY"] = "required"
        try:
            certificate = compile_claim(fact_payload())
        finally:
            del os.environ["KNOWSIFT_ADVERSARIAL_POLICY"]
        self.assertEqual(certificate["admission"], "HOLD")

    def test_gate_never_softens_a_reject(self) -> None:
        payload = reviewed_payload(relation="PARTIAL")
        payload["semantic_reviews"][0]["relation"] = "CONTRADICTS"
        payload["semantic_reviews"][0]["missing_bridge"] = ""
        certificate = compile_claim(payload)
        self.assertEqual(certificate["admission"], "REJECT")

    def test_disagreement_blocks_the_components_shortcut(self) -> None:
        payload = fact_payload()
        payload["semantic_reviews"][0]["reviewer_id"] = "claude-opus-5"
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
        self.assertEqual(compile_claim(copy.deepcopy(payload))["admission"], "ADMIT_COMPONENTS_ONLY")
        payload["adversarial_reviews"] = [counter_review(relation="UNRELATED")]
        self.assertEqual(compile_claim(payload)["admission"], "HOLD")

    def test_falsifiers_reach_the_certificate(self) -> None:
        certificate = compile_claim(reviewed_payload())
        self.assertEqual(
            certificate["adversarial_summary"]["falsifiers"],
            [
                {
                    "evidence_id": "E1",
                    "what_would_falsify": (
                        "A later revision of the same record dropping signed exports."
                    ),
                }
            ],
        )


class ReviewerRuntimeTests(unittest.TestCase):
    def test_prompt_hides_the_first_pass_verdict(self) -> None:
        prompt = adversarial_review.build_prompt(reviewed_payload())
        self.assertIn(EVIDENCE_TEXT, prompt)
        self.assertIn("E1", prompt)
        self.assertNotIn("claude-opus-5", prompt)
        self.assertNotIn("missing_bridge", prompt)

    def test_json_survives_prose_and_fences(self) -> None:
        wrapped = 'Sure!\n```json\n{"reviews": [{"relation": "ENTAILS"}]}\n```\nHope that helps.'
        self.assertEqual(
            adversarial_review.extract_json(wrapped),
            {"reviews": [{"relation": "ENTAILS"}]},
        )

    def test_braces_inside_strings_do_not_break_extraction(self) -> None:
        text = 'note: {"reviews": [{"what_would_falsify": "a } inside a string"}]}'
        parsed = adversarial_review.extract_json(text)
        self.assertEqual(parsed["reviews"][0]["what_would_falsify"], "a } inside a string")

    def test_unparseable_output_returns_none(self) -> None:
        self.assertIsNone(adversarial_review.extract_json("I could not do that."))

    def test_finalize_stamps_identity_without_repairing_judgements(self) -> None:
        raw = [{"evidence_id": "E1", "relation": "NONSENSE", "evidence_fragment": "x"}]
        finalized = adversarial_review.finalize_reviews(
            raw, fact_payload(), "reviewer-b", "SAME_FAMILY"
        )
        self.assertEqual(finalized[0]["claim_id"], "FACT-1")
        self.assertEqual(finalized[0]["reviewer_id"], "reviewer-b")
        self.assertEqual(finalized[0]["independence"], "SAME_FAMILY")
        self.assertEqual(finalized[0]["relation"], "NONSENSE")
        self.assertIsNone(finalized[0]["what_would_falsify"])

    def test_detect_always_offers_a_route_without_a_second_cli(self) -> None:
        report = adversarial_review.detect()
        route_ids = {route["id"] for route in report["routes"]}
        self.assertIn("host-subagent", route_ids)
        self.assertIn("manual", route_ids)

    def test_detect_reports_a_broken_install_as_unavailable(self) -> None:
        backend = {
            "id": "broken",
            "executable": "python3",
            "probe": ["python3", "-c", "import sys; sys.exit(1)"],
        }
        status = adversarial_review._probe(backend)
        self.assertFalse(status["available"])
        self.assertIn("not runnable", status["reason"])

    def test_custom_backend_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory) / "stub.py"
            stub.write_text(
                "import sys, json\n"
                "sys.stdin.read()\n"
                "print(json.dumps({'reviews': [{'evidence_id': 'E1', "
                "'relation': 'PARTIAL', 'evidence_fragment': "
                f"{FRAGMENT!r}, "
                "'strongest_counter_reading': 'c', 'what_would_falsify': 'f'}]}))\n",
                encoding="utf-8",
            )
            os.environ["KNOWSIFT_REVIEWER_CMD"] = f"{sys.executable} {stub}"
            try:
                reviews = adversarial_review.run_backend(
                    fact_payload(), "custom", "stub-model", 60
                )
            finally:
                del os.environ["KNOWSIFT_REVIEWER_CMD"]
        self.assertEqual(reviews[0]["reviewer_id"], "stub-model")
        self.assertEqual(reviews[0]["independence"], "SAME_FAMILY")
        payload = fact_payload()
        payload["semantic_reviews"][0]["reviewer_id"] = "claude-opus-5"
        payload["adversarial_reviews"] = reviews
        self.assertEqual(compile_claim(payload)["admission"], "HOLD")

    def test_independence_is_derived_not_asserted(self) -> None:
        cases = [
            ("claude-opus-5", "claude-opus-5", "CROSS_FAMILY", "SAME_MODEL"),
            ("claude-opus-5", "claude-haiku-4-5", "CROSS_FAMILY", "SAME_FAMILY"),
            ("claude-opus-5", "gpt-5-codex", None, "CROSS_FAMILY"),
            ("claude-opus-5", "gpt-5-codex", "SAME_MODEL", "SAME_MODEL"),
            (None, "gpt-5-codex", "CROSS_FAMILY", "SAME_FAMILY"),
        ]
        for first, second, declared, expected in cases:
            with self.subTest(first=first, second=second, declared=declared):
                self.assertEqual(
                    adversarial_review.resolve_independence(first, second, declared),
                    expected,
                )

    def test_child_env_drops_parent_session_credentials(self) -> None:
        backend = {"scrub_env": ["ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"]}
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "parent-session-token"
        try:
            env = adversarial_review.child_env(backend)
        finally:
            del os.environ["ANTHROPIC_AUTH_TOKEN"]
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", env)
        self.assertIn("PATH", env)

    def test_cli_flag_raises_the_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            claim = Path(directory) / "claim.json"
            claim.write_text(json.dumps(fact_payload()), encoding="utf-8")
            done = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts" / "compile_claim.py"),
                    str(claim),
                    "--adversarial",
                    "required",
                    "--require-admission",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(done.returncode, 3)
        self.assertEqual(json.loads(done.stdout)["admission"], "HOLD")


if __name__ == "__main__":
    unittest.main()
