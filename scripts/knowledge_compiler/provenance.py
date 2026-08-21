"""Provenance graph construction with explicit cycle detection."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def summarize_provenance(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    sources: dict[str, dict[str, Any]] = {}
    for item in evidence:
        if not isinstance(item, dict):
            continue
        source_id = item.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            continue
        node = sources.setdefault(
            source_id,
            {"derived_from": set(), "cites": set(), "dataset_ids": set(), "evidence_ids": []},
        )
        node["derived_from"].update(item.get("derived_from", []) or [])
        node["cites"].update(item.get("cites", []) or [])
        if item.get("dataset_id"):
            node["dataset_ids"].add(item["dataset_id"])
        node["evidence_ids"].append(item.get("evidence_id"))

    parents = {
        source_id: set(node["derived_from"]) | set(node["cites"])
        for source_id, node in sources.items()
    }
    cycles: set[tuple[str, ...]] = set()
    memo: dict[str, set[str]] = {}

    def roots(source_id: str, path: tuple[str, ...] = ()) -> set[str]:
        if source_id in memo:
            return memo[source_id]
        if source_id in path:
            start = path.index(source_id)
            cycles.add(path[start:] + (source_id,))
            return set()
        source_parents = parents.get(source_id, set())
        if not source_parents:
            memo[source_id] = {source_id}
            return memo[source_id]
        result: set[str] = set()
        for parent in sorted(source_parents):
            result.update(roots(parent, path + (source_id,)))
        memo[source_id] = result
        return result

    roots_by_source = {source_id: sorted(roots(source_id)) for source_id in sorted(sources)}
    all_roots = sorted({root for values in roots_by_source.values() for root in values})

    datasets: dict[str, list[str]] = defaultdict(list)
    for source_id, node in sources.items():
        for dataset_id in node["dataset_ids"]:
            datasets[dataset_id].append(source_id)
    shared_datasets = {
        dataset_id: sorted(source_ids)
        for dataset_id, source_ids in datasets.items()
        if len(set(source_ids)) > 1
    }

    serialized_nodes = {
        source_id: {
            "derived_from": sorted(node["derived_from"]),
            "cites": sorted(node["cites"]),
            "dataset_ids": sorted(node["dataset_ids"]),
            "evidence_ids": sorted(x for x in node["evidence_ids"] if x),
        }
        for source_id, node in sorted(sources.items())
    }
    return {
        "status": "PASS" if not cycles else "HOLD",
        "code": "PROVENANCE_ACYCLIC" if not cycles else "PROVENANCE_CYCLE",
        "evidence_count": len(evidence),
        "source_count": len(sources),
        "independent_root_count": len(all_roots),
        "independent_provenance_roots": all_roots,
        "roots_by_source": roots_by_source,
        "shared_datasets": shared_datasets,
        "cycles": [list(cycle) for cycle in sorted(cycles)],
        "nodes": serialized_nodes,
    }
