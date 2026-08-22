"""Fail-closed structural, literal, and reference validation."""

from __future__ import annotations

from collections import Counter
from typing import Any


ALLOWED_RELATIONS = {"ENTAILS", "CONTRADICTS", "PARTIAL", "UNRELATED", "AMBIGUOUS"}
REVIEW_FIELDS = {
    "claim_id",
    "evidence_id",
    "relation",
    "claim_fragment",
    "evidence_fragment",
    "missing_bridge",
}
OPTIONAL_REVIEW_FIELDS = {"reviewer_id"}
FORBIDDEN_REVIEW_FIELDS = {
    "confidence",
    "probability",
    "truth_score",
    "reliability_score",
    "source_reliability_score",
    "high_medium_low",
}
ADVERSARIAL_REVIEW_FIELDS = {
    "claim_id",
    "evidence_id",
    "relation",
    "reviewer_id",
    "evidence_fragment",
    "strongest_counter_reading",
    "what_would_falsify",
}
ADVERSARIAL_POLICIES = ("off", "optional", "required")
_POLICY_RANK = {name: rank for rank, name in enumerate(ADVERSARIAL_POLICIES)}
_POLICY_BY_RANK = {rank: name for name, rank in _POLICY_RANK.items()}


def _missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def validate_payload_shape(payload: Any, compile_schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"status": "HOLD", "errors": ["input:must_be_object"]}
    errors: list[str] = []
    for key in compile_schema.get("required", []):
        if key not in payload:
            errors.append(f"input:missing:{key}")
    allowed = set(compile_schema.get("properties", {}))
    errors.extend(f"input:unknown_field:{key}" for key in sorted(set(payload) - allowed))
    if payload.get("domain") is not None and not isinstance(payload.get("domain"), str):
        errors.append("input:domain_must_be_string_or_null")
    if payload.get("claim_class") is not None and not isinstance(payload.get("claim_class"), str):
        errors.append("input:claim_class_must_be_string_or_null")
    if "protocol_inputs" in payload and not isinstance(payload.get("protocol_inputs"), dict):
        errors.append("input:protocol_inputs_must_be_object")
    return {"status": "PASS" if not errors else "HOLD", "errors": errors}


