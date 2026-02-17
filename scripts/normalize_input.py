#!/usr/bin/env python3
"""
Q-Ledger — Input normalization (multi-provider adapters)

Goal:
- Convert common edge / proxy logs into a simple, provider-agnostic "NormalizedRequest"
  that can feed Q-Ledger consistently.

Output formats:
- NDJSON (one JSON object per line) — recommended
- CSV (normalized columns)

This is intentionally conservative:
- No raw log dumping.
- Only minimal HTTP request attributes needed for session inference and governance metrics.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional
from urllib.parse import urlparse


# -------------------------
# Normalized model helpers
# -------------------------

def to_iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso_like(ts: str) -> datetime:
    # Accept: 2026-02-17T00:00:01Z, 2026-02-17T00:00:01.123Z, 2026-02-17T00:00:01+00:00, ...
    t = ts.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    return datetime.fromisoformat(t)


def normalize_path(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return "/"
    # If it's a full URL, keep only path + query? Q-Ledger currently uses path only.
    if "://" in v:
        u = urlparse(v)
        return u.path or "/"
    # Strip querystring and fragments
    v = v.split("#", 1)[0].split("?", 1)[0]
    if not v.startswith("/"):
        v = "/" + v
    return v


@dataclass(frozen=True)
class NormalizedRequest:
    ts: str
    method: str
    path: str
    status: int
    host: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    provider: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "ts": self.ts,
            "method": self.method,
            "path": self.path,
            "status": self.status,
        }
        if self.host is not None:
            d["host"] = self.host
        if self.ip is not None:
            d["ip"] = self.ip
        if self.user_agent is not None:
            d["user_agent"] = self.user_agent
        if self.provider is not None:
            d["provider"] = self.provider
        if self.request_id is not None:
            d["request_id"] = self.request_id
        return d


# -------------------------
# Provider parsers
# -------------------------

def parse_cloudflare_csv(path: str, *, columns: Dict[str, str]) -> Iterator[NormalizedRequest]:
    """
    Cloudflare Log Search CSV export.

    Required columns mapping keys:
      ts, ip, ua, host, method, path, status

    Example mapping (see config/config.example.json):
      ts: EdgeStartTimestamp
      ip: ClientIP
      ua: UserAgent
      host: ClientRequestHost
      method: ClientRequestMethod
      path: ClientRequestPath
      status: EdgeResponseStatus
    """
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts_raw = row.get(columns["ts"], "") or ""
                dt = parse_iso_like(ts_raw)
                ts = to_iso_utc(dt)

                ip = (row.get(columns["ip"], "") or "").strip() or None
                ua = (row.get(columns["ua"], "") or "").strip() or None
                host = (row.get(columns["host"], "") or "").strip() or None
                method = (row.get(columns["method"], "") or "").strip().upper() or "GET"
                path_val = row.get(columns["path"], "") or "/"
                status_raw = row.get(columns["status"], "") or "0"
                status = int(status_raw)

                yield NormalizedRequest(
                    ts=ts,
                    host=host,
                    method=method,
                    path=normalize_path(path_val),
                    status=status,
                    ip=ip,
                    user_agent=ua,
                    provider="cloudflare_csv",
                )
            except Exception:
                # Best-effort: ignore malformed rows
                continue


_NGINX_RE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+"(?P<req>[^"]+)"\s+(?P<status>\d{3})\s+\S+\s+"[^"]*"\s+"(?P<ua>[^"]*)"'
)

def parse_nginx_combined(path: str, *, default_host: str) -> Iterator[NormalizedRequest]:
    """
    Nginx "combined" access log.

    Notes:
    - Host is not always present in the default combined format.
      Use --default-host to set it, or enrich your Nginx log format.
    """
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = _NGINX_RE.match(line.strip())
            if not m:
                continue
            try:
                ip = m.group("ip")
                ts_raw = m.group("ts")
                # Example: 10/Oct/2000:13:55:36 -0700
                dt = datetime.strptime(ts_raw, "%d/%b/%Y:%H:%M:%S %z")
                ts = to_iso_utc(dt)

                req = m.group("req")
                # Example: GET /path HTTP/1.1
                parts = req.split()
                method = (parts[0] if parts else "GET").upper()
                path_val = parts[1] if len(parts) > 1 else "/"
                status = int(m.group("status"))
                ua = m.group("ua") or None

                yield NormalizedRequest(
                    ts=ts,
                    host=default_host or None,
                    method=method,
                    path=normalize_path(path_val),
                    status=status,
                    ip=ip,
                    user_agent=ua,
                    provider="nginx_combined",
                )
            except Exception:
                continue


def parse_aws_alb(path: str) -> Iterator[NormalizedRequest]:
    """
    AWS ALB access logs (text, space-separated, with quoted fields).

    This parser is best-effort and focuses on:
    - time
    - client ip
    - elb_status_code
    - request (method + URL)
    - user_agent
    """
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                parts = shlex.split(line)
                if len(parts) < 14:
                    continue

                ts_raw = parts[1]  # 2026-02-17T00:00:01.000000Z
                dt = parse_iso_like(ts_raw)
                ts = to_iso_utc(dt)

                client = parts[3]  # ip:port
                ip = client.split(":", 1)[0] if ":" in client else client

                status_raw = parts[8]  # elb_status_code
                status = int(status_raw) if status_raw.isdigit() else 0

                request = parts[12]  # "GET https://example.com:443/path HTTP/1.1"
                req_parts = request.split()
                method = (req_parts[0] if req_parts else "GET").upper()
                url = req_parts[1] if len(req_parts) > 1 else "/"
                u = urlparse(url)
                host = u.netloc.split(":", 1)[0] if u.netloc else None
                path_val = u.path or "/"

                ua = parts[13] or None

                yield NormalizedRequest(
                    ts=ts,
                    host=host,
                    method=method,
                    path=normalize_path(path_val),
                    status=status,
                    ip=ip,
                    user_agent=ua,
                    provider="aws_alb",
                )
            except Exception:
                continue


def parse_generic_jsonlines(path: str, *, key_map: Dict[str, str], provider: str) -> Iterator[NormalizedRequest]:
    """
    Generic JSON-lines parser:
    - Each line is a JSON object.
    - key_map indicates where to find ts/host/method/path/status/ip/user_agent.
    """
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                ts_raw = str(obj.get(key_map["ts"], "") or "")
                dt = parse_iso_like(ts_raw)
                ts = to_iso_utc(dt)

                method = str(obj.get(key_map["method"], "GET") or "GET").upper()
                path_val = str(obj.get(key_map["path"], "/") or "/")
                status = int(obj.get(key_map["status"], 0) or 0)

                host = obj.get(key_map.get("host", "host"))
                host = str(host).strip() if host is not None and str(host).strip() else None

                ip = obj.get(key_map.get("ip", "ip"))
                ip = str(ip).strip() if ip is not None and str(ip).strip() else None

                ua = obj.get(key_map.get("user_agent", "user_agent"))
                ua = str(ua).strip() if ua is not None and str(ua).strip() else None

                yield NormalizedRequest(
                    ts=ts,
                    host=host,
                    method=method,
                    path=normalize_path(path_val),
                    status=status,
                    ip=ip,
                    user_agent=ua,
                    provider=provider,
                )
            except Exception:
                continue


# -------------------------
# Writers
# -------------------------

def write_ndjson(out_path: str, rows: Iterable[NormalizedRequest]) -> int:
    count = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
            count += 1
    return count


def write_csv(out_path: str, rows: Iterable[NormalizedRequest]) -> int:
    fieldnames = ["ts", "host", "method", "path", "status", "ip", "user_agent", "provider", "request_id"]
    count = 0
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r.to_dict())
            count += 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize edge/proxy logs into NormalizedRequest NDJSON/CSV for Q-Ledger.")
    ap.add_argument("--provider", required=True, choices=["cloudflare_csv", "nginx_combined", "aws_alb", "generic_jsonl"], help="Input provider / parser.")
    ap.add_argument("--input", required=True, help="Input file path.")
    ap.add_argument("--output", required=True, help="Output file path.")
    ap.add_argument("--output-format", default="ndjson", choices=["ndjson", "csv"], help="Output format.")
    ap.add_argument("--default-host", default="example.com", help="Default host (nginx_combined only, if host not present).")

    # Cloudflare mapping
    ap.add_argument("--cf-ts", default="EdgeStartTimestamp")
    ap.add_argument("--cf-ip", default="ClientIP")
    ap.add_argument("--cf-ua", default="UserAgent")
    ap.add_argument("--cf-host", default="ClientRequestHost")
    ap.add_argument("--cf-method", default="ClientRequestMethod")
    ap.add_argument("--cf-path", default="ClientRequestPath")
    ap.add_argument("--cf-status", default="EdgeResponseStatus")

    # Generic JSONL key mapping (override as needed)
    ap.add_argument("--key-ts", default="ts")
    ap.add_argument("--key-host", default="host")
    ap.add_argument("--key-method", default="method")
    ap.add_argument("--key-path", default="path")
    ap.add_argument("--key-status", default="status")
    ap.add_argument("--key-ip", default="ip")
    ap.add_argument("--key-ua", default="user_agent")
    ap.add_argument("--generic-provider-name", default="generic_jsonl")

    args = ap.parse_args()

    if args.provider == "cloudflare_csv":
        cols = {
            "ts": args.cf_ts,
            "ip": args.cf_ip,
            "ua": args.cf_ua,
            "host": args.cf_host,
            "method": args.cf_method,
            "path": args.cf_path,
            "status": args.cf_status,
        }
        rows = parse_cloudflare_csv(args.input, columns=cols)

    elif args.provider == "nginx_combined":
        rows = parse_nginx_combined(args.input, default_host=args.default_host)

    elif args.provider == "aws_alb":
        rows = parse_aws_alb(args.input)

    elif args.provider == "generic_jsonl":
        key_map = {
            "ts": args.key_ts,
            "host": args.key_host,
            "method": args.key_method,
            "path": args.key_path,
            "status": args.key_status,
            "ip": args.key_ip,
            "user_agent": args.key_ua,
        }
        rows = parse_generic_jsonlines(args.input, key_map=key_map, provider=args.generic_provider_name)

    else:
        raise SystemExit("Unsupported provider")

    if args.output_format == "ndjson":
        n = write_ndjson(args.output, rows)
    else:
        n = write_csv(args.output, rows)

    print(f"Wrote {n} normalized request(s) to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
