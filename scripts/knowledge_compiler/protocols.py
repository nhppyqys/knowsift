"""Protocol routing and deterministic validators."""

from __future__ import annotations

import math
from typing import Any, Callable


def _result(
    status: str,
    code: str,
    *,
    missing: list[str] | None = None,
    details: dict[str, Any] | None = None,
    derived: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status, "code": code, "missing": missing or []}
    if details is not None:
        result["details"] = details
    if derived is not None:
        result["derived"] = derived
    return result


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _is_finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _reference_errors(evidence_ids: Any, evidence_by_id: dict[str, Any], field: str) -> list[str]:
    if not isinstance(evidence_ids, list) or not evidence_ids:
        return [f"{field}:nonempty_evidence_ids_required"]
    return [f"{field}:unknown_evidence_id:{item}" for item in evidence_ids if item not in evidence_by_id]


def _fragment_errors(
    evidence_ids: Any,
    fragments: Any,
    evidence_by_id: dict[str, Any],
    field: str,
) -> list[str]:
    if not isinstance(evidence_ids, list) or not evidence_ids:
        return [f"{field}:nonempty_evidence_ids_required"]
    if not isinstance(fragments, dict) or set(fragments) != set(evidence_ids):
        return [f"{field}:evidence_fragments_must_match_evidence_ids"]
    errors: list[str] = []
    for evidence_id, fragment in fragments.items():
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            errors.append(f"{field}:unknown_evidence_id:{evidence_id}")
        elif not isinstance(fragment, str) or not fragment or fragment not in evidence.get("source_text", ""):
            errors.append(f"{field}:nonliteral_evidence_fragment:{evidence_id}")
    return errors


def _appropriate_entailing_ids(context: dict[str, Any]) -> set[str]:
    entails = set(context["semantic_summary"].get("entailing_evidence_ids", []))
    appropriate = set(context["source_authority"].get("appropriate_evidence_ids", []))
    return entails & appropriate


def _appropriate_supporting_ids(context: dict[str, Any]) -> set[str]:
    supporting = {
        review["evidence_id"]
        for review in context.get("valid_reviews", [])
        if review.get("relation") in {"ENTAILS", "PARTIAL"}
    }
    appropriate = set(context["source_authority"].get("appropriate_evidence_ids", []))
    return supporting & appropriate


