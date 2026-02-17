#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
q-ledger builder — Cloudflare Log Search CSV -> observational ledger (JSON + YAML)

- Weak-proof session inference from HTTP request logs (no model identity claims).
- Strict separation:
  - sessions_inferred (derived from logs)
  - attestations_validated (empty unless /q-attest implemented)
- Conservative scoring:
  - single-hit sessions never become "high"
  - yaml_preference only if YAML is actually observed
- Temporal chaining:
  - ledger_sequence increments each run
  - previous_ledger_hash_sha256 stored from prior run
  - state persisted in state/ledger-state.json

NEW (2026-01-25):
- Adds `path_categories` per session (entrypoint/policy/q_layer/canon/constraints/index/ontology/observation/reporting/traceability/discovery/other)
- Default session gap is 30 minutes (configurable)
- Optional support for a local governance scope config (e.g., config/governance_scope.json)
"""

import os
import csv
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional

import yaml


# ----------------------------
# Data model
# ----------------------------

@dataclass
class LogRow:
    ts: datetime
    ip: str
    ua: str
    path: str
    host: str
    method: str = ""
    status: str = ""


# ----------------------------
# Utils
# ----------------------------

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def canonical_json_hash(obj: Dict[str, Any]) -> str:
    canonical = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_hex(canonical)


def parse_ts(ts: str) -> datetime:
    raw = (ts or "").strip()
    if not raw:
        raise ValueError("empty timestamp")

    # epoch ms support
    if raw.isdigit() and len(raw) >= 12:
        return datetime.fromtimestamp(int(raw) / 1000.0, tz=timezone.utc)

    if raw.endswith("Z"):
        return datetime.fromisoformat(raw[:-1]).replace(tzinfo=timezone.utc)

    dt = datetime.fromisoformat(raw)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def normalize_path(uri: str) -> str:
    u = (uri or "").strip()
    if not u:
        return ""
    if "://" in u:
        u = u.split("://", 1)[1]
        u = u[u.find("/"):] if "/" in u else "/"
    if "?" in u:
        u = u.split("?", 1)[0]
    if "#" in u:
        u = u.split("#", 1)[0]
    if not u.startswith("/"):
        u = "/" + u
    while "//" in u:
        u = u.replace("//", "/")
    return u


def fingerprint_hash(ip: str, ua: str, salt: str) -> str:
    return sha256_hex(f"{ip}|{ua}|{salt}")


def load_json_file(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ----------------------------
# State (temporal chaining)
# ----------------------------

def load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"ledger_sequence": 0, "last_ledger_hash": None}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "ledger_sequence" not in data:
        data["ledger_sequence"] = 0
    if "last_ledger_hash" not in data:
        data["last_ledger_hash"] = None
    return data


def save_state(path: str, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ----------------------------
# Config + CSV loading
# ----------------------------



def resolve_existing_file(candidates: List[str], *, label: str) -> str:
    """Return the first existing file path from candidates.

    Raises FileNotFoundError if none exist.
    """
    for p in candidates:
        if not p:
            continue
        if os.path.isfile(p):
            return p
    joined = "\n  - " + "\n  - ".join([c for c in candidates if c])
    raise FileNotFoundError(f"No {label} file found. Tried:{joined}")


def resolve_config_path(cli_path: Optional[str] = None) -> str:
    """Resolve the Q-Ledger config path.

    Order:
      1) CLI --config
      2) env Q_LEDGER_CONFIG_PATH
      3) config/config.local.json (recommended, gitignored)
      4) config/config.json (committed demo default)
      5) config/config.example.json (template)
    """
    env_path = os.environ.get("Q_LEDGER_CONFIG_PATH", "").strip() or None
    return resolve_existing_file(
        [
            cli_path,
            env_path,
            "config/config.local.json",
            "config/config.json",
            "config/config.example.json",
        ],
        label="config",
    )


def resolve_scope_path(cli_path: Optional[str] = None) -> str:
    """Resolve the governance scope config path.

    Order:
      1) CLI --scope
      2) env Q_LEDGER_SCOPE_PATH
      3) config/governance_scope.local.json (recommended, gitignored)
      4) config/governance_scope.json (committed demo default)
      5) config/governance_scope.example.json (template)
    """
    env_path = os.environ.get("Q_LEDGER_SCOPE_PATH", "").strip() or None
    return resolve_existing_file(
        [
            cli_path,
            env_path,
            "config/governance_scope.local.json",
            "config/governance_scope.json",
            "config/governance_scope.example.json",
        ],
        label="governance scope",
    )


def validate_config(cfg: Dict[str, Any]) -> None:
    required = ["site", "input", "output"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Invalid config: missing required keys: {missing}")
def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_case_insensitive(row: Dict[str, str], headers_map: Dict[str, str], wanted: str) -> str:
    actual = headers_map.get((wanted or "").strip().lower(), "")
    return row.get(actual, "") if actual else ""


def load_rows(
    csv_path: str,
    col_ts: str,
    col_ip: str,
    col_ua: str,
    col_path: str,
    col_host: str,
    col_method: Optional[str] = None,
    col_status: Optional[str] = None,
    stats_out: Optional[Dict[str, Any]] = None,
) -> List[LogRow]:
    rows: List[LogRow] = []
    total_rows = 0
    skipped_rows = 0
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        headers = {h.lower(): h for h in fieldnames}

        for r in reader:
            total_rows += 1
            try:
                ts = parse_ts(_get_case_insensitive(r, headers, col_ts))
                ip = (_get_case_insensitive(r, headers, col_ip) or "").strip()
                ua = (_get_case_insensitive(r, headers, col_ua) or "").strip()
                path = normalize_path(_get_case_insensitive(r, headers, col_path))
                host = (_get_case_insensitive(r, headers, col_host) or "").strip()
                method = (_get_case_insensitive(r, headers, col_method) or "").strip() if col_method else ""
                status = (_get_case_insensitive(r, headers, col_status) or "").strip() if col_status else ""
                if not path:
                    continue
                rows.append(LogRow(ts=ts, ip=ip, ua=ua, path=path, host=host, method=method, status=status))
            except Exception:
                skipped_rows += 1
                continue

    rows.sort(key=lambda x: x.ts)
    if stats_out is not None:
        stats_out["rows_total"] = total_rows
        stats_out["rows_loaded"] = len(rows)
        stats_out["rows_skipped"] = skipped_rows

    return rows


# ----------------------------
# Governance scope (optional helper)
# ----------------------------


def load_rows_ndjson(
    ndjson_path: str,
    key_ts: str,
    key_ip: str,
    key_ua: str,
    key_path: str,
    key_host: str,
    key_method: Optional[str] = None,
    key_status: Optional[str] = None,
    stats_out: Optional[Dict[str, Any]] = None,
) -> List[LogRow]:
    """
    Load logs from NDJSON (one JSON object per line).

    The mapping keys (key_ts, key_ip, ...) are taken from config.input.columns,
    exactly like CSV mode, but interpreted as JSON object keys.

    This enables a provider-agnostic intermediate format (see scripts/normalize_input.py).
    """
    rows: List[LogRow] = []
    if stats_out is None:
        stats_out = {}
    stats_out.setdefault("rows_total", 0)
    stats_out.setdefault("rows_loaded", 0)
    stats_out.setdefault("rows_skipped", 0)

    with open(ndjson_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            stats_out["rows_total"] += 1
            try:
                obj = json.loads(line)
                # Normalize keys for parity with CSV loader
                obj = {str(k).lower(): v for k, v in obj.items()}

                ts_raw = str(obj.get(str(key_ts).lower(), "") or "")
                ip = str(obj.get(str(key_ip).lower(), "") or "")
                ua = str(obj.get(str(key_ua).lower(), "") or "")
                path = str(obj.get(str(key_path).lower(), "") or "")
                host = str(obj.get(str(key_host).lower(), "") or "")

                method = ""
                if key_method:
                    method = str(obj.get(str(key_method).lower(), "") or "")
                status_raw = 0
                if key_status:
                    status_raw = obj.get(str(key_status).lower(), 0)

                ts = parse_ts(ts_raw)
                status = int(status_raw) if status_raw is not None else 0
                rows.append(LogRow(ts=ts, ip=ip, ua=ua, path=path, host=host, method=method, status=status))
                stats_out["rows_loaded"] += 1
            except Exception:
                stats_out["rows_skipped"] += 1
                continue

    return rows

def load_scope_layers(scope_path: str) -> Dict[str, List[str]]:
    """
    Optional: load a local scope config (e.g., config/governance_scope.json) and return layers map.
    This is NOT required for the ledger to work, but enables stable path categorization.
    """
    d = load_json_file(scope_path)
    if not d:
        return {}

    layers = d.get("layers", {})
    out: Dict[str, List[str]] = {}
    for k, v in layers.items():
        if isinstance(v, list):
            out[k] = [normalize_path(x) for x in v]
    return out


def build_category_map(layers: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Map exact paths to canonical categories.
    """
    path_to_cat: Dict[str, str] = {}

    def add(paths: List[str], cat: str) -> None:
        for p in paths:
            if p:
                path_to_cat[p] = cat

    add(layers.get("entrypoints", []), "entrypoint")
    add(layers.get("policy", []), "policy")
    add(layers.get("q_layer", []), "q_layer")
    add(layers.get("canon_identity_boundaries", []), "canon")
    add(layers.get("constraints", []), "constraints")
    add(layers.get("routing_discovery", []), "discovery")
    add(layers.get("ontology", []), "ontology")
    add(layers.get("ontology_fallback", []), "ontology")
    add(layers.get("index", []), "index")
    add(layers.get("observation", []), "observation")
    add(layers.get("traceability", []), "traceability")
    add(layers.get("reporting", []), "reporting")

    return path_to_cat


