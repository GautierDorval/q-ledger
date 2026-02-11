#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import sys
import os
import yaml


# ----------------------------
# Helpers
# ----------------------------

def parse_iso_z(s: str) -> datetime:
    s = (s or "").strip()
    if s.endswith("Z"):
        return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def median(values: List[float]) -> Optional[float]:
    return float(statistics.median(values)) if values else None


def percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    vs = sorted(values)
    k = int(round((len(vs) - 1) * p))
    return float(vs[k])


def fmt_seconds(s: Optional[float]) -> str:
    if s is None:
        return "n/a"
    if s < 60:
        return f"{s:.1f} s"
    if s < 3600:
        return f"{s/60:.1f} min"
    return f"{s/3600:.2f} h"


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------
# Legacy analysis (kept)
# ----------------------------

def is_governance_path_legacy(path: str) -> bool:
    markers = [
        "/.well-known/",
        "/ai-governance.json",
        "/ai-manifest.json",
        "/dualweb-index.md",
        "/response-legitimacy",
        "/llms",
        "/readme.llm.txt",
        "/canon.md",
        "/identity.json",
        "/services-non-publics.md",
        "/author.md",
        "/humans.txt",
        "/site-context.md",
        "/editorial-context.md",
        "/non-goals.md",
        "/negative-definitions.md",
        "/output-constraints.md",
        "/data-handling.md",
        "/citations.md",
        "/changelog-ai.md"
    ]
    return any(m in path for m in markers)


def is_content_path_legacy(path: str) -> bool:
    if is_governance_path_legacy(path):
        return False
    if path.endswith((".json", ".jsonld", ".yaml", ".yml", ".txt", ".md")):
        return False
    return path.endswith("/") or path.count("/") >= 1


def session_revisit_stats(session: Dict[str, Any]) -> Tuple[Dict[str, int], List[float]]:
    """
    Returns:
    - counts: path -> occurrences
    - deltas: approximate deltas between repeated paths (seconds)
      Approximation: uniform spacing between start/end across hits.
    """
    paths = session.get("path", [])
    total_hits = len(paths)

    counts: Dict[str, int] = {}
    for p in paths:
        counts[p] = counts.get(p, 0) + 1

    deltas: List[float] = []
    if total_hits <= 1:
        return counts, deltas

    start = parse_iso_z(session["window_utc"]["start"])
    end = parse_iso_z(session["window_utc"]["end"])
    duration = max(0.0, (end - start).total_seconds())
    if duration == 0:
        return counts, deltas

    step = duration / (total_hits - 1)
    hit_times = [start.timestamp() + i * step for i in range(total_hits)]

    positions: Dict[str, List[int]] = {}
    for idx, p in enumerate(paths):
        positions.setdefault(p, []).append(idx)

    for p, idxs in positions.items():
        if len(idxs) < 2:
            continue
        for a, b in zip(idxs, idxs[1:]):
            deltas.append(hit_times[b] - hit_times[a])

    return counts, deltas


def detect_sequences_legacy(paths: List[str]) -> Dict[str, int]:
    motifs = {
        "yaml_then_ledger": 0,
        "yaml_then_protocol": 0,
        "ledger_then_protocol": 0,
        "gov_content_gov": 0
    }

    for i in range(len(paths) - 1):
        a, b = paths[i], paths[i + 1]
        if a.endswith((".yml", ".yaml")) and "/.well-known/q-ledger" in b:
            motifs["yaml_then_ledger"] += 1
        if a.endswith((".yml", ".yaml")) and "q-attest-protocol" in b:
            motifs["yaml_then_protocol"] += 1
        if "/.well-known/q-ledger" in a and "q-attest-protocol" in b:
            motifs["ledger_then_protocol"] += 1

    for i in range(len(paths) - 2):
        a, b, c = paths[i], paths[i + 1], paths[i + 2]
        if is_governance_path_legacy(a) and is_content_path_legacy(b) and is_governance_path_legacy(c):
            motifs["gov_content_gov"] += 1

    return motifs