def route_protocols(
    payload: dict[str, Any],
    protocol_registry: dict[str, Any],
    domain_registry: dict[str, Any],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    ir = payload.get("claim_ir") if isinstance(payload.get("claim_ir"), dict) else {}
    operator = ir.get("operator")
    routes = protocol_registry.get("base_routes", {})
    protocols = list(routes.get(operator, []))
    if not protocols:
        errors.append(f"routing:no_base_route:{operator}")

    if ir.get("quantifier") in set(protocol_registry.get("generalizing_quantifiers", [])):
        protocols.append("GENERALIZATION")

    domain = payload.get("domain")
    domains = domain_registry.get("domains", {})
    if domain in domains:
        domain_config = domains[domain]
        protocols.extend(domain_config.get("required_protocols", []))
        if domain_config.get("version_sensitive") is True:
            protocols.append("VERSIONED_TECHNICAL_SPEC")

    protocol_inputs = payload.get("protocol_inputs")
    if not isinstance(protocol_inputs, dict):
        protocol_inputs = {}
    for input_key, protocol in protocol_registry.get("input_augmentations", {}).items():
        if input_key in protocol_inputs:
            protocols.append(protocol)

    deduplicated: list[str] = []
    for protocol in protocols:
        if protocol not in deduplicated:
            deduplicated.append(protocol)
    known = set(protocol_registry.get("protocols", {}))
    for protocol in deduplicated:
        if protocol not in known:
            errors.append(f"routing:unregistered_protocol:{protocol}")
    return deduplicated, errors


def validate_semantic_evidence(context: dict[str, Any], _: Any) -> dict[str, Any]:
    semantic = context["semantic_summary"]
    appropriate_entails = _appropriate_entailing_ids(context)
    appropriate = set(context["source_authority"].get("appropriate_evidence_ids", []))
    appropriate_contradictions = appropriate & set(semantic.get("contradicting_evidence_ids", []))
    if semantic.get("status") == "FAIL" and appropriate_contradictions:
        return _result("FAIL", "APPROPRIATE_EVIDENCE_CONTRADICTS_CLAIM")
    if semantic.get("status") != "PASS":
        return _result("HOLD", "SEMANTIC_SUPPORT_UNRESOLVED")
    if not appropriate_entails:
        return _result("HOLD", "NO_APPROPRIATE_ENTAILING_EVIDENCE")
    return _result(
        "PASS",
        "TRACEABLE_SEMANTIC_SUPPORT",
        details={"evidence_ids": sorted(appropriate_entails)},
    )


def validate_scope_boundary(context: dict[str, Any], _: Any) -> dict[str, Any]:
    claim_scope = context["ir"].get("scope") or {}
    verified_scope = context["verified_scope"]
    if not claim_scope:
        return _result("PASS", "NO_EXPLICIT_CLAIM_SCOPE")

    appropriate_entails = _appropriate_entailing_ids(context)
    unverified: list[str] = []
    mismatched: list[str] = []
    for key, value in claim_scope.items():
        if key in verified_scope:
            if verified_scope[key] != value:
                mismatched.append(key)
            continue
        evidence_match = any(
            (context["evidence_by_id"][evidence_id].get("scope") or {}).get(key) == value
            for evidence_id in appropriate_entails
        )
        if not evidence_match:
            unverified.append(key)
    if mismatched:
        return _result(
            "PASS_SCOPED",
            "CLAIM_SCOPE_NARROWED_TO_VERIFIED_SCOPE",
            details={"mismatched_fields": sorted(mismatched)},
        )
    if unverified:
        return _result(
            "HOLD",
            "CLAIM_SCOPE_NOT_VERIFIED",
            missing=[f"verified_scope.{key}" for key in sorted(unverified)],
        )
    return _result("PASS", "CLAIM_SCOPE_VERIFIED")


def validate_generalization(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        missing = [
            key
            for key in ("target_scope", "observed_scopes", "transport_basis")
            if _is_missing(data.get(key))
        ]
        basis = data.get("transport_basis")
        if isinstance(basis, dict):
            if _is_missing(basis.get("method")):
                missing.append("transport_basis.method")
            missing.extend(
                _fragment_errors(
                    basis.get("evidence_ids"),
                    basis.get("evidence_fragments"),
                    context["evidence_by_id"],
                    "transport_basis",
                )
            )
        elif "transport_basis" not in missing:
            missing.append("transport_basis")
        if not missing:
            return _result("PASS", "GENERALIZATION_BASIS_TRACEABLE")
    if context["verified_scope"]:
        return _result(
            "PASS_SCOPED",
            "UNSUPPORTED_GENERALIZATION_REMOVED",
            details={"verified_scope": context["verified_scope"]},
        )
    return _result(
        "HOLD",
        "GENERALIZATION_UNSUPPORTED_AND_NO_SAFE_SCOPE",
        missing=["generalization.transport_basis_or_verified_scope"],
    )


def validate_versioned_technical_spec(context: dict[str, Any], data: Any) -> dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    version = data.get("version")
    if _is_missing(version):
        version = context["verified_scope"].get("version")
    if _is_missing(version):
        version = (context["ir"].get("scope") or {}).get("version")
    if _is_missing(version):
        return _result("HOLD", "VERSION_REQUIRED", missing=["version"])

    evidence_ids = data.get("evidence_ids") or sorted(_appropriate_supporting_ids(context))
    errors = _reference_errors(evidence_ids, context["evidence_by_id"], "versioned_technical_spec")
    if errors:
        return _result("HOLD", "VERSION_EVIDENCE_INVALID", missing=errors)
    matches = []
    for evidence_id in evidence_ids:
        evidence = context["evidence_by_id"][evidence_id]
        evidence_version = evidence.get("version")
        if evidence_version is None:
            evidence_version = (evidence.get("scope") or {}).get("version")
        if str(evidence_version) == str(version):
            matches.append(evidence_id)
    if not matches:
        return _result("HOLD", "VERSION_NOT_MATCHED_BY_EVIDENCE", missing=[str(version)])
    if not (set(matches) & _appropriate_supporting_ids(context)):
        return _result("HOLD", "VERSION_SOURCE_NOT_APPROPRIATE_AND_SUPPORTING")
    return _result("PASS", "VERSION_MATCHED", details={"version": version, "evidence_ids": matches})


def validate_formal_proof(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _result("HOLD", "FORMAL_PROOF_INPUT_REQUIRED", missing=["formal_proof"])
    missing = [key for key in ("method", "artifact_reference", "result") if _is_missing(data.get(key))]
    missing.extend(_reference_errors(data.get("evidence_ids"), context["evidence_by_id"], "formal_proof"))
    if missing:
        return _result("HOLD", "FORMAL_PROOF_NOT_TRACEABLE", missing=missing)
    if data.get("result") != "PASS":
        return _result("FAIL", "FORMAL_CHECK_DID_NOT_PASS")
    return _result("PASS", "FORMAL_CHECK_PASSED", details={"method": data["method"]})


def validate_legal_authority(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _result("HOLD", "LEGAL_AUTHORITY_INPUT_REQUIRED", missing=["legal_authority"])
    required = ("jurisdiction", "authority_type", "citation", "effective_date_or_version", "operative_evidence_id")
    missing = [key for key in required if _is_missing(data.get(key))]
    evidence_id = data.get("operative_evidence_id")
    if evidence_id and evidence_id not in context["evidence_by_id"]:
        missing.append(f"unknown_evidence_id:{evidence_id}")
    if missing:
        return _result("HOLD", "LEGAL_AUTHORITY_UNRESOLVED", missing=missing)
    if evidence_id not in _appropriate_entailing_ids(context):
        return _result("HOLD", "OPERATIVE_AUTHORITY_NOT_APPROPRIATE_AND_ENTAILING")
    if context["verified_exceptions"] and context["ir"].get("quantifier") in {"ALL", "NONE"}:
        return _result("PASS_SCOPED", "LEGAL_EXCEPTIONS_REQUIRE_NARROWING")
    return _result("PASS", "LEGAL_AUTHORITY_TRACEABLE")


def validate_statistical_inference(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _result("HOLD", "STATISTICAL_INPUT_REQUIRED", missing=["statistical_inference"])
    missing = [key for key in ("effect_measure", "estimate", "comparison") if _is_missing(data.get(key))]
    if not _is_missing(data.get("estimate")) and not _is_finite_number(data.get("estimate")):
        missing.append("finite_estimate")
    uncertainty_ok = False
    standard_error = data.get("standard_error")
    interval = data.get("confidence_interval")
    sample_size = data.get("sample_size")
    if _is_finite_number(standard_error) and standard_error > 0:
        uncertainty_ok = True
    if (
        isinstance(interval, list)
        and len(interval) == 2
        and all(_is_finite_number(value) for value in interval)
        and interval[0] <= interval[1]
    ):
        uncertainty_ok = True
    if _is_finite_number(sample_size) and sample_size > 0:
        uncertainty_ok = True
    if not uncertainty_ok:
        missing.append("standard_error_or_confidence_interval_or_sample_size")
    evidence_ids = data.get("evidence_ids") or sorted(_appropriate_entailing_ids(context))
    missing.extend(_reference_errors(evidence_ids, context["evidence_by_id"], "statistical_inference"))
    if missing:
        return _result("HOLD", "STATISTICAL_INFERENCE_INCOMPLETE", missing=missing)
    return _result(
        "PASS",
        "STATISTICAL_RECORD_TRACEABLE",
        derived={
            "effect_measure": data["effect_measure"],
            "estimate": data["estimate"],
            "comparison": data["comparison"],
        },
    )


def validate_causal_inference(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _result("HOLD", "CAUSAL_INPUT_REQUIRED", missing=["causal_inference"])
    design_type = data.get("design_type")
    design = context["causal_designs"].get(design_type)
    if design is None:
        return _result("HOLD", "UNKNOWN_CAUSAL_DESIGN", missing=["recognized_design_type"])
    record = data.get("record") if isinstance(data.get("record"), dict) else {}
    missing = [key for key in design["required_fields"] if _is_missing(record.get(key))]
    assumptions = data.get("assumptions") if isinstance(data.get("assumptions"), dict) else {}
    for name in design["required_assumptions"]:
        assumption = assumptions.get(name)
        if not isinstance(assumption, dict):
            missing.append(f"assumptions.{name}")
            continue
        if _is_missing(assumption.get("method")):
            missing.append(f"assumptions.{name}.method")
        evidence_id = assumption.get("evidence_id")
        evidence = context["evidence_by_id"].get(evidence_id)
        if evidence is None:
            missing.append(f"assumptions.{name}.known_evidence_id")
            continue
        fragment = assumption.get("evidence_fragment")
        if not isinstance(fragment, str) or not fragment or fragment not in evidence.get("source_text", ""):
            missing.append(f"assumptions.{name}.literal_evidence_fragment")
    if missing:
        return _result("HOLD", "CAUSAL_ASSUMPTIONS_UNRESOLVED", missing=sorted(set(missing)))
    return _result(
        "PASS",
        "CAUSAL_DESIGN_AND_ASSUMPTIONS_TRACEABLE",
        details={"design_type": design_type},
    )


def validate_predictive_validation(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _result("HOLD", "PREDICTIVE_INPUT_REQUIRED", missing=["predictive_validation"])
    required = ("metric", "baseline", "evaluation_scope", "out_of_sample")
    missing = [key for key in required if _is_missing(data.get(key))]
    if data.get("out_of_sample") is not True:
        missing.append("out_of_sample_true")
    missing.extend(_reference_errors(data.get("evidence_ids"), context["evidence_by_id"], "predictive_validation"))
    if missing:
        return _result("HOLD", "PREDICTIVE_VALIDATION_INCOMPLETE", missing=sorted(set(missing)))
    return _result("PASS", "OUT_OF_SAMPLE_VALIDATION_TRACEABLE")


def validate_prescriptive_decision(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _result("HOLD", "PRESCRIPTIVE_INPUT_REQUIRED", missing=["prescriptive_decision"])
    required = ("objective", "alternatives", "constraints", "tradeoffs")
    missing = [key for key in required if _is_missing(data.get(key))]
    if not isinstance(data.get("alternatives"), list) or len(data.get("alternatives", [])) < 2:
        missing.append("at_least_two_alternatives")
    missing.extend(_reference_errors(data.get("evidence_ids"), context["evidence_by_id"], "prescriptive_decision"))
    if missing:
        return _result("HOLD", "PRESCRIPTIVE_DECISION_INCOMPLETE", missing=sorted(set(missing)))
    return _result("PASS", "DECISION_INPUTS_TRACEABLE")


def validate_conditional_phenomenon(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _result("HOLD", "CONDITIONAL_INPUT_REQUIRED", missing=["conditional_phenomenon"])
    missing = [key for key in ("operational_outcome", "comparison_baseline") if _is_missing(data.get(key))]
    conditions = context["verified_conditions"]
    if _is_missing(conditions):
        missing.append("evidence_linked_verified_conditions")
    evidence_ids = data.get("evidence_ids") or sorted(_appropriate_entailing_ids(context))
    missing.extend(_reference_errors(evidence_ids, context["evidence_by_id"], "conditional_phenomenon"))
    if missing:
        return _result("HOLD", "CONDITIONAL_PHENOMENON_INCOMPLETE", missing=missing)
    return _result("PASS_SCOPED", "PHENOMENON_DEFINED_WITHIN_CONDITIONS")


def _fixed_effect(effects: list[float], variances: list[float]) -> dict[str, Any]:
    weights = [1.0 / value for value in variances]
    pooled = sum(weight * effect for weight, effect in zip(weights, effects)) / sum(weights)
    standard_error = math.sqrt(1.0 / sum(weights))
    q = sum(weight * ((effect - pooled) ** 2) for weight, effect in zip(weights, effects))
    degrees = len(effects) - 1
    i2 = max(0.0, (q - degrees) / q) if q > 0 else 0.0
    return {
        "model": "fixed_effect",
        "pooled": pooled,
        "standard_error": standard_error,
        "ci95": [pooled - 1.96 * standard_error, pooled + 1.96 * standard_error],
        "Q": q,
        "I2": i2,
    }


def _random_effects_dl(effects: list[float], variances: list[float]) -> dict[str, Any]:
    fixed = _fixed_effect(effects, variances)
    weights = [1.0 / value for value in variances]
    denominator = sum(weights) - sum(value * value for value in weights) / sum(weights)
    tau2 = max(0.0, (fixed["Q"] - (len(effects) - 1)) / denominator) if denominator > 0 else 0.0
    random_weights = [1.0 / (value + tau2) for value in variances]
    pooled = sum(weight * effect for weight, effect in zip(random_weights, effects)) / sum(random_weights)
    standard_error = math.sqrt(1.0 / sum(random_weights))
    return {
        "model": "random_effects_DL",
        "pooled": pooled,
        "standard_error": standard_error,
        "ci95": [pooled - 1.96 * standard_error, pooled + 1.96 * standard_error],
        "Q": fixed["Q"],
        "I2": fixed["I2"],
        "tau2": tau2,
    }


def validate_evidence_synthesis(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _result("HOLD", "SYNTHESIS_INPUT_REQUIRED", missing=["evidence_synthesis"])
    required = ("synthesis_type", "search_strategy", "inclusion_criteria", "study_records")
    missing = [key for key in required if _is_missing(data.get(key))]
    studies = data.get("study_records")
    if not isinstance(studies, list) or not studies:
        missing.append("nonempty_study_records")
    if missing:
        return _result("HOLD", "SYNTHESIS_NOT_REPRODUCIBLE", missing=sorted(set(missing)))
    synthesis_type = data.get("synthesis_type")
    if synthesis_type == "qualitative_systematic_review":
        if _is_missing(data.get("risk_of_bias_method")):
            return _result("HOLD", "SYNTHESIS_RISK_OF_BIAS_MISSING", missing=["risk_of_bias_method"])
        record_errors = []
        for index, record in enumerate(studies):
            evidence_id = record.get("evidence_id") if isinstance(record, dict) else None
            if evidence_id not in context["evidence_by_id"]:
                record_errors.append(f"study_records[{index}].known_evidence_id")
            elif context["source_authority"].get("by_evidence", {}).get(evidence_id) != "APPROPRIATE":
                record_errors.append(f"study_records[{index}].appropriate_source")
        if record_errors:
            return _result("HOLD", "SYNTHESIS_STUDY_RECORDS_INVALID", missing=record_errors)
        return _result("PASS", "QUALITATIVE_SYNTHESIS_TRACEABLE")
    if synthesis_type in {"diagnostic_meta_analysis", "network_meta_analysis"}:
        return _result("HOLD", "SPECIALIZED_SYNTHESIS_PROTOCOL_REQUIRED", missing=[synthesis_type])
    if synthesis_type not in {"fixed_effect_meta_analysis", "random_effects_meta_analysis"}:
        return _result("HOLD", "UNKNOWN_SYNTHESIS_TYPE", missing=["synthesis_type"])
    if len(studies) < 2:
        return _result("HOLD", "META_ANALYSIS_REQUIRES_MULTIPLE_STUDIES", missing=["at_least_two_studies"])

    effects: list[float] = []
    variances: list[float] = []
    record_errors: list[str] = []
    seen_study_ids: set[str] = set()
    seen_evidence_ids: set[str] = set()
    for index, record in enumerate(studies):
        path = f"study_records[{index}]"
        if not isinstance(record, dict):
            record_errors.append(path)
            continue
        study_id = record.get("study_id")
        evidence_id = record.get("evidence_id")
        effect = record.get("effect_estimate")
        variance = record.get("variance")
        if not isinstance(study_id, str) or not study_id or study_id in seen_study_ids:
            record_errors.append(f"{path}.unique_study_id")
        else:
            seen_study_ids.add(study_id)
        if evidence_id not in context["evidence_by_id"] or evidence_id in seen_evidence_ids:
            record_errors.append(f"{path}.unique_known_evidence_id")
        else:
            seen_evidence_ids.add(evidence_id)
            if context["source_authority"].get("by_evidence", {}).get(evidence_id) != "APPROPRIATE":
                record_errors.append(f"{path}.appropriate_source")
        if not _is_finite_number(effect):
            record_errors.append(f"{path}.finite_effect_estimate")
        if not _is_finite_number(variance) or variance <= 0:
            record_errors.append(f"{path}.positive_variance")
        if not record_errors or not any(error.startswith(path) for error in record_errors):
            effects.append(effect)
            variances.append(variance)
    if record_errors:
        return _result("HOLD", "META_ANALYSIS_NOT_RECOMPUTABLE", missing=record_errors)
    design_fields = ("effect_measure", "compatibility_method", "dependence_method", "model_choice_rationale")
    design_missing = [field for field in design_fields if _is_missing(data.get(field))]
    if design_missing:
        return _result("HOLD", "META_ANALYSIS_DESIGN_UNRESOLVED", missing=design_missing)
    derived = _fixed_effect(effects, variances)
    if synthesis_type == "random_effects_meta_analysis":
        derived = _random_effects_dl(effects, variances)
    return _result("PASS", "META_ANALYSIS_RECOMPUTED", derived=derived)


def validate_historical_source_criticism(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _result("HOLD", "HISTORICAL_INPUT_REQUIRED", missing=["historical_source_criticism"])
    event_year = data.get("event_year")
    records = data.get("source_records")
    missing: list[str] = []
    if isinstance(event_year, bool) or not isinstance(event_year, int):
        missing.append("integer_event_year")
    if not isinstance(records, list) or not records:
        missing.append("nonempty_source_records")
        records = []
    characterized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            missing.append(f"source_records[{index}]")
            continue
        evidence_id = record.get("evidence_id")
        source_year = record.get("source_year")
        document_type = record.get("document_type")
        if evidence_id not in context["evidence_by_id"]:
            missing.append(f"source_records[{index}].known_evidence_id")
        if isinstance(source_year, bool) or not isinstance(source_year, int):
            missing.append(f"source_records[{index}].integer_source_year")
        if _is_missing(document_type):
            missing.append(f"source_records[{index}].document_type")
        if isinstance(event_year, int) and not isinstance(event_year, bool) and isinstance(source_year, int) and not isinstance(source_year, bool):
            characterized.append(
                {
                    "evidence_id": evidence_id,
                    "temporal_distance_years": source_year - event_year,
                    "document_type": document_type,
                }
            )
    if missing:
        return _result("HOLD", "HISTORICAL_EVIDENCE_INCOMPLETE", missing=missing)
    return _result(
        "PASS",
        "HISTORICAL_EVIDENCE_CHARACTERIZED",
        derived={
            "sources": characterized,
            "independent_provenance_root_count": context["provenance"].get("independent_root_count", 0),
        },
    )


def validate_practitioner_heuristic(context: dict[str, Any], data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _result("HOLD", "PRACTITIONER_INPUT_REQUIRED", missing=["practitioner_heuristic"])
    missing = [key for key in ("context", "limitations") if _is_missing(data.get(key))]
    missing.extend(_reference_errors(data.get("evidence_ids"), context["evidence_by_id"], "practitioner_heuristic"))
    if missing:
        return _result("HOLD", "PRACTITIONER_HEURISTIC_INCOMPLETE", missing=missing)
    return _result("PASS_SCOPED", "PRACTITIONER_HEURISTIC_CONTEXT_BOUND")


VALIDATORS: dict[str, Callable[[dict[str, Any], Any], dict[str, Any]]] = {
    "semantic_evidence": validate_semantic_evidence,
    "scope_boundary": validate_scope_boundary,
    "generalization": validate_generalization,
    "versioned_technical_spec": validate_versioned_technical_spec,
    "formal_proof": validate_formal_proof,
    "legal_authority": validate_legal_authority,
    "statistical_inference": validate_statistical_inference,
    "causal_inference": validate_causal_inference,
    "predictive_validation": validate_predictive_validation,
    "prescriptive_decision": validate_prescriptive_decision,
    "conditional_phenomenon": validate_conditional_phenomenon,
    "evidence_synthesis": validate_evidence_synthesis,
    "historical_source_criticism": validate_historical_source_criticism,
    "practitioner_heuristic": validate_practitioner_heuristic,
}


def run_protocols(
    protocols: list[str],
    protocol_registry: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    inputs = context["payload"].get("protocol_inputs")
    if not isinstance(inputs, dict):
        inputs = {}
    results: dict[str, dict[str, Any]] = {}
    definitions = protocol_registry.get("protocols", {})
    for protocol in protocols:
        definition = definitions.get(protocol)
        if not isinstance(definition, dict):
            results[protocol] = _result("HOLD", "UNREGISTERED_PROTOCOL")
            continue
        validator_name = definition.get("validator")
        validator = VALIDATORS.get(validator_name)
        if validator is None:
            results[protocol] = _result("HOLD", "VALIDATOR_NOT_IMPLEMENTED")
            continue
        input_key = definition.get("input_key")
        data = inputs.get(input_key) if input_key else None
        results[protocol] = validator(context, data)
    return results
