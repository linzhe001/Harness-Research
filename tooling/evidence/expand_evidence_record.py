#!/usr/bin/env python3
"""Print detail references for one light Evidence record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_INDEX = Path(".evidence/light/index.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--record-id", required=True)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_record(path: Path, record_id: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records")
    if not isinstance(records, list):
        raise ValueError(f"{path} records must be a list")
    for record in records:
        if isinstance(record, dict) and record.get("id") == record_id:
            return record
    raise ValueError(f"record not found: {record_id}")


def main() -> int:
    args = parse_args()
    index_path = args.workspace_root / args.index
    try:
        record = load_record(index_path, args.record_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(record, indent=2, ensure_ascii=False))
        return 0
    print(f"id: {record.get('id')}")
    print(f"kind: {record.get('kind')}")
    print(f"status: {record.get('status')}")
    print(f"summary: {record.get('summary')}")
    print(f"detail_ref: {record.get('detail_ref') or 'N/A'}")
    print("source_refs:")
    for ref in record.get("source_refs", []):
        if isinstance(ref, dict):
            print(f"- {ref.get('role')}: {ref.get('path')} {ref.get('sha256') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
