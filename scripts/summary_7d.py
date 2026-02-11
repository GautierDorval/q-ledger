#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import glob
import os
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


LEDGERS_DIR = "ledgers"
OUT_MD = "out/summary_7d.md"
OUT_JSON = "out/summary_7d.json"


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def mean(values: List[Optional[float]]) -> Optional[float]:
    vs = [v for v in values if v is not None]
    if not vs:
        return None
    return sum(vs) / len(vs)


def fmt(x: Optional[float], nd: int = 4) -> str:
    if x is None:
        return "n/a"
    return f"{x:.{nd}f}"


def find_metrics_paths(date: str, seq: Any, regime: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (legacy_metrics_path, q_metrics_path) if found.
    """
    seq_str = str(seq)

    # Legacy metrics (existing)
    legacy = os.path.join(LEDGERS_DIR, f"metrics-{date}-seq{seq_str}-{regime}.json")
    if not os.path.exists(legacy):
        legacy2 = os.path.join(LEDGERS_DIR, f"metrics-{date}-seq{seq_str}.json")
        legacy = legacy2 if os.path.exists(legacy2) else None

    # Q-metrics (new; allow multiple naming styles, non-breaking)
    q1 = os.path.join(LEDGERS_DIR, f"q-metrics-{date}-seq{seq_str}.json")
    q2 = os.path.join(LEDGERS_DIR, f"q-metrics-{date}-seq{seq_str}-{regime}.json")
    q = q1 if os.path.exists(q1) else (q2 if os.path.exists(q2) else None)

    return legacy, q


def main():
    pattern = os.path.join(LEDGERS_DIR, "day-tag-*.json")
    tag_files = sorted(glob.glob(pattern))

    if not tag_files:
        raise SystemExit("No day-tag files found in ledgers/. Run archive.ps1 at least once with the updated naming.")

    tags: List[Dict[str, Any]] = []
    for p in tag_files:
        d = load_json(p)
        d["_path"] = p
        tags.append(d)

    # Sort by date_utc then ledger_sequence (in case same day appears multiple times)
    def sort_key(d: Dict[str, Any]):
        date = d.get("date_utc", "0000-00-00")
        seq = int(d.get("ledger_sequence", 0))
        return (date, seq)

    tags.sort(key=sort_key)

    # Keep latest tag per date_utc
    latest_by_date: Dict[str, Dict[str, Any]] = {}
    for t in tags:
        date = t.get("date_utc")
        if not date:
            continue
        latest_by_date[date] = t

    dates_sorted = sorted(latest_by_date.keys())
    last7_dates = dates_sorted[-7:]
    last7 = [latest_by_date[d] for d in last7_dates]

    # Legacy aggregates (from day-tag)
    regime_counts = Counter([d.get("regime", "unknown") for d in last7])
    sessions_total = [safe_float(d.get("sessions_total")) for d in last7]
    single_hit_ratio = [safe_float(d.get("single_hit_ratio")) for d in last7]
    mean_hits = [safe_float(d.get("mean_hits_per_session")) for d in last7]
    distinct_paths = [safe_float(d.get("distinct_paths_total")) for d in last7]

    # Dominant files from legacy metrics archives
    revisits_counter = Counter()
    missing_legacy_metrics = 0

    # Q-metrics aggregates
    q_entry = []
    q_constraints = []
    q_escape = []
    q_seqfid = []
    missing_q_metrics = 0

    for d in last7:
        date = d.get("date_utc")
        seq = d.get("ledger_sequence")
        regime = d.get("regime", "unknown")

        legacy_path, q_path = find_metrics_paths(date, seq, regime)

        if legacy_path and os.path.exists(legacy_path):
            m = load_json(legacy_path)
            top_revisits = m.get("top_revisits", [])
            for item in top_revisits:
                try:
                    path, n = item[0], int(item[1])
                    revisits_counter[path] += n
                except Exception:
                    continue
        else:
            missing_legacy_metrics += 1

        if q_path and os.path.exists(q_path):
            qm = load_json(q_path)
            rates = (qm.get("metrics", {}) or {}).get("rates", {}) or {}
            q_entry.append(safe_float(rates.get("entry_compliance_rate")))
            q_constraints.append(safe_float(rates.get("constraint_touch_rate")))
            q_escape.append(safe_float(rates.get("escape_rate")))
            q_seqfid.append(safe_float(rates.get("sequence_fidelity")))
        else:
            missing_q_metrics += 1

    top_paths = revisits_counter.most_common(10)

    os.makedirs("out", exist_ok=True)
    md: List[str] = []
    md.append("# Summary — last 7 days (q-ledger)")
    md.append("")
    md.append(f"- Days covered: `{len(last7_dates)}`")
    md.append(f"- Date range (UTC): `{last7_dates[0]}` -> `{last7_dates[-1]}`")
    md.append("")

    md.append("## Regime counts (legacy)")
    for regime, n in sorted(regime_counts.items(), key=lambda x: x[1], reverse=True):
        md.append(f"- `{regime}`: {n}")
    md.append("")

    md.append("## Averages (7d) — legacy")
    md.append(f"- Sessions/day (avg): {fmt(mean(sessions_total), 2)}")
    md.append(f"- Single-hit ratio (avg): {fmt(mean(single_hit_ratio), 4)}")
    md.append(f"- Mean hits/session (avg): {fmt(mean(mean_hits), 4)}")
    md.append(f"- Distinct paths/day (avg): {fmt(mean(distinct_paths), 2)}")
    md.append("")

    md.append("## Dominant files (top revisits aggregated across 7d) — legacy")
    if not top_paths:
        md.append("- n/a")
    else:
        for p, n in top_paths:
            md.append(f"- `{p}`: {n}")
    md.append("")

    md.append("## Q-metrics (7d) — observability (if archived)")
    md.append(f"- Entry compliance rate (avg): {fmt(mean(q_entry), 4)}")
    md.append(f"- Constraint touch rate (avg): {fmt(mean(q_constraints), 4)}")
    md.append(f"- Escape rate (avg): {fmt(mean(q_escape), 4)}")
    md.append(f"- Sequence fidelity (avg): {fmt(mean(q_seqfid), 4)}")
    if missing_q_metrics:
        md.append(f"> Note: {missing_q_metrics} day(s) missing q-metrics archives. (Archive q-metrics JSON alongside legacy metrics.)")
    md.append("")

    md.append("## Days (latest run per day)")
    for d in last7:
        md.append(
            f"- `{d.get('date_utc')}` | seq={d.get('ledger_sequence')} | `{d.get('regime')}` | "
            f"sessions={d.get('sessions_total')} | single_hit_ratio={d.get('single_hit_ratio')} | "
            f"mean_hits={d.get('mean_hits_per_session')} | distinct_paths={d.get('distinct_paths_total')}"
        )
    md.append("")
    if missing_legacy_metrics:
        md.append(f"> Note: {missing_legacy_metrics} day(s) missing legacy metrics JSON archives. (Run archive.ps1 with metrics.json present.)")
        md.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    summary_obj = {
        "days_covered": len(last7_dates),
        "date_range_utc": {"start": last7_dates[0], "end": last7_dates[-1]},
        "regime_counts": dict(regime_counts),
        "averages_legacy": {
            "sessions_per_day": mean(sessions_total),
            "single_hit_ratio": mean(single_hit_ratio),
            "mean_hits_per_session": mean(mean_hits),
            "distinct_paths_total": mean(distinct_paths),
        },
        "dominant_files_top10_legacy": top_paths,
        "q_metrics_averages": {
            "entry_compliance_rate": mean(q_entry),
            "constraint_touch_rate": mean(q_constraints),
            "escape_rate": mean(q_escape),
            "sequence_fidelity": mean(q_seqfid)
        },
        "missing_legacy_metrics_json_days": missing_legacy_metrics,
        "missing_q_metrics_json_days": missing_q_metrics,
        "days": [
            {
                "date_utc": d.get("date_utc"),
                "ledger_sequence": d.get("ledger_sequence"),
                "regime": d.get("regime"),
                "rationale": d.get("rationale"),
                "sessions_total": d.get("sessions_total"),
                "single_hit_ratio": d.get("single_hit_ratio"),
                "mean_hits_per_session": d.get("mean_hits_per_session"),
                "distinct_paths_total": d.get("distinct_paths_total"),
                "hash": d.get("hash"),
                "previous_hash": d.get("previous_hash"),
            }
            for d in last7
        ],
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary_obj, f, ensure_ascii=False, indent=2)

    print(f"OK: wrote {OUT_MD}")
    print(f"OK: wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
