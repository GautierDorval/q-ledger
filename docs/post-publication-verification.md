# Post-publication verification

Manual publication (copy/paste into a CMS, a virtual file editor, or a dashboard) is fast, but it is also a common source of human error:
- wrong file pasted into the wrong endpoint
- partial paste / truncated payload
- one endpoint updated, the other left stale
- accidental edits

Q-Ledger includes a post-publication verification step to mitigate this risk **without requiring privileged access**.

## What it does

The verifier re-fetches your public endpoints and compares **canonical hashes** against your local outputs:
- `/.well-known/q-ledger.json`
- `/.well-known/q-ledger.yml`
- `/.well-known/q-metrics.json`
- `/.well-known/q-metrics.yml`

It reports:
- local vs remote `sha256` (canonicalized JSON)
- local vs remote size
- optional HTTP hints (ETag, Last-Modified) when present

This is **not** an identity proof and **not** a compliance attestation. It only verifies that what you published matches what you generated locally.

## Usage

### PowerShell (recommended on Windows)

```powershell
.\scriptserify-publication.ps1
```

Override base URL:

```powershell
.\scriptserify-publication.ps1 -BaseUrl "https://example.com"
```

Override config:

```powershell
.\scriptserify-publication.ps1 -ConfigPath ".\config\config.local.json"
```

### Python (cross-platform)

```bash
python scripts/verify_publication.py --config config/config.local.json
```

Or:

```bash
python scripts/verify_publication.py --base-url https://example.com
```

## Configuration

See `config/config.example.json`:

- `publication.base_url`
- `publication.endpoints.*`
- `publication.timeout_seconds`
- `publication.user_agent`
