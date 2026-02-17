#!/usr/bin/env python3
"""
Q-Ledger — Post-publication verification

Purpose:
- Reduce human error during manual publication (copy/paste or partial updates).
- Re-fetch public endpoints and compare canonical hashes vs local outputs.

This script is observational tooling. It does not prove identity or compliance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit("PyYAML is required. Install with: pip install -r requirements.txt") from e


DEFAULT_ENDPOINTS: Dict[str, str] = {
    "q_ledger_json": "/.well-known/q-ledger.json",
    "q_ledger_yml": "/.well-known/q-ledger.yml",
    "q_metrics_json": "/.well-known/q-metrics.json",
    "q_metrics_yml": "/.well-known/q-metrics.yml",
}


def canonical_json_bytes(obj: Any) -> bytes:
    """
    Canonical JSON bytes:
    - sort_keys=True
    - compact separators
    - UTF-8
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_bytes(url: str, *, timeout_seconds: int, user_agent: str) -> Tuple[bytes, Dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:  # nosec - intended network fetch
        data = resp.read()
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return data, headers


@dataclass(frozen=True)
class VerifyResult:
    name: str
    url: str
    ok: bool
    local_sha256: str
    remote_sha256: str
    local_size: int
    remote_size: int
    note: str


def verify_endpoint_json(*, name: str, url: str, local_obj: Any, timeout_seconds: int, user_agent: str) -> VerifyResult:
    local_bytes = canonical_json_bytes(local_obj)
    local_sha = sha256_hex(local_bytes)

    remote_bytes, headers = fetch_bytes(url, timeout_seconds=timeout_seconds, user_agent=user_agent)
    remote_size = len(remote_bytes)

    try:
        remote_obj = json.loads(remote_bytes.decode("utf-8"))
    except Exception:
        # Fallback to raw bytes hash if remote is not valid JSON
        remote_sha = sha256_hex(remote_bytes)
        return VerifyResult(
            name=name,
            url=url,
            ok=False,
            local_sha256=local_sha,
            remote_sha256=remote_sha,
            local_size=len(local_bytes),
            remote_size=remote_size,
            note="Remote payload is not valid JSON.",
        )

    remote_sha = sha256_hex(canonical_json_bytes(remote_obj))
    ok = (local_sha == remote_sha)
    note_bits = []
    if "last-modified" in headers:
        note_bits.append(f"last-modified={headers['last-modified']}")
    if "etag" in headers:
        note_bits.append(f"etag={headers['etag']}")
    note = "; ".join(note_bits) if note_bits else "OK" if ok else "Mismatch"
    return VerifyResult(
        name=name,
        url=url,
        ok=ok,
        local_sha256=local_sha,
        remote_sha256=remote_sha,
        local_size=len(local_bytes),
        remote_size=remote_size,
        note=note,
    )


def verify_endpoint_yaml(*, name: str, url: str, local_obj: Any, timeout_seconds: int, user_agent: str) -> VerifyResult:
    local_sha = sha256_hex(canonical_json_bytes(local_obj))
    local_size = len(canonical_json_bytes(local_obj))

    remote_bytes, headers = fetch_bytes(url, timeout_seconds=timeout_seconds, user_agent=user_agent)
    remote_size = len(remote_bytes)

    try:
        remote_obj = yaml.safe_load(remote_bytes.decode("utf-8"))
    except Exception:
        remote_sha = sha256_hex(remote_bytes)
        return VerifyResult(
            name=name,
            url=url,
            ok=False,
            local_sha256=local_sha,
            remote_sha256=remote_sha,
            local_size=local_size,
            remote_size=remote_size,
            note="Remote payload is not valid YAML.",
        )

    remote_sha = sha256_hex(canonical_json_bytes(remote_obj))
    ok = (local_sha == remote_sha)
    note_bits = []
    if "last-modified" in headers:
        note_bits.append(f"last-modified={headers['last-modified']}")
    if "etag" in headers:
        note_bits.append(f"etag={headers['etag']}")
    note = "; ".join(note_bits) if note_bits else "OK" if ok else "Mismatch"
    return VerifyResult(
        name=name,
        url=url,
        ok=ok,
        local_sha256=local_sha,
        remote_sha256=remote_sha,
        local_size=local_size,
        remote_size=remote_size,
        note=note,
    )


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_base_url(config: Optional[Dict[str, Any]], explicit_base_url: Optional[str]) -> str:
    if explicit_base_url:
        return explicit_base_url.rstrip("/")
    if config:
        pub = config.get("publication", {})
        if isinstance(pub, dict) and pub.get("base_url"):
            return str(pub["base_url"]).rstrip("/")
        if config.get("site"):
            return str(config["site"]).rstrip("/")
    raise SystemExit("Missing base URL. Provide --base-url or a config file with publication.base_url / site.")


def build_endpoints(config: Optional[Dict[str, Any]]) -> Dict[str, str]:
    eps = dict(DEFAULT_ENDPOINTS)
    if not config:
        return eps
    pub = config.get("publication", {})
    if isinstance(pub, dict):
        cfg_eps = pub.get("endpoints")
        if isinstance(cfg_eps, dict):
            for k, v in cfg_eps.items():
                if isinstance(v, str):
                    eps[k] = v
    return eps


def print_result(r: VerifyResult) -> None:
    status = "PASS" if r.ok else "FAIL"
    print(f"[{status}] {r.name}")
    print(f"  url: {r.url}")
    print(f"  local_sha256:  {r.local_sha256}")
    print(f"  remote_sha256: {r.remote_sha256}")
    print(f"  local_size:  {r.local_size} bytes")
    print(f"  remote_size: {r.remote_size} bytes")
    print(f"  note: {r.note}")
    print("")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None, help="Path to config JSON (optional).")
    ap.add_argument("--base-url", default=None, help="Public base URL (e.g., https://example.com).")
    ap.add_argument("--local-ledger", default="out/q-ledger.json", help="Path to local q-ledger JSON.")
    ap.add_argument("--local-metrics", default="out/q-metrics.json", help="Path to local q-metrics JSON.")
    ap.add_argument("--timeout", type=int, default=None, help="HTTP timeout seconds (overrides config).")
    ap.add_argument("--user-agent", default=None, help="HTTP User-Agent (overrides config).")
    args = ap.parse_args()

    config = load_config(args.config) if args.config else None
    base_url = build_base_url(config, args.base_url)
    endpoints = build_endpoints(config)

    timeout_seconds = int(args.timeout if args.timeout is not None else (config or {}).get("publication", {}).get("timeout_seconds", 10))
    user_agent = str(args.user_agent if args.user_agent else (config or {}).get("publication", {}).get("user_agent", "q-ledger-verifier"))

    local_ledger = load_json_file(args.local_ledger)
    local_metrics = load_json_file(args.local_metrics)

    results = []
    results.append(
        verify_endpoint_json(
            name="q-ledger.json",
            url=f"{base_url}{endpoints['q_ledger_json']}",
            local_obj=local_ledger,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
    )
    results.append(
        verify_endpoint_yaml(
            name="q-ledger.yml",
            url=f"{base_url}{endpoints['q_ledger_yml']}",
            local_obj=local_ledger,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
    )
    results.append(
        verify_endpoint_json(
            name="q-metrics.json",
            url=f"{base_url}{endpoints['q_metrics_json']}",
            local_obj=local_metrics,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
    )
    results.append(
        verify_endpoint_yaml(
            name="q-metrics.yml",
            url=f"{base_url}{endpoints['q_metrics_yml']}",
            local_obj=local_metrics,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
    )

    for r in results:
        print_result(r)

    failures = [r for r in results if not r.ok]
    if failures:
        print(f"Verification failed: {len(failures)} endpoint(s) mismatched.")
        return 1

    print("Verification OK: all endpoints match local outputs.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
