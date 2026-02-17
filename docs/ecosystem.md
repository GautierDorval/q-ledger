# Ecosystem positioning

This repository is intentionally **observational**.

It turns edge logs (what happened) into a chain-linked ledger + derived metrics (what we can infer, conservatively), and publishes them as a public surface (`/.well-known/`).

It is **not** a governance standard, a doctrine, or an audit methodology.

## Observation vs evaluation vs audit

A useful mental model:

- **Q-Ledger (this repo)**: observation and publication of *publicly verifiable snapshots*
  - inputs: edge logs (Cloudflare, Nginx, ALB, …)
  - outputs: `q-ledger.*`, `q-metrics.*`
  - guarantees: append-only chain linking + reproducible canonical hashing
  - does not claim: identity proof, intent, compliance

- **Test suites / evaluation protocols**: controlled measurement
  - inputs: prompts, model outputs, scoring rubrics
  - outputs: evaluation artifacts and failure modes
  - focus: interpretive integrity under adversarial pressure

- **Audit methodologies**: calibrated assessment for decision-making
  - inputs: evidence chain + evaluation artifacts + governance policies
  - outputs: audit reports, risk classification, remediation plans

## Why keep them separate

Mixing observation and normative claims makes systems harder to trust.

Q-Ledger stays narrow:
- it publishes what can be verified from logs and deterministic processing
- it avoids implying compliance, safety, or correctness

That separation makes Q-Ledger reusable even outside any specific governance framework.

## Suggested integration pattern

A practical integration pattern:

1. Publish governance surfaces under `/.well-known/` (your choice of format and policy)
2. Run Q-Ledger to make this surface observable and time-linked (public snapshots)
3. Run evaluation protocols (test suite) to measure interpretive integrity
4. Run audits when you need contractual or regulatory-grade conclusions

## What Q-Metrics should and should not be used for

Q-Metrics are surface signals.

Good uses:
- regression detection (entrypoint compliance dropped)
- drift monitoring (sequence fidelity changed)
- publishing mistakes (after verification)

Bad uses:
- claiming compliance (“we passed governance”)
- proving agent identity or internal intent

## Related repositories (optional)

If you are using Q-Ledger inside a broader stack, keep the boundaries clear:

- **Manifest / doctrine (normative definitions)**
  - `interpretive-governance-manifest`
  - `interpretive-governance-doctrine` (if applicable)

- **Evaluation / scoring (controlled measurement)**
  - `interpretive-governance-test-suite`
  - `iip-scoring-standard` (if applicable)

- **Operational surfaces (discovery / SEO / diplomacy)**
  - `interpretive-seo`

- **Agentic / runtime references (execution patterns)**
  - `interpretive-agentic-reference`

- **Simulation / stress-testing (organizational dynamics)**
  - `authority-governance-simulation-reference`

Q-Ledger is not a runtime dependency of the above repositories (and vice-versa). It is an observational bridge: it publishes what is visible at the edge, without claiming compliance.
