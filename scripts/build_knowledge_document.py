#!/usr/bin/env python3
"""Validate certificate-backed records and render a layered Markdown document."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from knowledge_compiler.knowledge_document import (
    KnowledgeDocumentError,
    render_knowledge_document,
    validate_document_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Knowledge document plan JSON")
    parser.add_argument("--output", type=Path, help="Markdown output path")
    parser.add_argument("--check-only", action="store_true", help="Validate without rendering")
    parser.add_argument("--force", action="store_true", help="Replace an existing output")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if args.check_only:
            validate_document_plan(payload, args.input.parent)
            print("knowsift: document plan is valid")
            return 0
        rendered = render_knowledge_document(payload, args.input.parent)
    except (OSError, json.JSONDecodeError, KnowledgeDocumentError) as error:
        print(f"knowsift: {error}", file=sys.stderr)
        return 2
    if args.output:
        if args.output.exists() and not args.force:
            print(
                f"knowsift: output exists (use --force to replace): {args.output}",
                file=sys.stderr,
            )
            return 2
        try:
            args.output.write_text(rendered, encoding="utf-8")
        except OSError as error:
            print(f"knowsift: {error}", file=sys.stderr)
            return 2
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
