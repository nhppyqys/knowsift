"""End-to-end compiler and fail-closed certificate admission."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from .normalize import normalize_claim, render_canonical
from .protocols import route_protocols, run_protocols
from .provenance import summarize_provenance
from .registry import load_json, load_runtime_resources
from .validation import (
    classify_source_authority,
    resolve_adversarial_policy,
    resolve_min_independence,
    resolve_policy,
    validate_adversarial_reviews,
    validate_locator_authority,
    validate_snapshots,
    validate_claim_ir,
    validate_components,
    validate_evidence,
    validate_exceptions,
    validate_linked_values,
    validate_payload_shape,
    validate_semantic_reviews,
)


CERTIFICATE_VERSION = "4.3.0"


def load_json_reviewers() -> dict[str, Any]:
    """Reviewer registry, used only to sanity-check declared independence."""
    try:
        return load_json("reviewers.json")
    except (OSError, ValueError):
        return {}


def _input_digest(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda value: f"<{type(value).__name__}>",
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _decide_admission(
    *,
    structural_failure: bool,
    semantic_summary: dict[str, Any],
    locator_authority: dict[str, Any],
    snapshot_integrity: dict[str, Any],
    adversarial_summary: dict[str, Any],
    source_authority: dict[str, Any],
    protocol_results: dict[str, dict[str, Any]],
    protocol_registry: dict[str, Any],
    normalization: dict[str, Any],
    valid_components: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    appropriate = set(source_authority.get("appropriate_evidence_ids", []))
    appropriate_entails = appropriate & set(semantic_summary.get("entailing_evidence_ids", []))
    appropriate_contradictions = appropriate & set(
        semantic_summary.get("contradicting_evidence_ids", [])
    )

    if structural_failure:
        return "HOLD", ["STRUCTURAL_OR_REFERENCE_VALIDATION_FAILED"]
    if appropriate_contradictions and not appropriate_entails:
        return "REJECT", ["APPROPRIATE_EVIDENCE_CONTRADICTS_CLAIM"]
    if appropriate_contradictions and appropriate_entails:
        return "HOLD", ["APPROPRIATE_EVIDENCE_CONFLICT"]

    failed_protocols = sorted(
        name for name, result in protocol_results.items() if result.get("status") == "FAIL"
    )
    if failed_protocols:
        return "REJECT", [f"PROTOCOL_FAILED:{name}" for name in failed_protocols]

    # A source that cannot be what it claims to be, or a quote that is not in the
    # captured bytes, blocks admission before anyone argues about the reading.
    if locator_authority.get("status") == "HOLD":
        return "HOLD", [f"LOCATOR_GATE:{locator_authority.get('code', 'UNRESOLVED')}"]
    if snapshot_integrity.get("status") == "HOLD":
        return "HOLD", [f"SNAPSHOT_GATE:{snapshot_integrity.get('code', 'UNRESOLVED')}"]

    # An unresolved second opinion blocks every admission state, including the
    # components-only shortcut. The runtime never picks a winner between two
    # reviewers; it only refuses to call a contested reading knowledge.
    if adversarial_summary.get("status") == "HOLD":
        return "HOLD", [
            f"ADVERSARIAL_GATE:{adversarial_summary.get('code', 'UNRESOLVED')}"
        ]

    held_protocols = sorted(
        name for name, result in protocol_results.items() if result.get("status") == "HOLD"
    )
    semantic_error_free = not semantic_summary.get("errors")
    if valid_components and semantic_error_free and source_authority.get("status") == "PASS":
        definitions = protocol_registry.get("protocols", {})
        component_safe_holds = {
            name
            for name in held_protocols
            if name == "CAUSAL_INFERENCE"
            or (definitions.get(name) or {}).get("validator") == "semantic_evidence"
        }
        no_other_holds = set(held_protocols) == component_safe_holds
        if no_other_holds and not appropriate_contradictions and (
            semantic_summary.get("status") in {"HOLD", "PASS"}
            or normalization.get("status") == "SUPPORTED_COMPONENTS_ONLY"
        ):
            return "ADMIT_COMPONENTS_ONLY", ["ONLY_EVIDENCE_LINKED_COMPONENTS_PASSED"]

    if semantic_summary.get("status") != "PASS":
        reasons.append(f"SEMANTIC_GATE:{semantic_summary.get('code', 'UNRESOLVED')}")
    if source_authority.get("status") != "PASS":
        reasons.append(f"SOURCE_AUTHORITY:{source_authority.get('code', 'UNRESOLVED')}")
    reasons.extend(f"PROTOCOL_HELD:{name}" for name in held_protocols)
    if reasons:
        return "HOLD", reasons

    scoped = normalization.get("status") == "SUPPORTED_IF_NARROWED" or any(
        result.get("status") == "PASS_SCOPED" for result in protocol_results.values()
    )
    return ("ADMIT_SCOPED" if scoped else "ADMIT"), [
        "ALL_GATES_PASSED_WITH_SCOPE_NARROWING" if scoped else "ALL_GATES_PASSED"
    ]


def compile_claim(
    payload: Any,
    *,
    adversarial_policy: str | None = None,
    adversarial_min_independence: str | None = None,
    locator_policy: str | None = None,
    snapshot_policy: str | None = None,
    snapshot_root: Any = None,
) -> dict[str, Any]:
    resources = load_runtime_resources()
    protocol_registry = resources["protocol_registry"]
    domain_registry = resources["domain_registry"]
    causal_designs = resources["causal_designs"]
    data = payload if isinstance(payload, dict) else {}

    payload_check = validate_payload_shape(payload, resources["compile_schema"])
    ir = data.get("claim_ir") if isinstance(data.get("claim_ir"), dict) else {}
    ir_check = validate_claim_ir(
        ir,
        resources["claim_schema"],
        set(protocol_registry.get("high_impact_operators", [])),
    )
    evidence_input = data.get("evidence") if isinstance(data.get("evidence"), list) else []
    evidence_check, evidence_by_id = validate_evidence(
        evidence_input,
        resources["compile_schema"].get("$defs", {}).get("evidence", {}),
    )
    semantic_summary, valid_reviews = validate_semantic_reviews(
        data.get("semantic_reviews"), ir, evidence_by_id
    )
    host_policy = adversarial_policy
    if host_policy is None:
        host_policy = os.environ.get("KNOWSIFT_ADVERSARIAL_POLICY") or None
    effective_policy, policy_errors = resolve_adversarial_policy(
        data.get("adversarial_policy"), host_policy
    )
    reviewer_registry = load_json_reviewers()
    min_tier, tier_errors = resolve_min_independence(
        data.get("adversarial_min_independence"),
        adversarial_min_independence
        if adversarial_min_independence is not None
        else os.environ.get("KNOWSIFT_ADVERSARIAL_MIN_INDEPENDENCE") or None,
    )
    adversarial_summary, _adversarial_reviews = validate_adversarial_reviews(
        data.get("adversarial_reviews"),
        ir,
        evidence_by_id,
        valid_reviews,
        effective_policy,
        reviewer_registry,
        min_tier,
    )
    policy_errors = list(policy_errors) + tier_errors
    if policy_errors:
        adversarial_summary["errors"] = sorted(
            set(adversarial_summary["errors"]) | set(policy_errors)
        )
        adversarial_summary["status"] = "HOLD"
        adversarial_summary["code"] = "INVALID_ADVERSARIAL_POLICY"

    locator_effective, locator_policy_errors = resolve_policy(
        data.get("locator_policy"),
        locator_policy
        if locator_policy is not None
        else os.environ.get("KNOWSIFT_LOCATOR_POLICY") or None,
        "locator_policy",
    )
    locator_authority = validate_locator_authority(
        evidence_input, resources["source_kind_registry"], locator_effective
    )
    if locator_policy_errors:
        locator_authority["errors"] = sorted(
            set(locator_authority["errors"]) | set(locator_policy_errors)
        )
        locator_authority["status"] = "HOLD"
        locator_authority["code"] = "INVALID_LOCATOR_POLICY"

    snapshot_effective, snapshot_policy_errors = resolve_policy(
        data.get("snapshot_policy"),
        snapshot_policy
        if snapshot_policy is not None
        else os.environ.get("KNOWSIFT_SNAPSHOT_POLICY") or None,
        "snapshot_policy",
    )
    snapshot_integrity = validate_snapshots(
        evidence_input,
        snapshot_root if snapshot_root is not None else os.environ.get("KNOWSIFT_SNAPSHOT_ROOT"),
        snapshot_effective,
    )
    if snapshot_policy_errors:
        snapshot_integrity["errors"] = sorted(
            set(snapshot_integrity["errors"]) | set(snapshot_policy_errors)
        )
        snapshot_integrity["status"] = "HOLD"
        snapshot_integrity["code"] = "INVALID_SNAPSHOT_POLICY"
    scope_check = validate_linked_values(
        "verified_scope", data.get("verified_scope"), evidence_by_id
    )
    conditions_check = validate_linked_values(
        "verified_conditions", data.get("verified_conditions"), evidence_by_id
    )
    exceptions_check = validate_exceptions(data.get("verified_exceptions"), evidence_by_id)
    components_check = validate_components(
        data.get("supported_components"), ir, evidence_by_id, valid_reviews
    )

    provenance = summarize_provenance(evidence_input)
    source_authority = classify_source_authority(
        data.get("domain"), data.get("claim_class"), evidence_by_id, valid_reviews, domain_registry
    )
    protocols_required, routing_errors = route_protocols(
        data, protocol_registry, domain_registry
    )
    routing_check = {
        "status": "PASS" if not routing_errors else "HOLD",
        "errors": routing_errors,
    }

    context = {
        "payload": data,
        "ir": ir,
        "evidence": evidence_input,
        "evidence_by_id": evidence_by_id,
        "valid_reviews": valid_reviews,
        "semantic_summary": semantic_summary,
        "adversarial_summary": adversarial_summary,
        "locator_authority": locator_authority,
        "snapshot_integrity": snapshot_integrity,
        "source_authority": source_authority,
        "verified_scope": scope_check.get("plain", {}),
        "verified_conditions": conditions_check.get("plain", {}),
        "verified_exceptions": exceptions_check.get("valid", []),
        "valid_components": components_check.get("valid", []),
        "provenance": provenance,
        "causal_designs": causal_designs,
    }

    pre_protocol_checks = (
        payload_check,
        ir_check,
        evidence_check,
        scope_check,
        conditions_check,
        exceptions_check,
        components_check,
        routing_check,
    )
    upstream_failure = any(check.get("status") != "PASS" for check in pre_protocol_checks)
    upstream_failure = upstream_failure or provenance.get("status") != "PASS"
    if upstream_failure:
        protocol_results = {
            protocol: {
                "status": "HOLD",
                "code": "UPSTREAM_VALIDATION_FAILED",
                "missing": [],
            }
            for protocol in protocols_required
        }
    else:
        protocol_results = run_protocols(protocols_required, protocol_registry, context)

    if ir_check.get("status") == "PASS":
        normalization = normalize_claim(
            ir,
            data,
            protocol_results,
            semantic_summary,
            scope_check.get("plain", {}),
            conditions_check.get("plain", {}),
            exceptions_check.get("valid", []),
            components_check.get("valid", []),
        )
    else:
        normalization = {
            "status": "HOLD",
            "normalized_ir": None,
            "transformations": ["NORMALIZATION_BLOCKED_BY_INVALID_CLAIM_IR"],
        }

    structural_checks = {
        "payload": payload_check,
        "claim_ir": ir_check,
        "evidence": evidence_check,
        "verified_scope": scope_check,
        "verified_conditions": conditions_check,
        "verified_exceptions": {
            "status": exceptions_check["status"],
            "errors": exceptions_check["errors"],
        },
        "supported_components": {
            "status": components_check["status"],
            "errors": components_check["errors"],
        },
        "routing": routing_check,
    }
    structural_failure = any(
        check.get("status") != "PASS" for check in structural_checks.values()
    ) or provenance.get("status") != "PASS"

    admission, decisive_reasons = _decide_admission(
        structural_failure=structural_failure,
        semantic_summary=semantic_summary,
        locator_authority=locator_authority,
        snapshot_integrity=snapshot_integrity,
        adversarial_summary=adversarial_summary,
        source_authority=source_authority,
        protocol_results=protocol_results,
        protocol_registry=protocol_registry,
        normalization=normalization,
        valid_components=components_check.get("valid", []),
    )

    unresolved: list[str] = []
    for name, check in structural_checks.items():
        unresolved.extend(f"{name}:{error}" for error in check.get("errors", []))
    if provenance.get("status") != "PASS":
        unresolved.append(f"provenance:{provenance.get('code')}")
    unresolved.extend(f"semantic:{error}" for error in semantic_summary.get("errors", []))
    if semantic_summary.get("status") == "HOLD":
        unresolved.append(f"semantic:{semantic_summary.get('code')}")
    if source_authority.get("status") != "PASS":
        unresolved.append(f"source_authority:{source_authority.get('code')}")
    if locator_authority.get("status") == "HOLD":
        unresolved.append(f"locator:{locator_authority.get('code')}")
    unresolved.extend(f"locator:{error}" for error in locator_authority.get("errors", []))
    unresolved.extend(
        "locator:contradicted:{evidence_id}:{kind}:not_available_from:{rule}".format(
            evidence_id=item.get("evidence_id"),
            kind=item.get("source_kind"),
            rule=item.get("rule"),
        )
        for item in locator_authority.get("violations", [])
    )
    if snapshot_integrity.get("status") == "HOLD":
        unresolved.append(f"snapshot:{snapshot_integrity.get('code')}")
    unresolved.extend(f"snapshot:{error}" for error in snapshot_integrity.get("errors", []))
    if adversarial_summary.get("status") == "HOLD":
        unresolved.append(f"adversarial:{adversarial_summary.get('code')}")
    unresolved.extend(
        f"adversarial:{error}" for error in adversarial_summary.get("errors", [])
    )
    unresolved.extend(
        "adversarial:disagreement:{evidence_id}:{first}->{second}".format(
            evidence_id=item.get("evidence_id"),
            first=item.get("first_pass_relation"),
            second=item.get("adversarial_relation"),
        )
        for item in adversarial_summary.get("disagreements", [])
    )
    for name, result in protocol_results.items():
        if result.get("status") == "HOLD":
            unresolved.append(f"protocol:{name}:{result.get('code')}")
            unresolved.extend(
                f"protocol:{name}:missing:{item}" for item in result.get("missing", [])
            )

    evidence_references = [
        {
            "evidence_id": item.get("evidence_id"),
            "source_id": item.get("source_id"),
            "source_kind": item.get("source_kind"),
            "quote": item.get("quote"),
            "date": item.get("date"),
            "version": item.get("version"),
            "scope": item.get("scope", {}),
        }
        for item in evidence_input
        if isinstance(item, dict)
    ]
    normalized_ir = normalization.get("normalized_ir")
    if admission not in {"ADMIT", "ADMIT_SCOPED"}:
        normalized_ir = None

    return {
        "certificate_version": CERTIFICATE_VERSION,
        "input_digest": _input_digest(payload),
        "claim_id": ir.get("claim_id"),
        "claim_text": ir.get("source_text") if isinstance(ir.get("source_text"), str) else None,
        "canonical_claim": render_canonical(normalized_ir),
        "normalized_ir": normalized_ir,
        "protocols_required": protocols_required,
        "machine_checks": structural_checks,
        "semantic_summary": semantic_summary,
        "adversarial_summary": adversarial_summary,
        "locator_authority": locator_authority,
        "snapshot_integrity": snapshot_integrity,
        "source_authority": source_authority,
        "protocol_results": protocol_results,
        "provenance": provenance,
        "evidence_references": evidence_references,
        "transformations": normalization.get("transformations", []),
        "supported_components": components_check.get("valid", []),
        "unresolved": _deduplicate(unresolved),
        "decisive_reasons": decisive_reasons,
        "admission": admission,
    }