def classify_regime_legacy(
    sessions_total: int,
    single_hit_ratio: float,
    mean_hits: float,
    motifs_total: int,
    top_revisits: List[Tuple[str, int]]
) -> Tuple[str, str]:
    if sessions_total < 5:
        return ("other_low_data", "sessions_total < 5")

    top_manifest = 0
    for p, n in top_revisits:
        if p == "/ai-manifest.json":
            top_manifest = n
            break

    if single_hit_ratio >= 0.70 and motifs_total == 0 and (top_manifest >= 5 or mean_hits <= 1.5):
        return ("validation_ingestion", f"single_hit_ratio>=0.70, motifs_total=0, manifest_revisits={top_manifest}, mean_hits={mean_hits:.2f}")

    if motifs_total >= 1:
        return ("exploration_navigation", f"motifs_total>=1 ({motifs_total})")
    if mean_hits >= 2.3 and single_hit_ratio <= 0.55:
        return ("exploration_navigation", f"mean_hits>=2.3 and single_hit_ratio<=0.55 (mean_hits={mean_hits:.2f}, ratio={single_hit_ratio:.2f})")

    return ("mixed", f"no strong rule matched (mean_hits={mean_hits:.2f}, ratio={single_hit_ratio:.2f}, motifs_total={motifs_total}, manifest_revisits={top_manifest})")


# ----------------------------
# Q-metrics (new)
# ----------------------------

def compress_consecutive(items: List[str]) -> List[str]:
    out: List[str] = []
    for x in items:
        if not out or out[-1] != x:
            out.append(x)
    return out