def validate_anchor(text: str, anchor: Any, path: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(anchor, dict):
        return [f"{path}:anchor_must_be_object"]
    if set(anchor) != {"text", "start", "end"}:
        errors.append(f"{path}:anchor_fields_must_be_text_start_end")
    start = anchor.get("start")
    end = anchor.get("end")
    fragment = anchor.get("text")
    if isinstance(start, bool) or not isinstance(start, int):
        errors.append(f"{path}:start_must_be_integer")
    if isinstance(end, bool) or not isinstance(end, int):
        errors.append(f"{path}:end_must_be_integer")
    if not isinstance(fragment, str):
        errors.append(f"{path}:text_must_be_string")
    if errors:
        return errors
    if start < 0 or end < start or end > len(text):
        return [f"{path}:anchor_out_of_bounds"]
    if text[start:end] != fragment:
        return [f"{path}:anchor_text_mismatch"]
    return []


def validate_claim_ir(
    ir: Any,
    claim_schema: dict[str, Any],
    high_impact_operators: set[str],
) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(ir, dict):
        return {"status": "HOLD", "errors": ["claim_ir:must_be_object"]}

    required = claim_schema.get("required", [])
    properties = claim_schema.get("properties", {})
    for key in required:
        if key not in ir or _missing(ir.get(key)) and key not in {"scope", "anchors"}:
            errors.append(f"claim_ir:missing:{key}")
    unknown = sorted(set(ir) - set(properties))
    errors.extend(f"claim_ir:unknown_field:{key}" for key in unknown)

    for key in ("claim_id", "source_text", "subject", "predicate"):
        if key in ir and (not isinstance(ir[key], str) or not ir[key].strip()):
            errors.append(f"claim_ir:{key}_must_be_nonempty_string")
    if "scope" in ir and not isinstance(ir.get("scope"), dict):
        errors.append("claim_ir:scope_must_be_object")
    if "anchors" in ir and not isinstance(ir.get("anchors"), dict):
        errors.append("claim_ir:anchors_must_be_object")

    for field in ("operator", "polarity", "quantifier", "modality"):
        allowed = set(properties.get(field, {}).get("enum", []))
        if ir.get(field) not in allowed:
            errors.append(f"claim_ir:invalid_{field}:{ir.get(field)}")

    source_text = ir.get("source_text") if isinstance(ir.get("source_text"), str) else ""
    anchors = ir.get("anchors") if isinstance(ir.get("anchors"), dict) else {}
    for slot, anchor in anchors.items():
        errors.extend(validate_anchor(source_text, anchor, f"claim_ir.anchors.{slot}"))

    required_anchors = {"subject", "predicate"}
    if ir.get("object") is not None:
        required_anchors.add("object")
    if ir.get("operator") in high_impact_operators:
        required_anchors.add("operator")
    if ir.get("quantifier") not in {None, "UNSPECIFIED"}:
        required_anchors.add("quantifier")
    if ir.get("modality") not in {None, "ASSERTED"}:
        required_anchors.add("modality")
    if isinstance(ir.get("scope"), dict) and ir.get("scope"):
        required_anchors.add("scope")
    for slot in sorted(required_anchors - set(anchors)):
        errors.append(f"claim_ir:missing_anchor:{slot}")

    return {"status": "PASS" if not errors else "HOLD", "errors": errors}


def validate_evidence(
    items: Any,
    evidence_schema: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    if not isinstance(items, list):
        return {"status": "HOLD", "errors": ["evidence:must_be_array"]}, {}

    evidence_by_id: dict[str, dict[str, Any]] = {}
    allowed_fields = set(evidence_schema.get("properties", {}))
    for index, item in enumerate(items):
        path = f"evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path}:must_be_object")
            continue
        errors.extend(
            f"{path}:unknown_field:{key}" for key in sorted(set(item) - allowed_fields)
        )
        for key in ("evidence_id", "source_id", "source_kind", "source_text", "quote"):
            if key not in item or _missing(item.get(key)):
                errors.append(f"{path}:missing:{key}")
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            errors.append(f"{path}:evidence_id_must_be_nonempty_string")
            continue
        if evidence_id in evidence_by_id:
            errors.append(f"{path}:duplicate_evidence_id:{evidence_id}")
            continue
        evidence_by_id[evidence_id] = item

        for key in ("source_id", "source_kind", "source_text"):
            if not isinstance(item.get(key), str) or not item.get(key, "").strip():
                errors.append(f"{path}:{key}_must_be_nonempty_string")
        source_text = item.get("source_text") if isinstance(item.get("source_text"), str) else ""
        errors.extend(validate_anchor(source_text, item.get("quote"), f"{path}.quote"))
        for key in ("derived_from", "cites"):
            value = item.get(key, [])
            if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
                errors.append(f"{path}:{key}_must_be_string_array")
        if "scope" in item and not isinstance(item.get("scope"), dict):
            errors.append(f"{path}:scope_must_be_object")
        for key in ("entities", "numbers"):
            if key in item and not isinstance(item.get(key), list):
                errors.append(f"{path}:{key}_must_be_array")
        for key in ("date", "version", "dataset_id"):
            if key in item and item.get(key) is not None and not isinstance(item.get(key), str):
                errors.append(f"{path}:{key}_must_be_string_or_null")

    known_source_ids = {
        item.get("source_id")
        for item in evidence_by_id.values()
        if isinstance(item.get("source_id"), str)
    }
    for evidence_id, item in evidence_by_id.items():
        for relation in ("derived_from", "cites"):
            for source_id in item.get(relation, []) or []:
                if source_id not in known_source_ids:
                    errors.append(
                        f"evidence:{evidence_id}:{relation}_unknown_source:{source_id}"
                    )

    return {"status": "PASS" if not errors else "HOLD", "errors": errors}, evidence_by_id


def validate_semantic_reviews(
    reviews: Any,
    ir: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[str] = []
    valid: list[dict[str, Any]] = []
    if not isinstance(reviews, list):
        return {"status": "HOLD", "errors": ["semantic_reviews:must_be_array"]}, []

    seen_evidence: set[str] = set()
    for index, review in enumerate(reviews):
        path = f"semantic_reviews[{index}]"
        local_errors: list[str] = []
        if not isinstance(review, dict):
            errors.append(f"{path}:must_be_object")
            continue
        missing = sorted(REVIEW_FIELDS - set(review))
        local_errors.extend(f"{path}:missing:{key}" for key in missing)
        extra = sorted(set(review) - REVIEW_FIELDS - OPTIONAL_REVIEW_FIELDS)
        local_errors.extend(f"{path}:unknown_or_forbidden_field:{key}" for key in extra)
        if "reviewer_id" in review:
            reviewer_id = review.get("reviewer_id")
            if not isinstance(reviewer_id, str) or not reviewer_id.strip():
                local_errors.append(f"{path}:empty_reviewer_id")
        local_errors.extend(
            f"{path}:forbidden_field:{key}"
            for key in sorted(set(review) & FORBIDDEN_REVIEW_FIELDS)
        )

        relation = review.get("relation")
        if relation not in ALLOWED_RELATIONS:
            local_errors.append(f"{path}:invalid_relation:{relation}")
        if review.get("claim_id") != ir.get("claim_id"):
            local_errors.append(f"{path}:claim_id_mismatch")
        evidence_id = review.get("evidence_id")
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            local_errors.append(f"{path}:unknown_evidence_id:{evidence_id}")
        elif evidence_id in seen_evidence:
            local_errors.append(f"{path}:duplicate_review_for_evidence:{evidence_id}")

        claim_fragment = review.get("claim_fragment")
        evidence_fragment = review.get("evidence_fragment")
        if not isinstance(claim_fragment, str) or not claim_fragment.strip():
            local_errors.append(f"{path}:empty_claim_fragment")
        elif claim_fragment not in ir.get("source_text", ""):
            local_errors.append(f"{path}:claim_fragment_not_literal")
        if not isinstance(evidence_fragment, str) or not evidence_fragment.strip():
            local_errors.append(f"{path}:empty_evidence_fragment")
        elif evidence is not None and evidence_fragment not in evidence.get("source_text", ""):
            local_errors.append(f"{path}:evidence_fragment_not_literal")

        bridge = review.get("missing_bridge")
        if not isinstance(bridge, str):
            local_errors.append(f"{path}:missing_bridge_must_be_string")
        elif relation == "ENTAILS" and bridge.strip():
            local_errors.append(f"{path}:entails_cannot_have_missing_bridge")
        elif relation in {"PARTIAL", "AMBIGUOUS"} and not bridge.strip():
            local_errors.append(f"{path}:{relation.lower()}_requires_missing_bridge")

        if local_errors:
            errors.extend(local_errors)
        else:
            valid.append(review)
            seen_evidence.add(evidence_id)

    counts = Counter(review["relation"] for review in valid)
    if not valid:
        errors.append("semantic_reviews:no_valid_reviews")

    entails = [r["evidence_id"] for r in valid if r["relation"] == "ENTAILS"]
    contradicts = [r["evidence_id"] for r in valid if r["relation"] == "CONTRADICTS"]
    partial_or_ambiguous = [
        r["evidence_id"]
        for r in valid
        if r["relation"] in {"PARTIAL", "AMBIGUOUS"}
    ]

    if errors:
        status = "HOLD"
        code = "INVALID_SEMANTIC_REVIEW"
    elif contradicts and entails:
        status = "HOLD"
        code = "SEMANTIC_CONFLICT"
    elif contradicts:
        status = "FAIL"
        code = "EVIDENCE_CONTRADICTS_CLAIM"
    elif entails and partial_or_ambiguous:
        status = "HOLD"
        code = "SEMANTIC_COVERAGE_CONFLICT"
    elif entails:
        status = "PASS"
        code = "ENTAILMENT_RECORDED"
    else:
        status = "HOLD"
        code = "NO_ENTAILING_EVIDENCE"

    summary = {
        "status": status,
        "code": code,
        "counts": {key: counts.get(key, 0) for key in sorted(ALLOWED_RELATIONS)},
        "entailing_evidence_ids": entails,
        "contradicting_evidence_ids": contradicts,
        "partial_or_ambiguous_evidence_ids": partial_or_ambiguous,
        "errors": errors,
    }
    return summary, valid


def validate_linked_values(
    name: str,
    values: Any,
    evidence_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    if values is None:
        values = {}
    if not isinstance(values, dict):
        return {"status": "HOLD", "errors": [f"{name}:must_be_object"], "plain": {}}
    plain: dict[str, Any] = {}
    for key, record in values.items():
        path = f"{name}.{key}"
        required_fields = {"value", "evidence_ids", "evidence_fragments"}
        if not isinstance(record, dict) or set(record) != required_fields:
            errors.append(f"{path}:must_contain_value_evidence_ids_and_fragments")
            continue
        evidence_ids = record.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            errors.append(f"{path}:evidence_ids_must_be_nonempty_array")
            continue
        unknown = [item for item in evidence_ids if item not in evidence_by_id]
        if unknown:
            errors.extend(f"{path}:unknown_evidence_id:{item}" for item in unknown)
            continue
        fragments = record.get("evidence_fragments")
        if not isinstance(fragments, dict) or set(fragments) != set(evidence_ids):
            errors.append(f"{path}:evidence_fragments_must_match_evidence_ids")
            continue
        fragment_errors = []
        for evidence_id, fragment in fragments.items():
            if (
                not isinstance(fragment, str)
                or not fragment.strip()
                or fragment not in evidence_by_id[evidence_id].get("source_text", "")
            ):
                fragment_errors.append(f"{path}:nonliteral_evidence_fragment:{evidence_id}")
        if fragment_errors:
            errors.extend(fragment_errors)
            continue
        plain[key] = record.get("value")
    return {"status": "PASS" if not errors else "HOLD", "errors": errors, "plain": plain}


def validate_exceptions(
    exceptions: Any,
    evidence_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    valid: list[dict[str, Any]] = []
    if exceptions is None:
        exceptions = []
    if not isinstance(exceptions, list):
        return {"status": "HOLD", "errors": ["verified_exceptions:must_be_array"], "valid": []}
    for index, item in enumerate(exceptions):
        path = f"verified_exceptions[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path}:must_be_object")
            continue
        if set(item) != {"text", "evidence_id", "quote"}:
            errors.append(f"{path}:unknown_field")
        if not isinstance(item.get("text"), str) or not item.get("text", "").strip():
            errors.append(f"{path}:text_must_be_nonempty_string")
        evidence = evidence_by_id.get(item.get("evidence_id"))
        if evidence is None:
            errors.append(f"{path}:unknown_evidence_id:{item.get('evidence_id')}")
            continue
        if "quote" not in item:
            errors.append(f"{path}:quote_required")
        else:
            errors.extend(validate_anchor(evidence.get("source_text", ""), item["quote"], f"{path}.quote"))
        if not errors or not any(error.startswith(path) for error in errors):
            valid.append(item)
    return {"status": "PASS" if not errors else "HOLD", "errors": errors, "valid": valid}


def validate_components(
    components: Any,
    ir: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
    valid_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    valid: list[dict[str, Any]] = []
    if components is None:
        components = []
    if not isinstance(components, list):
        return {"status": "HOLD", "errors": ["supported_components:must_be_array"], "valid": []}
    support_reviews = {
        r["evidence_id"]: r
        for r in valid_reviews
        if r["relation"] in {"ENTAILS", "PARTIAL"}
    }
    seen: set[str] = set()
    for index, item in enumerate(components):
        path = f"supported_components[{index}]"
        local: list[str] = []
        if not isinstance(item, dict):
            errors.append(f"{path}:must_be_object")
            continue
        required = {"component_id", "text", "claim_fragment", "evidence_ids"}
        for key in sorted(required - set(item)):
            local.append(f"{path}:missing:{key}")
        if set(item) - required:
            local.append(f"{path}:unknown_field")
        component_id = item.get("component_id")
        if not isinstance(component_id, str) or not component_id.strip():
            local.append(f"{path}:component_id_must_be_nonempty_string")
        elif component_id in seen:
            local.append(f"{path}:duplicate_component_id:{component_id}")
        claim_fragment = item.get("claim_fragment")
        if not isinstance(item.get("text"), str) or not item.get("text", "").strip():
            local.append(f"{path}:text_must_be_nonempty_string")
        if not isinstance(claim_fragment, str) or claim_fragment not in ir.get("source_text", ""):
            local.append(f"{path}:claim_fragment_not_literal")
        evidence_ids = item.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            local.append(f"{path}:evidence_ids_must_be_nonempty_array")
        else:
            for evidence_id in evidence_ids:
                if evidence_id not in evidence_by_id:
                    local.append(f"{path}:unknown_evidence_id:{evidence_id}")
                elif evidence_id not in support_reviews:
                    local.append(f"{path}:evidence_not_supporting_component:{evidence_id}")
                elif isinstance(claim_fragment, str) and claim_fragment not in support_reviews[evidence_id].get("claim_fragment", ""):
                    local.append(f"{path}:component_not_within_reviewed_claim_fragment:{evidence_id}")
        if local:
            errors.extend(local)
        else:
            valid.append(item)
            seen.add(component_id)
    return {"status": "PASS" if not errors else "HOLD", "errors": errors, "valid": valid}


def classify_source_authority(
    domain: Any,
    claim_class: Any,
    evidence_by_id: dict[str, dict[str, Any]],
    valid_reviews: list[dict[str, Any]],
    registry: dict[str, Any],
) -> dict[str, Any]:
    domains = registry.get("domains", {})
    if domain is not None and domain not in domains:
        return {
            "status": "HOLD",
            "code": "UNKNOWN_DOMAIN",
            "domain": domain,
            "claim_class": claim_class,
            "by_evidence": {},
            "appropriate_evidence_ids": [],
            "insufficient_evidence_ids": [],
            "unclassified_evidence_ids": [],
        }
    domain_rules = domains.get(domain, registry.get("default", {}))
    if claim_class is not None:
        claim_classes = domain_rules.get("claim_classes", {})
        if claim_class not in claim_classes:
            return {
                "status": "HOLD",
                "code": "UNKNOWN_CLAIM_CLASS",
                "domain": domain,
                "claim_class": claim_class,
                "by_evidence": {},
                "appropriate_evidence_ids": [],
                "insufficient_evidence_ids": [],
                "unclassified_evidence_ids": sorted(evidence_by_id),
            }
        rules = claim_classes[claim_class]
    else:
        rules = domain_rules
    preferred = set(rules.get("preferred_sources", []))
    insufficient = set(rules.get("insufficient_as_sole_source", []))
    reviewed_ids = set(evidence_by_id)
    by_evidence: dict[str, str] = {}
    appropriate: list[str] = []
    weak: list[str] = []
    unknown: list[str] = []
    for evidence_id in sorted(reviewed_ids):
        source_kind = evidence_by_id[evidence_id].get("source_kind")
        if source_kind in preferred:
            by_evidence[evidence_id] = "APPROPRIATE"
            appropriate.append(evidence_id)
        elif source_kind in insufficient:
            by_evidence[evidence_id] = "INSUFFICIENT_AS_SOLE_SOURCE"
            weak.append(evidence_id)
        else:
            by_evidence[evidence_id] = "UNCLASSIFIED"
            unknown.append(evidence_id)
    if appropriate:
        status, code = "PASS", "APPROPRIATE_SOURCE_PRESENT"
    else:
        status, code = "HOLD", "NO_APPROPRIATE_SOURCE"
    return {
        "status": status,
        "code": code,
        "domain": domain,
        "claim_class": claim_class,
        "by_evidence": by_evidence,
        "appropriate_evidence_ids": appropriate,
        "insufficient_evidence_ids": weak,
        "unclassified_evidence_ids": unknown,
    }


def resolve_adversarial_policy(payload_value: Any, host_value: Any) -> tuple[str, list[str]]:
    """Resolve the effective adversarial policy.

    The strictest supplied value wins, so a payload can never relax a policy the
    host environment requires. Absent both, the default is ``optional``.
    """
    errors: list[str] = []
    ranks: list[int] = []
    for label, value in (("payload", payload_value), ("host", host_value)):
        if value is None:
            continue
        if not isinstance(value, str) or value not in ADVERSARIAL_POLICIES:
            errors.append(f"adversarial_policy:invalid_{label}_value:{value}")
            continue
        ranks.append(_POLICY_RANK[value])
    resolved = _POLICY_BY_RANK[max(ranks)] if ranks else "optional"
    return resolved, errors


def _adversarial_summary(policy: str, status: str, code: str, **extra: Any) -> dict[str, Any]:
    summary = {
        "status": status,
        "code": code,
        "policy": policy,
        "reviewer_ids": [],
        "reviewed_evidence_ids": [],
        "unreviewed_evidence_ids": [],
        "disagreements": [],
        "falsifiers": [],
        "errors": [],
    }
    summary.update(extra)
    return summary


def validate_adversarial_reviews(
    reviews: Any,
    ir: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
    semantic_reviews: list[dict[str, Any]],
    policy: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Check an independent second pass over the same claim and evidence.

    The runtime never judges which reviewer is right. It only checks that a
    second reviewer exists, is a different reviewer, anchored its reading in the
    same evidence text, and reached the same relation. Disagreement is an
    unresolved state, not a verdict.
    """
    if policy == "off":
        return _adversarial_summary(policy, "SKIPPED", "ADVERSARIAL_REVIEW_DISABLED"), []
    if reviews is None:
        if policy == "required":
            return _adversarial_summary(policy, "HOLD", "ADVERSARIAL_REVIEW_REQUIRED"), []
        return _adversarial_summary(policy, "SKIPPED", "ADVERSARIAL_REVIEW_NOT_SUPPLIED"), []
    if not isinstance(reviews, list):
        return (
            _adversarial_summary(
                policy,
                "HOLD",
                "INVALID_ADVERSARIAL_REVIEW",
                errors=["adversarial_reviews:must_be_array"],
            ),
            [],
        )

    errors: list[str] = []
    valid: list[dict[str, Any]] = []
    seen_evidence: set[str] = set()
    for index, review in enumerate(reviews):
        path = f"adversarial_reviews[{index}]"
        if not isinstance(review, dict):
            errors.append(f"{path}:must_be_object")
            continue
        local_errors: list[str] = []
        local_errors.extend(
            f"{path}:missing:{key}"
            for key in sorted(ADVERSARIAL_REVIEW_FIELDS - set(review))
        )
        local_errors.extend(
            f"{path}:unknown_or_forbidden_field:{key}"
            for key in sorted(set(review) - ADVERSARIAL_REVIEW_FIELDS)
        )
        local_errors.extend(
            f"{path}:forbidden_field:{key}"
            for key in sorted(set(review) & FORBIDDEN_REVIEW_FIELDS)
        )

        if review.get("relation") not in ALLOWED_RELATIONS:
            local_errors.append(f"{path}:invalid_relation:{review.get('relation')}")
        if review.get("claim_id") != ir.get("claim_id"):
            local_errors.append(f"{path}:claim_id_mismatch")

        evidence_id = review.get("evidence_id")
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            local_errors.append(f"{path}:unknown_evidence_id:{evidence_id}")
        elif evidence_id in seen_evidence:
            local_errors.append(f"{path}:duplicate_review_for_evidence:{evidence_id}")

        reviewer_id = review.get("reviewer_id")
        if not isinstance(reviewer_id, str) or not reviewer_id.strip():
            local_errors.append(f"{path}:empty_reviewer_id")

        fragment = review.get("evidence_fragment")
        if not isinstance(fragment, str) or not fragment.strip():
            local_errors.append(f"{path}:empty_evidence_fragment")
        elif evidence is not None and fragment not in evidence.get("source_text", ""):
            local_errors.append(f"{path}:evidence_fragment_not_literal")

        for key in ("strongest_counter_reading", "what_would_falsify"):
            value = review.get(key)
            if not isinstance(value, str) or not value.strip():
                local_errors.append(f"{path}:empty_{key}")

        if local_errors:
            errors.extend(local_errors)
        else:
            valid.append(review)
            seen_evidence.add(evidence_id)

    by_evidence = {review["evidence_id"]: review for review in valid}
    first_pass = {
        review["evidence_id"]: review
        for review in semantic_reviews
        if isinstance(review, dict) and isinstance(review.get("evidence_id"), str)
    }

    disagreements: list[dict[str, Any]] = []
    unreviewed: list[str] = []
    for evidence_id in sorted(first_pass):
        original = first_pass[evidence_id]
        counter = by_evidence.get(evidence_id)
        if counter is None:
            unreviewed.append(evidence_id)
            continue
        original_reviewer = original.get("reviewer_id")
        if isinstance(original_reviewer, str) and original_reviewer.strip():
            if original_reviewer == counter["reviewer_id"]:
                errors.append(
                    f"adversarial_reviews:reviewer_not_independent:{evidence_id}"
                )
        elif policy == "required":
            errors.append(f"semantic_reviews:missing_reviewer_id:{evidence_id}")
        if original.get("relation") != counter.get("relation"):
            disagreements.append(
                {
                    "evidence_id": evidence_id,
                    "first_pass_relation": original.get("relation"),
                    "adversarial_relation": counter.get("relation"),
                    "adversarial_reviewer_id": counter.get("reviewer_id"),
                    "strongest_counter_reading": counter.get("strongest_counter_reading"),
                }
            )

    errors.extend(
        f"adversarial_reviews:no_matching_semantic_review:{evidence_id}"
        for evidence_id in sorted(set(by_evidence) - set(first_pass))
    )

    summary = _adversarial_summary(
        policy,
        "PASS",
        "INDEPENDENT_REVIEW_AGREES",
        reviewer_ids=sorted({review["reviewer_id"] for review in valid}),
        reviewed_evidence_ids=sorted(by_evidence),
        unreviewed_evidence_ids=unreviewed,
        disagreements=disagreements,
        falsifiers=[
            {
                "evidence_id": review["evidence_id"],
                "what_would_falsify": review["what_would_falsify"],
            }
            for review in sorted(valid, key=lambda item: item["evidence_id"])
        ],
        errors=sorted(set(errors)),
    )

    if summary["errors"]:
        summary["status"], summary["code"] = "HOLD", "INVALID_ADVERSARIAL_REVIEW"
    elif disagreements:
        summary["status"], summary["code"] = "HOLD", "REVIEWER_DISAGREEMENT"
    elif policy == "required" and unreviewed:
        summary["status"], summary["code"] = "HOLD", "ADVERSARIAL_REVIEW_INCOMPLETE"
    elif not valid:
        if policy == "required":
            summary["status"], summary["code"] = "HOLD", "ADVERSARIAL_REVIEW_REQUIRED"
        else:
            summary["status"], summary["code"] = "SKIPPED", "ADVERSARIAL_REVIEW_NOT_SUPPLIED"
    return summary, valid


def resolve_policy(payload_value: Any, host_value: Any, name: str) -> tuple[str, list[str]]:
    """Resolve a three-state policy. The strictest supplied value wins.

    A payload can never relax a policy the host environment requires, which is
    what makes an environment variable a usable enforcement point.
    """
    errors: list[str] = []
    ranks: list[int] = []
    for label, value in (("payload", payload_value), ("host", host_value)):
        if value is None:
            continue
        if not isinstance(value, str) or value not in ADVERSARIAL_POLICIES:
            errors.append(f"{name}:invalid_{label}_value:{value}")
            continue
        ranks.append(_POLICY_RANK[value])
    return (_POLICY_BY_RANK[max(ranks)] if ranks else "optional"), errors


def _split_locator(locator: str) -> tuple[str, str] | None:
    from urllib.parse import urlsplit

    parts = urlsplit(locator.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    host = parts.netloc.split("@")[-1].split(":")[0].lower()
    if host.startswith("www."):
        host = host[4:]
    return host, parts.path or "/"


def classify_locator(locator: Any, registry: dict[str, Any]) -> dict[str, Any]:
    """Work out which roles a locator can legitimately support.

    An unknown host is reported as unverifiable. Guessing in either direction
    would be worse than saying so.
    """
    if not isinstance(locator, str) or not locator.strip():
        return {"status": "UNVERIFIABLE", "code": "NO_LOCATOR", "permits": None}
    split = _split_locator(locator)
    if split is None:
        return {"status": "UNVERIFIABLE", "code": "NOT_AN_HTTP_LOCATOR", "permits": None}
    host, path = split

    best: dict[str, Any] | None = None
    best_key = (-1, -1)
    for rule in registry.get("rules", []):
        suffix = rule.get("host_suffix")
        if not suffix:
            continue
        suffix = suffix.lower().lstrip(".")
        if host != suffix and not host.endswith("." + suffix):
            continue
        prefix = rule.get("path_prefix")
        if prefix and not path.startswith(prefix):
            continue
        key = (len(suffix), len(prefix or ""))
        if key > best_key:
            best, best_key = rule, key

    if best is None:
        return {
            "status": "UNVERIFIABLE",
            "code": "UNKNOWN_HOST",
            "host": host,
            "permits": None,
        }

    permits = list(best.get("permits", []))
    applied: list[str] = []
    for demotion in registry.get("demotions", []):
        needle = demotion.get("path_contains")
        if needle and needle in path and demotion.get("remove"):
            removed = [item for item in demotion["remove"] if item in permits]
            if removed:
                permits = [item for item in permits if item not in removed]
                applied.append(demotion.get("reason", needle))
    return {
        "status": "CLASSIFIED",
        "code": "LOCATOR_CLASSIFIED",
        "host": host,
        "rule": best.get("label"),
        "permits": sorted(permits),
        "demotions_applied": applied,
    }


def validate_locator_authority(
    evidence: list[dict[str, Any]],
    registry: dict[str, Any],
    policy: str,
) -> dict[str, Any]:
    """Check declared source_kind against what the locator can actually support."""
    summary = {
        "status": "SKIPPED",
        "code": "LOCATOR_CHECK_DISABLED",
        "policy": policy,
        "by_evidence": {},
        "violations": [],
        "unverifiable_evidence_ids": [],
        "errors": [],
    }
    if policy == "off":
        return summary

    class_of: dict[str, str] = {}
    for name, kinds in registry.get("kind_classes", {}).items():
        for kind in kinds:
            class_of[kind] = name

    checked = 0
    for item in evidence:
        if not isinstance(item, dict):
            continue
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str):
            continue
        verdict = classify_locator(item.get("locator"), registry)
        kind = item.get("source_kind")
        declared_class = class_of.get(kind)
        entry = {
            "locator_status": verdict["status"],
            "locator_code": verdict["code"],
            "source_kind": kind,
            "declared_class": declared_class,
            "permits": verdict.get("permits"),
            "rule": verdict.get("rule"),
        }
        if verdict["status"] != "CLASSIFIED":
            summary["unverifiable_evidence_ids"].append(evidence_id)
            entry["verdict"] = "UNVERIFIABLE"
        elif declared_class is None:
            summary["errors"].append(
                f"locator_authority:unclassified_source_kind:{evidence_id}:{kind}"
            )
            entry["verdict"] = "UNCLASSIFIED_KIND"
        elif declared_class not in (verdict.get("permits") or []):
            summary["violations"].append(
                {
                    "evidence_id": evidence_id,
                    "source_kind": kind,
                    "declared_class": declared_class,
                    "locator_permits": verdict.get("permits"),
                    "rule": verdict.get("rule"),
                }
            )
            entry["verdict"] = "CONTRADICTED_BY_LOCATOR"
            checked += 1
        else:
            entry["verdict"] = "CONSISTENT"
            checked += 1
        summary["by_evidence"][evidence_id] = entry

    summary["unverifiable_evidence_ids"] = sorted(summary["unverifiable_evidence_ids"])
    summary["errors"] = sorted(set(summary["errors"]))
    if summary["errors"]:
        summary["status"], summary["code"] = "HOLD", "INVALID_LOCATOR_INPUT"
    elif summary["violations"]:
        summary["status"], summary["code"] = "HOLD", "SOURCE_KIND_CONTRADICTED_BY_LOCATOR"
    elif policy == "required" and summary["unverifiable_evidence_ids"]:
        summary["status"], summary["code"] = "HOLD", "LOCATOR_NOT_VERIFIABLE"
    elif checked:
        summary["status"], summary["code"] = "PASS", "LOCATOR_SUPPORTS_DECLARED_ROLE"
    else:
        summary["status"], summary["code"] = "SKIPPED", "NO_LOCATOR_SUPPLIED"
    return summary


def validate_snapshots(
    evidence: list[dict[str, Any]],
    snapshot_root: Any,
    policy: str,
) -> dict[str, Any]:
    """Verify that quoted source_text really came out of the captured bytes.

    Without this the whole anchor chain terminates at a summary somebody wrote,
    not at the page it claims to quote.
    """
    import hashlib
    from pathlib import Path

    summary = {
        "status": "SKIPPED",
        "code": "SNAPSHOT_CHECK_DISABLED",
        "policy": policy,
        "by_evidence": {},
        "unsnapshotted_evidence_ids": [],
        "errors": [],
    }
    if policy == "off":
        return summary

    root = Path(snapshot_root).resolve() if snapshot_root else None
    verified = 0
    for item in evidence:
        if not isinstance(item, dict):
            continue
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str):
            continue
        snapshot = item.get("snapshot")
        if snapshot is None:
            summary["unsnapshotted_evidence_ids"].append(evidence_id)
            continue
        path_key = f"snapshot:{evidence_id}"
        if not isinstance(snapshot, dict) or set(snapshot) != {"path", "sha256"}:
            summary["errors"].append(f"{path_key}:fields_must_be_path_and_sha256")
            continue
        relative = snapshot.get("path")
        digest = snapshot.get("sha256")
        if not isinstance(relative, str) or not relative.strip():
            summary["errors"].append(f"{path_key}:path_must_be_nonempty_string")
            continue
        if not isinstance(digest, str) or len(digest) != 64:
            summary["errors"].append(f"{path_key}:sha256_must_be_64_hex_chars")
            continue
        if root is None:
            summary["errors"].append(f"{path_key}:no_snapshot_root_configured")
            continue
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            summary["errors"].append(f"{path_key}:path_escapes_snapshot_root")
            continue
        try:
            raw = candidate.read_bytes()
        except OSError:
            summary["errors"].append(f"{path_key}:file_not_found:{relative}")
            continue
        actual = hashlib.sha256(raw).hexdigest()
        if actual != digest:
            summary["errors"].append(f"{path_key}:sha256_mismatch")
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            summary["errors"].append(f"{path_key}:snapshot_not_utf8")
            continue
        source_text = item.get("source_text")
        if not isinstance(source_text, str) or source_text not in text:
            summary["errors"].append(f"{path_key}:source_text_not_in_snapshot")
            continue
        summary["by_evidence"][evidence_id] = {
            "path": relative,
            "sha256": digest,
            "verdict": "SOURCE_TEXT_FOUND_IN_CAPTURED_BYTES",
        }
        verified += 1

    summary["unsnapshotted_evidence_ids"] = sorted(summary["unsnapshotted_evidence_ids"])
    summary["errors"] = sorted(set(summary["errors"]))
    if summary["errors"]:
        summary["status"], summary["code"] = "HOLD", "SNAPSHOT_VERIFICATION_FAILED"
    elif policy == "required" and summary["unsnapshotted_evidence_ids"]:
        summary["status"], summary["code"] = "HOLD", "SNAPSHOT_REQUIRED"
    elif verified:
        summary["status"], summary["code"] = "PASS", "QUOTED_TEXT_MATCHES_CAPTURE"
    else:
        summary["status"], summary["code"] = "SKIPPED", "NO_SNAPSHOT_SUPPLIED"
    return summary