# ----------------------------
# Session inference
# ----------------------------

def infer_sessions(
    rows: List[LogRow],
    site_host: str,
    salt: str,
    gap_minutes: int,
    gov_exact_paths: List[str],
    path_to_category: Dict[str, str]
) -> List[Dict[str, Any]]:

    if site_host:
        rows = [r for r in rows if r.host == site_host]

    grouped: Dict[str, List[LogRow]] = defaultdict(list)
    for r in rows:
        fp = fingerprint_hash(r.ip or "noip", r.ua or "noua", salt)
        grouped[fp].append(r)

    sessions: List[Dict[str, Any]] = []
    gap = timedelta(minutes=gap_minutes)

    gov_set = set(gov_exact_paths)

    def is_gov(p: str) -> bool:
        return p in gov_set if gov_set else True  # if not provided, treat all as "observed"

    def classify(p: str) -> str:
        return path_to_category.get(p, "other")

    for fp, items in grouped.items():
        items.sort(key=lambda x: x.ts)
        current: List[LogRow] = []

        def flush(chunk: List[LogRow]) -> None:
            if not chunk:
                return

            paths = [x.path for x in chunk]
            cats = [classify(p) for p in paths]

            total = len(paths)
            gov_hits = sum(1 for p in paths if is_gov(p))
            revisits = total - len(set(paths))

            signals: List[str] = []
            if gov_hits >= 1:
                signals.append("governance_path_hit")
            if gov_hits >= 2:
                signals.append("multiple_governance_hits")
            if any(p.endswith((".yml", ".yaml")) for p in paths):
                signals.append("yaml_accessed")
            if any(p.endswith(".jsonld") for p in paths):
                signals.append("jsonld_accessed")
            if revisits > 0:
                signals.append("path_revisited")

            ratio = gov_hits / max(total, 1)
            confidence = 0.20 + ratio * 0.55  # up to 0.75 before bonuses

            yaml_present = any(p.endswith((".yml", ".yaml")) for p in paths)
            jsonld_present = any(p.endswith(".jsonld") for p in paths)
            if yaml_present and not jsonld_present:
                signals.append("yaml_preference_observed")
                confidence += 0.10

            if total >= 5 and gov_hits >= 3:
                signals.append("systematic_governance_check")
                confidence += 0.10

            cap = 0.55 if total == 1 else 0.95
            confidence = min(cap, max(0.05, confidence))

            if total == 1:
                level = "low"
            elif confidence >= 0.75:
                level = "high"
            elif confidence >= 0.50:
                level = "medium"
            else:
                level = "low"

            if "yaml_preference_observed" in signals:
                primary = "yaml_preference"
            elif gov_hits >= 2:
                primary = "governance_sequence"
            elif gov_hits == 1:
                primary = "single_governance_hit"
            else:
                primary = "unknown"

            start = chunk[0].ts
            end = chunk[-1].ts
            sid = sha256_hex(f"{fp}|{start.isoformat()}|{end.isoformat()}")[:16]

            sessions.append({
                "session_id": sid,
                "window_utc": {
                    "start": start.isoformat().replace("+00:00", "Z"),
                    "end": end.isoformat().replace("+00:00", "Z")
                },
                "client_fingerprint_hash": fp[:24],
                "confidence": round(confidence, 2),
                "path": paths,
                "path_categories": cats,
                "signals": signals,
                "agent_classification": {
                    "confidence_level": level,
                    "primary_signal": primary,
                    "human_readable_hypothesis": (
                        "comportement compatible avec un agent autonome"
                        if confidence >= 0.60 and total >= 2
                        else "hypothese faible"
                    ),
                    "warning": "aucune preuve cryptographique d'identite"
                }
            })

        for r in items:
            if not current:
                current = [r]
                continue
            if r.ts - current[-1].ts <= gap:
                current.append(r)
            else:
                flush(current)
                current = [r]
        flush(current)

    sessions.sort(key=lambda s: s["window_utc"]["start"])
    return sessions


