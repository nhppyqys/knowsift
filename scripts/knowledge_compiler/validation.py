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
FORBIDDEN_REVIEW_FIELDS = {
    "confidence",
    "probability",
    "truth_score",
    "reliability_score",
    "source_reliability_score",
    "high_medium_low",
}


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
        extra = sorted(set(review) - REVIEW_FIELDS)
        local_errors.extend(f"{path}:unknown_or_forbidden_field:{key}" for key in extra)
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
