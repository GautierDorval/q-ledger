import os
import sys
import tempfile
import unittest
import json
from typing import Any, Dict
from pathlib import Path

# Allow importing from scripts/
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_ledger  # noqa: E402


class TestBuildLedgerCore(unittest.TestCase):
    def test_canonical_json_hash_stable(self):
        a = {"b": 2, "a": 1}
        b = {"a": 1, "b": 2}
        ha = build_ledger.canonical_json_hash(a)
        hb = build_ledger.canonical_json_hash(b)
        self.assertEqual(ha, hb)
        self.assertEqual(len(ha), 64)

    def test_parse_ts_iso_z(self):
        dt = build_ledger.parse_ts("2026-02-17T00:00:00Z")
        self.assertEqual(dt.tzinfo is not None, True)

    def test_parse_ts_epoch_ms(self):
        dt = build_ledger.parse_ts("1700000000000")  # epoch ms
        self.assertEqual(dt.tzinfo is not None, True)

    def test_normalize_path(self):
        self.assertEqual(build_ledger.normalize_path("https://example.com/.well-known/q-ledger.json?x=1"), "/.well-known/q-ledger.json")
        self.assertEqual(build_ledger.normalize_path("/.well-known/q-ledger.json#frag"), "/.well-known/q-ledger.json")

    def test_infer_sessions_single_hit_cap(self):
        rows = [
            build_ledger.LogRow(
                ts=build_ledger.parse_ts("2026-02-17T00:00:00Z"),
                ip="1.2.3.4",
                ua="ua",
                path="/.well-known/q-ledger.json",
                host="example.com",
                method="GET",
                status="200",
            )
        ]
        sessions = build_ledger.infer_sessions(
            rows,
            "example.com",
            "test-salt",
            30,
            ["/.well-known/q-ledger.json"],
            {},
        )
        self.assertEqual(len(sessions), 1)
        s = sessions[0]
        self.assertLessEqual(s["confidence"], 0.55)
        self.assertEqual(len(s["client_fingerprint_hash"]), 24)

    def test_load_rows_stats(self):
        # One valid row + one malformed row (missing timestamp)
        csv_content = (
            "RayID,EdgeStartTimestamp,ClientIP,ClientRequestUserAgent,ClientRequestPath,ClientRequestHost,ClientRequestMethod,EdgeResponseStatus\n"
            "abc,2026-02-17T00:00:00Z,1.1.1.1,ua,/.well-known/q-ledger.json,example.com,GET,200\n"
            "def,,1.1.1.1,ua,/.well-known/q-ledger.json,example.com,GET,200\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "in.csv"
            p.write_text(csv_content, encoding="utf-8")
            stats = {}
            rows = build_ledger.load_rows(
                str(p),
                "EdgeStartTimestamp",
                "ClientIP",
                "ClientRequestUserAgent",
                "ClientRequestPath",
                "ClientRequestHost",
                "ClientRequestMethod",
                "EdgeResponseStatus",
                stats,
            )
            self.assertEqual(stats["rows_total"], 2)
            self.assertEqual(stats["rows_loaded"], 1)
            self.assertEqual(stats["rows_skipped"], 1)
            self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()

def test_load_rows_ndjson_counts_and_parsing(tmp_path: Path) -> None:
    ndjson = tmp_path / 'in.ndjson'
    ndjson.write_text(
        '\n'.join([
            json.dumps({
                'ts': '2026-02-17T00:00:01Z',
                'ip': '203.0.113.1',
                'user_agent': 'ExampleBot/1.0',
                'path': '/.well-known/q-ledger.json',
                'host': 'example.com',
                'method': 'GET',
                'status': 200,
            }),
            'not-json',
            json.dumps({
                'ts': '2026-02-17T00:00:02Z',
                'ip': '203.0.113.2',
                'user_agent': 'AnotherBot/2.0',
                'path': '/.well-known/q-metrics.json',
                'host': 'example.com',
                'method': 'GET',
                'status': 200,
            }),
        ]) + '\n',
        encoding='utf-8',
    )

    stats: Dict[str, Any] = {}
    rows = build_ledger.load_rows_ndjson(
        str(ndjson),
        key_ts='ts',
        key_ip='ip',
        key_ua='user_agent',
        key_path='path',
        key_host='host',
        key_method='method',
        key_status='status',
        stats_out=stats,
    )

    assert len(rows) == 2
    assert stats['rows_total'] == 3
    assert stats['rows_loaded'] == 2
    assert stats['rows_skipped'] == 1

    assert rows[0].host == 'example.com'
    assert rows[0].path == '/.well-known/q-ledger.json'
    assert rows[0].method.upper() == 'GET'
    assert rows[0].status == 200