# ----------------------------
# Main
# ----------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build Q-Ledger (append-only, chain-linked) from Cloudflare CSV logs."
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Path to config JSON. If omitted, uses Q_LEDGER_CONFIG_PATH or config/config.local.json, then falls back to committed defaults.",
    )
    parser.add_argument(
        "--scope",
        dest="scope_path",
        default=None,
        help="Path to governance scope JSON. If omitted, uses Q_LEDGER_SCOPE_PATH or config/governance_scope.local.json, then falls back to committed defaults.",
    )
    parser.add_argument(
        "--input-csv",
        dest="input_csv",
        default=None,
        help="Override input CSV path (otherwise taken from config).",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        default=None,
        help="Input file path. Supports CSV (legacy) and NDJSON (one JSON object per line). Overrides config.",
    )
    parser.add_argument(
        "--input-format",
        dest="input_format",
        default=None,
        choices=["cloudflare_csv", "normalized_csv", "normalized_ndjson"],
        help="Input format override. If omitted, uses config.input.format or file extension.",
    )
    parser.add_argument(
        "--state",
        dest="state_path",
        default="state/ledger-state.json",
        help="Path to ledger state JSON (sequence + previous hash).",
    )
    args = parser.parse_args(argv)

    cfg_path = resolve_config_path(args.config_path)
    cfg = load_config(cfg_path)

    # Governance scope config (recommended). If absent, path categories are simply omitted.
    scope_cfg_path = None
    try:
        scope_cfg_path = resolve_scope_path(args.scope_path)
    except FileNotFoundError:
        scope_cfg_path = None

    layers = load_scope_layers(scope_cfg_path) if scope_cfg_path and os.path.exists(scope_cfg_path) else {}
    path_to_category = build_category_map(layers) if layers else {}

    # Governance exact paths: either provided directly, or derived from scope layers
    gov_paths = list(cfg.get("governance_paths", []))
    if not gov_paths and layers:
        # Flatten all layer paths into a single allowlist
        for _k, paths in layers.items():
            gov_paths.extend(paths)
    gov_paths = [normalize_path(p) for p in gov_paths if p]

    salt_env = cfg.get("fingerprint_salt_env", "Q_LEDGER_SALT")
    salt = os.environ.get(salt_env, "").strip()
    if not salt:
        raise SystemExit(f"Missing environment variable: {salt_env}")

    input_cfg = cfg["input"]
    cols = input_cfg["columns"]

    input_path = args.input_path or args.input_csv or input_cfg.get("csv_path") or input_cfg.get("input_csv")
    if not input_path:
        raise SystemExit(
            "Missing input path. Provide --input (preferred) / --input-csv or set input.csv_path in config."
        )

    input_format = args.input_format or input_cfg.get("format") or "cloudflare_csv"
    lower_path = str(input_path).lower()
    if lower_path.endswith(".ndjson") or lower_path.endswith(".jsonl"):
        input_format = "normalized_ndjson"

    ingest_stats: Dict[str, Any] = {}

    if input_format == "normalized_ndjson":
        rows = load_rows_ndjson(
            input_path,
            cols["timestamp"],
            cols["ip"],
            cols["ua"],
            cols["path"],
            cols["host"],
            cols.get("method"),
            cols.get("status"),
            stats_out=ingest_stats,
        )
    else:
        rows = load_rows(
            input_path,
            cols["timestamp"],
            cols["ip"],
            cols["ua"],
            cols["path"],
            cols["host"],
            cols.get("method"),
            cols.get("status"),
            stats_out=ingest_stats,
        )

    # Optional filtering by method/status if columns exist in CSV (safe)
    allow_methods = cfg.get("allow_methods", ["GET"])
    allow_status = cfg.get("allow_status", ["200", "304"])
    filtered_rows: List[LogRow] = []
    allow_methods_norm = [m.upper() for m in allow_methods] if allow_methods else []
    allow_status_norm = [str(s) for s in allow_status] if allow_status else []
    gov_set = set(gov_paths) if gov_paths else set()

    for r in rows:
        if r.method and allow_methods_norm and r.method.upper() not in allow_methods_norm:
            continue
        if r.status and allow_status_norm and r.status not in allow_status_norm:
            continue
        # If governance paths list is present, keep only those
        if gov_set and r.path not in gov_set:
            continue
        filtered_rows.append(r)

    gap_minutes = int(cfg.get("session_gap_minutes", 30))

    sessions = infer_sessions(
        filtered_rows,
        cfg.get("site_host", ""),
        salt,
        gap_minutes,
        gov_paths,
        path_to_category,
    )

    state = load_state(args.state_path)

    ledger_sequence = int(state.get("ledger_sequence", 0)) + 1
    previous_hash = state.get("last_ledger_hash")

    generated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    ledger: Dict[str, Any] = {
        "ledger_version": "1.1",
        "ledger_sequence": ledger_sequence,
        "site": cfg["site"],
        "generated_utc": generated,
        "method": {
            "name": "ledger-derived-from-logs",
            "version": "session-inference-1.5",
            "session_gap_minutes": gap_minutes,
            "notes": "sessions inferred from logs; no model identity is asserted",
        },
        "export_window": cfg.get("export_window", "manual"),
        "input_stats": ingest_stats,
        "sessions_inferred": sessions,
        "attestations_validated": [],
        "integrity": {
            "previous_ledger_hash_sha256": previous_hash,
            "canonicalization": "json(sort_keys=true,separators=(',',':'))",
        },
    }

    ledger_hash = canonical_json_hash(ledger)
    ledger["integrity"]["content_hash_sha256"] = ledger_hash

    os.makedirs(os.path.dirname(cfg["output"]["json"]), exist_ok=True)
    os.makedirs(os.path.dirname(cfg["output"]["yaml"]), exist_ok=True)

    with open(cfg["output"]["json"], "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)

    with open(cfg["output"]["yaml"], "w", encoding="utf-8") as f:
        f.write("# Human-readable mirror file\n")
        f.write("# Canonical: /.well-known/q-ledger.json\n")
        f.write("# Do not edit manually when the pipeline is active\n\n")
        yaml.safe_dump(ledger, f, allow_unicode=True, sort_keys=False)

    latest_json = cfg["output"].get("latest_json")
    if latest_json:
        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)

    save_state(args.state_path, {
        "ledger_sequence": ledger_sequence,
        "last_ledger_hash": ledger_hash,
    })

    skipped = ingest_stats.get("rows_skipped", 0)
    skipped_note = f" | skipped_rows={skipped}" if skipped else ""
    print(f"OK: sessions={len(sessions)} | seq={ledger_sequence} | hash={ledger_hash[:12]}…{skipped_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

