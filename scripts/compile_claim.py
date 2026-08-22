#!/usr/bin/env python3
"""Compile one JSON claim record into an Epistemic Certificate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from knowledge_compiler import compile_claim


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to a compiler input JSON file")
    parser.add_argument("--output", type=Path, help="Write the certificate to this path")
    parser.add_argument("--force", action="store_true", help="Allow replacing an existing output file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument(
        "--require-admission",
        action="store_true",
        help="Exit 3 unless admission is ADMIT or ADMIT_SCOPED",
    )
    parser.add_argument(
        "--adversarial",
        choices=["off", "optional", "required"],
        help=(
            "Host-side adversarial review policy. The strictest of this flag, "
            "KNOWSIFT_ADVERSARIAL_POLICY, and the payload's adversarial_policy wins, "
            "so an input can never relax what the host requires."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with args.input.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        print(f"knowsift: {error}", file=sys.stderr)
        return 2

    certificate = compile_claim(payload, adversarial_policy=args.adversarial)
    indent = 2 if args.pretty else None
    serialized = json.dumps(
        certificate,
        ensure_ascii=False,
        sort_keys=True,
        indent=indent,
        separators=None if args.pretty else (",", ":"),
    )
    if args.output:
        if args.output.exists() and not args.force:
            print(
                f"knowsift: output exists (use --force to replace): {args.output}",
                file=sys.stderr,
            )
            return 2
        try:
            args.output.write_text(serialized + "\n", encoding="utf-8")
        except OSError as error:
            print(f"knowsift: {error}", file=sys.stderr)
            return 2
    else:
        print(serialized)

    if args.require_admission and certificate["admission"] not in {"ADMIT", "ADMIT_SCOPED"}:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
