#!/usr/bin/env python3
"""Validate a source bundle collected by an external search or ingestion agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from knowledge_compiler.knowledge_document import KnowledgeDocumentError, validate_source_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Source bundle JSON")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        normalized = validate_source_bundle(payload, args.input.parent)
    except (OSError, json.JSONDecodeError, KnowledgeDocumentError) as error:
        print(f"knowsift: {error}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "status": "VALID",
                "topic": normalized["topic"],
                "source_count": len(normalized["sources"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
