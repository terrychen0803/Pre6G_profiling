#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from profile_job_builder.preservation import compare_preservation
from profile_job_builder.yamlio import load_yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--generated", required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    result = compare_preservation(
        load_yaml(args.source),
        load_yaml(args.generated),
        args.container,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if result["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