def load_scope(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        return load_json(path)
    except Exception:
        return None


def build_exact_path_to_category(scope: Dict[str, Any]) -> Dict[str, str]:
    """
    Build exact path -> category map from governance_scope.json.
    IMPORTANT: we keep canon_identity_boundaries as 'canon' (not constraints),
    because build_ledger uses that category; we'll treat canon as constraints at metric time.
    """
    layers = (scope or {}).get("layers", {})
    mapping: Dict[str, str] = {}

    def add(layer_key: str, category: str) -> None:
        for p in layers.get(layer_key, []) or []:
            mapping[p] = category

    add("entrypoints", "entrypoint")
    add("policy", "policy")
    add("q_layer", "q_layer")
    add("canon_identity_boundaries", "canon")
    add("constraints", "constraints")
    add("routing_discovery", "discovery")
    add("ontology", "ontology")
    add("ontology_fallback", "ontology")
    add("index", "index")
    add("observation", "observation")
    add("traceability", "traceability")
    add("reporting", "reporting")

    return mapping


def classify_path_with_scope(path: str, exact_map: Dict[str, str]) -> str:
    return exact_map.get(path, "other")


def subsequence_match(seq: List[str], expected: List[str]) -> bool:
    """
    Match expected as an ordered subsequence (not necessarily contiguous).
    """
    if not expected:
        return True
    j = 0
    for c in seq:
        if c == expected[j]:
            j += 1
            if j == len(expected):
                return True
    return False


def normalize_categories_for_metrics(cats: List[str]) -> List[str]:
    """
    - drop 'other'
    - compress consecutive duplicates
    - keep canon as canon (we will treat canon as constraints where needed)
    """
    cats = [c for c in (cats or []) if c and c != "other"]
    return compress_consecutive(cats)


def compute_expected_patterns(scope: Optional[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """
    Returns:
    - expected_pattern_full: may include content
    - expected_pattern_governance_only: content removed + simplified
    """
    expected_pattern_full: List[str] = []
    expected_pattern_governance_only: List[str] = []

    expected_sequences = (scope or {}).get("expected_sequences", []) or []
    if expected_sequences:
        p = expected_sequences[0].get("pattern", []) or []
        layer_to_cat = {
            "entrypoints": "entrypoint",
            "policy": "policy",
            "q_layer": "q_layer",
            "constraints": "constraints",
            "index": "index",
            "ontology": "ontology",
            "content": "content"
        }
        expected_pattern_full = [layer_to_cat.get(x, x) for x in p]

    # Governance-only expected pattern:
    # We want something stable and measurable even when no human content is logged.
    # Minimal regime: entrypoint → (policy|discovery|q_layer) → (canon|constraints) → (ontology|index)
    # As an ordered subsequence, we represent this as:
    expected_pattern_governance_only = ["entrypoint", "constraints", "ontology"]
    # We'll treat 'canon' as 'constraints' for matching (see matching function below).

    return expected_pattern_full, expected_pattern_governance_only


def map_canon_to_constraints_for_checks(cats: List[str]) -> List[str]:
    """
    For some metric checks, canon must count as constraints.
    This returns a transformed list used ONLY for checks (does not alter ledger output).
    """
    out = []
    for c in cats:
        if c == "canon":
            out.append("constraints")
        else:
            out.append(c)
    return out


def compute_q_metrics(ledger: Dict[str, Any], scope: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sessions = ledger.get("sessions_inferred", [])
    generated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Determine window from ledger sessions
    starts: List[datetime] = []
    ends: List[datetime] = []
    for s in sessions:
        try:
            starts.append(parse_iso_z(s["window_utc"]["start"]))
            ends.append(parse_iso_z(s["window_utc"]["end"]))
        except Exception:
            continue

    if starts and ends:
        start_date = min(starts).date().isoformat()
        end_date = max(ends).date().isoformat()
    else:
        start_date = "to-be-generated"
        end_date = "to-be-generated"

    # Classification map (fallback if ledger lacks path_categories)
    exact_map = build_exact_path_to_category(scope) if scope else {}

    expected_pattern_full, expected_pattern_governance_only = compute_expected_patterns(scope)

    # First pass: detect whether any content category is present at all
    observed_any_content = False
    for s in sessions:
        cats = s.get("path_categories", [])
        if not cats:
            paths = s.get("path", [])
            cats = [classify_path_with_scope(p, exact_map) for p in paths]
        cats = normalize_categories_for_metrics(cats)
        if "content" in cats:
            observed_any_content = True
            break

    # Counters
    total = 0
    entrypoint_first = 0
    constraints_touched = 0
    escaped = 0
    seq_match = 0

    governance_only_mode = False
    used_pattern: Optional[List[str]] = None

    for s in sessions:
        paths = s.get("path", [])
        cats = s.get("path_categories", [])

        if not cats:
            cats = [classify_path_with_scope(p, exact_map) for p in paths]

        cats = normalize_categories_for_metrics(cats)
        if not cats:
            continue

        total += 1

        if cats[0] == "entrypoint":
            entrypoint_first += 1

        # Treat canon as constraints for this metric (fix)
        cats_for_checks = map_canon_to_constraints_for_checks(cats)

        if "constraints" in cats_for_checks:
            constraints_touched += 1

        # governance-only escape: no entrypoint at all, but touches governed layers (including canon)
        if "entrypoint" not in cats_for_checks and any(
            c in ("policy", "q_layer", "constraints", "ontology", "index", "reporting", "traceability", "observation", "discovery")
            for c in cats_for_checks
        ):
            escaped += 1

        # Sequence fidelity:
        # - If content observed, use declared expected_pattern_full (if present)
        # - Otherwise, use governance-only expected pattern
        if expected_pattern_full and observed_any_content:
            used_pattern = expected_pattern_full
            # For matching, map canon->constraints (so canon satisfies constraints slot)
            seq = cats_for_checks
            if subsequence_match(seq, used_pattern):
                seq_match += 1
        else:
            governance_only_mode = True
            used_pattern = expected_pattern_governance_only
            seq = cats_for_checks
            # Governance-only pattern expects constraints+ontology after entrypoint (subsequence)
            if subsequence_match(seq, used_pattern):
                seq_match += 1

    rates = {
        "entry_compliance_rate": (entrypoint_first / total) if total else None,
        "constraint_touch_rate": (constraints_touched / total) if total else None,
        "escape_rate": (escaped / total) if total else None,
        "sequence_fidelity": (seq_match / total) if total else None
    }

    counts = {
        "sessions_inferred_total": total if total else None,
        "sessions_with_entrypoint_first": entrypoint_first if total else None,
        "sessions_with_constraints_touched": constraints_touched if total else None,
        "sessions_escaped": escaped if total else None,
        "sessions_matching_expected_sequence": seq_match if total else None
    }

    notes = [
        "All values are derived from observational logs and are weak evidence only.",
        "If Q-Ledger is unavailable, these metrics must be treated as unavailable.",
        "Canon identity/boundary files are treated as constraints for constraint touch and sequence fidelity.",
        "Escape rate is computed in governance-only mode unless human content is included in the ledger scope."
    ]
    if governance_only_mode:
        notes.append("Sequence fidelity computed in governance-only mode (content not observed or not included).")

    q_metrics = {
        "schemaVersion": "0.1.0",
        "type": "QMetrics",
        "site": ledger.get("site", "https://gautierdorval.com/"),
        "canonical": "https://gautierdorval.com/.well-known/q-metrics.json",
        "derived_from": [
            "https://gautierdorval.com/.well-known/q-ledger.json"
        ],
        "purpose": "Publish non-normative, derived observability metrics from Q-Ledger to make interpretive governance behavior measurable, reproducible, and contestable. This file does not grant response authorization and does not define truth. Q-Layer remains authoritative for response legitimacy.",
        "non_normative_notice": "Metrics are descriptive. They must not be treated as authorization, compliance, certification, or guarantees.",
        "disclosure_token": "GD-IG-GOVERNED",
        "metric_config": {
            "time_window_days": (scope or {}).get("window_days", 7),
            "session_window_minutes": (scope or {}).get("session_window_minutes", 30),
            "expected_pattern_used": used_pattern
        },
        "metrics": {
            "window": {
                "start_date": start_date,
                "end_date": end_date,
                "generated_at_utc": generated
            },
            "counts": counts,
            "rates": rates,
            "notes": notes
        },
        "traceability": {
            "q_ledger": "https://gautierdorval.com/.well-known/q-ledger.json",
            "q_ledger_yaml": "https://gautierdorval.com/.well-known/q-ledger.yml",
            "q_attest_protocol": "https://gautierdorval.com/.well-known/q-attest-protocol.md",
            "changelog": "https://gautierdorval.com/changelog-ai.md"
        },
        "last_reviewed": datetime.now(timezone.utc).date().isoformat(),
        "stability": "high"
    }

    return q_metrics


# ----------------------------
# Main
# ----------------------------

def main():
    ledger_path = sys.argv[1] if len(sys.argv) >= 2 else "out/q-ledger.json"
    out_md = sys.argv[2] if len(sys.argv) >= 3 else "out/metrics.md"
    out_json = sys.argv[3] if len(sys.argv) >= 4 else "out/metrics.json"
    out_qmetrics = sys.argv[4] if len(sys.argv) >= 5 else "out/q-metrics.json"
    out_qmetrics_yaml = sys.argv[5] if len(sys.argv) >= 6 else "out/q-metrics.yml"

    scope_path = os.environ.get("GOVERNANCE_SCOPE_PATH", "config/governance_scope.json")
    scope = load_scope(scope_path)

    ledger = load_json(ledger_path)
    sessions = ledger.get("sessions_inferred", [])

    seq = ledger.get("ledger_sequence", "n/a")
    gen = ledger.get("generated_utc", "n/a")
    prev = ledger.get("integrity", {}).get("previous_ledger_hash_sha256")
    h = ledger.get("integrity", {}).get("content_hash_sha256")

    # Legacy aggregates
    all_revisit_counts: Dict[str, int] = {}
    all_deltas: List[float] = []
    motifs_total_map = {"yaml_then_ledger": 0, "yaml_then_protocol": 0, "ledger_then_protocol": 0, "gov_content_gov": 0}

    distinct_paths = set()
    total_hits = 0
    single_hit_sessions = 0

    for s in sessions:
        paths = s.get("path", [])
        total_hits += len(paths)
        if len(paths) == 1:
            single_hit_sessions += 1
        for p in paths:
            distinct_paths.add(p)

        counts, deltas = session_revisit_stats(s)
        for p, c in counts.items():
            if c >= 2:
                all_revisit_counts[p] = all_revisit_counts.get(p, 0) + (c - 1)
        all_deltas.extend(deltas)

        motifs = detect_sequences_legacy(paths)
        for k in motifs_total_map:
            motifs_total_map[k] += motifs.get(k, 0)

    sessions_total = len(sessions)
    single_hit_ratio = (single_hit_sessions / sessions_total) if sessions_total else 0.0
    mean_hits = (total_hits / sessions_total) if sessions_total else 0.0
    motifs_total = sum(motifs_total_map.values())

    top_revisits = sorted(all_revisit_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    regime, rationale = classify_regime_legacy(sessions_total, single_hit_ratio, mean_hits, motifs_total, top_revisits)

    # Build markdown (legacy report)
    md: List[str] = []
    md.append("# q-ledger metrics")
    md.append("")
    md.append(f"- Generated: `{gen}`")
    md.append(f"- Ledger sequence: `{seq}`")
    md.append(f"- Hash: `{h}`")
    md.append(f"- Previous hash: `{prev}`")
    md.append(f"- Sessions: `{sessions_total}`")
    md.append(f"- Single-hit ratio: `{single_hit_ratio:.2f}`")
    md.append(f"- Mean hits per session: `{mean_hits:.2f}`")
    md.append(f"- Distinct paths: `{len(distinct_paths)}`")
    md.append("")

    md.append("## Daily regime classification (legacy)")
    md.append(f"- Regime: `{regime}`")
    md.append(f"- Rationale: `{rationale}`")
    md.append("")

    md.append("## Top revisits (approx.)")
    if not top_revisits:
        md.append("- n/a")
    else:
        for p, n in top_revisits:
            md.append(f"- `{p}`: {n}")
    md.append("")

    md.append("## Time between revisits (approx.)")
    if not all_deltas:
        md.append("- n/a")
    else:
        md.append(f"- Count: {len(all_deltas)}")
        md.append(f"- Min: {fmt_seconds(min(all_deltas))}")
        md.append(f"- Median: {fmt_seconds(median(all_deltas))}")
        md.append(f"- P90: {fmt_seconds(percentile(all_deltas, 0.90))}")
        md.append(f"- Max: {fmt_seconds(max(all_deltas))}")
    md.append("")

    md.append("## Motifs detected (legacy)")
    for k, v in motifs_total_map.items():
        md.append(f"- `{k}`: {v}")
    md.append("")

    md.append("## Sessions (summary)")
    for s in sessions:
        sid = s.get("session_id")
        w = s.get("window_utc", {})
        conf = s.get("confidence")
        primary = s.get("agent_classification", {}).get("primary_signal")
        hits = len(s.get("path", []))
        md.append(f"- `{sid}` | `{w.get('start')}` -> `{w.get('end')}` | conf={conf} | `{primary}` | hits={hits}")

    md.append("")

    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    metrics_obj = {
        "generated_utc": gen,
        "ledger_sequence": seq,
        "hash": h,
        "previous_hash": prev,
        "sessions_total": sessions_total,
        "single_hit_ratio": round(single_hit_ratio, 4),
        "mean_hits_per_session": round(mean_hits, 4),
        "distinct_paths_total": len(distinct_paths),
        "regime": regime,
        "regime_rationale": rationale,
        "top_revisits": top_revisits,
        "motifs": motifs_total_map,
        "revisit_deltas_seconds": {
            "count": len(all_deltas),
            "min": min(all_deltas) if all_deltas else None,
            "median": median(all_deltas),
            "p90": percentile(all_deltas, 0.90),
            "max": max(all_deltas) if all_deltas else None
        }
    }

    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(metrics_obj, f, ensure_ascii=False, indent=2)

    # Q-metrics outputs
    q_metrics = compute_q_metrics(ledger, scope)

    os.makedirs(os.path.dirname(out_qmetrics), exist_ok=True)
    with open(out_qmetrics, "w", encoding="utf-8") as f:
        json.dump(q_metrics, f, ensure_ascii=False, indent=2)

    os.makedirs(os.path.dirname(out_qmetrics_yaml), exist_ok=True)
    with open(out_qmetrics_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(q_metrics, f, allow_unicode=True, sort_keys=False)

    print(f"OK: wrote {out_md}")
    print(f"OK: wrote {out_json}")
    print(f"OK: wrote {out_qmetrics}")
    print(f"OK: wrote {out_qmetrics_yaml}")
    print(f"Legacy regime: {regime} | {rationale}")


if __name__ == "__main__":
    main()
