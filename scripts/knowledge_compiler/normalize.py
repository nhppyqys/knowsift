"""Deterministic, evidence-linked claim normalization."""

from __future__ import annotations

import copy
import json
from typing import Any


def normalize_claim(
    ir: dict[str, Any],
    payload: dict[str, Any],
    protocol_results: dict[str, dict[str, Any]],
    semantic_summary: dict[str, Any],
    verified_scope: dict[str, Any],
    verified_conditions: dict[str, Any],
    verified_exceptions: list[dict[str, Any]],
    valid_components: list[dict[str, Any]],
) -> dict[str, Any]:
    if semantic_summary.get("status") == "FAIL":
        return {
            "status": "CONTRADICTED",
            "normalized_ir": None,
            "transformations": ["CLAIM_CONTRADICTED_BY_SUPPLIED_EVIDENCE"],
        }
    if any(result.get("status") == "FAIL" for result in protocol_results.values()):
        return {
            "status": "CONTRADICTED",
            "normalized_ir": None,
            "transformations": ["DECISIVE_PROTOCOL_CHECK_FAILED"],
        }

    causal = protocol_results.get("CAUSAL_INFERENCE")
    if causal and causal.get("status") != "PASS":
        return {
            "status": "SUPPORTED_COMPONENTS_ONLY" if valid_components else "HOLD",
            "normalized_ir": None,
            "transformations": ["CAUSAL_CLAIM_NOT_SAFELY_NORMALIZABLE"],
        }

    out = copy.deepcopy(ir)
    transformations: list[str] = []
    scoped = False

    generalization = protocol_results.get("GENERALIZATION")
    if generalization and generalization.get("status") == "PASS_SCOPED":
        out["quantifier"] = "UNSPECIFIED"
        out["scope"] = {**(out.get("scope") or {}), **verified_scope}
        transformations.append("REMOVE_UNSUPPORTED_GENERALIZATION")
        scoped = True

    scope_result = protocol_results.get("SCOPE_BOUNDARY")
    if scope_result and scope_result.get("status") == "PASS_SCOPED":
        out["scope"] = {**(out.get("scope") or {}), **verified_scope}
        transformations.append("ALIGN_TO_VERIFIED_SCOPE")
        scoped = True

    legal = protocol_results.get("LEGAL_AUTHORITY")
    if legal and legal.get("status") == "PASS_SCOPED" and verified_exceptions:
        if out.get("quantifier") in {"ALL", "NONE"}:
            out["quantifier"] = "GENERALLY"
        out.setdefault("legal", {})["exceptions"] = [item["text"] for item in verified_exceptions]
        transformations.append("ADD_VERIFIED_LEGAL_EXCEPTIONS")
        scoped = True

    conditional = protocol_results.get("CONDITIONAL_PHENOMENON")
    if conditional and conditional.get("status") == "PASS_SCOPED":
        out["scope"] = {**(out.get("scope") or {}), "conditions": verified_conditions}
        transformations.append("ATTACH_VERIFIED_CONDITIONS")
        scoped = True

    practitioner = protocol_results.get("PRACTITIONER_HEURISTIC")
    if practitioner and practitioner.get("status") == "PASS_SCOPED":
        data = (payload.get("protocol_inputs") or {}).get("practitioner_heuristic", {})
        context = data.get("context")
        if context:
            out["scope"] = {**(out.get("scope") or {}), "practice_context": context}
            transformations.append("ATTACH_PRACTITIONER_CONTEXT")
            scoped = True

    return {
        "status": "SUPPORTED_IF_NARROWED" if scoped else "SUPPORTED_AS_IS",
        "normalized_ir": out,
        "transformations": transformations,
    }


def _format_scope_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _contains_han(value: str) -> bool:
    return any("\u3400" <= character <= "\u9fff" for character in value)


def _strip_terminal_punctuation(value: Any) -> str:
    return str(value).strip().rstrip("。！？.!?")


def _render_chinese(ir: dict[str, Any]) -> str:
    scope = ir.get("scope") if isinstance(ir.get("scope"), dict) else {}
    scope_labels = {
        "arrangement": "安排",
        "conditions": "条件",
        "department": "部门",
        "duration": "时间",
        "horizon": "期限",
        "jurisdiction": "适用地区",
        "model": "型号",
        "organization": "组织",
        "population": "人群",
        "practice_context": "实践场景",
        "study": "研究",
        "version": "版本",
    }
    quantifier = {
        "ALL": "所有",
        "MOST": "大多数",
        "SOME": "部分",
        "EXISTS": "至少一个",
        "NONE": "没有",
        "GENERALLY": "通常，",
        "UNSPECIFIED": "",
    }.get(ir.get("quantifier"), "")
    modality = {
        "ASSERTED": "",
        "POSSIBLE": "可能",
        "LIKELY": "很可能",
        "SHOULD": "应该",
        "MUST": "必须",
        "REPORTED": "据报告",
    }.get(ir.get("modality"), "")
    negative = "不" if ir.get("polarity") == "NEGATIVE" else ""
    subject = _strip_terminal_punctuation(ir.get("subject", ""))
    predicate = _strip_terminal_punctuation(ir.get("predicate", ""))
    statement = f"{quantifier}{subject}{modality}{negative}{predicate}"
    if ir.get("object") is not None:
        statement += _strip_terminal_punctuation(ir["object"])

    parts: list[str] = []
    if scope:
        scope_text = "；".join(
            f"{scope_labels.get(key, key)}：{_format_scope_value(value)}"
            for key, value in sorted(scope.items())
        )
        parts.append(f"适用范围：{scope_text}。")
        parts.append(f"结论：{statement}。")
    else:
        parts.append(f"{statement}。")
    exceptions = (ir.get("legal") or {}).get("exceptions")
    if exceptions:
        parts.append("例外：" + "；".join(str(item) for item in exceptions) + "。")
    return "".join(parts)


def render_canonical(ir: dict[str, Any] | None) -> str | None:
    if ir is None:
        return None
    if _contains_han(str(ir.get("source_text", ""))):
        return _render_chinese(ir)
    scope = ir.get("scope") if isinstance(ir.get("scope"), dict) else {}
    if scope:
        scope_text = "; ".join(
            f"{key}={_format_scope_value(value)}" for key, value in sorted(scope.items())
        )
        prefix = f"Within {scope_text}, "
    else:
        prefix = ""

    quantifier = {
        "ALL": "All ",
        "MOST": "Most ",
        "SOME": "Some ",
        "EXISTS": "At least one ",
        "NONE": "No ",
        "GENERALLY": "Generally, ",
        "UNSPECIFIED": "",
    }.get(ir.get("quantifier"), "")
    modality = {
        "ASSERTED": "",
        "POSSIBLE": "may ",
        "LIKELY": "likely ",
        "SHOULD": "should ",
        "MUST": "must ",
        "REPORTED": "is reported to ",
    }.get(ir.get("modality"), "")
    negative = "does not " if ir.get("polarity") == "NEGATIVE" else ""
    sentence = f"{prefix}{quantifier}{ir.get('subject', '')} {modality}{negative}{ir.get('predicate', '')}"
    if ir.get("object") is not None:
        sentence += f" {ir['object']}"
    exceptions = (ir.get("legal") or {}).get("exceptions")
    if exceptions:
        sentence += "; exceptions: " + "; ".join(str(item) for item in exceptions)
    return " ".join(sentence.split())
