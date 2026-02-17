#!/usr/bin/env python3
"""
Repo invariants / safety checks.

Goal:
- Prevent accidental commits of environment-specific config into tracked files.
- Keep committed config files strictly identical to their *.example.json counterparts.

This is intentionally small and dependency-free.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_identical(a: Path, b: Path) -> None:
    obj_a = load_json(a)
    obj_b = load_json(b)

    a_dump = json.dumps(obj_a, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    b_dump = json.dumps(obj_b, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    if a_dump != b_dump:
        print(f"FAIL: {a} must be identical to {b}")
        sys.exit(1)


def main() -> int:
    assert_identical(REPO_ROOT / "config" / "config.json", REPO_ROOT / "config" / "config.example.json")
    assert_identical(REPO_ROOT / "config" / "governance_scope.json", REPO_ROOT / "config" / "governance_scope.example.json")
    print("OK: repo invariants satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
