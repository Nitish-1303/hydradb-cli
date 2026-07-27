# Conformance

This directory is the anti-drift gate for `hydradb-cli`'s alignment to the shared
HydraDB client contract (`../CONTRACT.md`, PRO-1298).

`vectors.json` is the **shared** fixture set — identical across all four client
repos (`hydradb-cli`, `hydradb-mcp`, `openclaw-hydradb`, `hydradb-claude-code`).
Do not edit this repo's copy in isolation; the master lives with `CONTRACT.md`.

## What the runner asserts

`test_conformance.py` builds the real wrapper against a **mocked SDK transport**
(`httpx.MockTransport`), so the genuine SDK request-building code runs and the
exact HTTP call is captured. For every vector it checks:

1. **Canonical operation** — the wrapper hits the expected endpoint + HTTP method.
2. **SDK call shape** — the request carries the vector's `args_include` and
   `args_scope` fields, uses the required `content_type`, and never sends a
   `forbid_field` (e.g. knowledge ingest must be `multipart/form-data` with a
   top-level `database` field, never `application/json` with `app_knowledge`).
3. **CLI alias resolution** — every deprecated CLI alias in `aliases.cli`
   (`recall full`, `tenant create`, `memories add`, …) routes to the same
   canonical operation as its replacement.

## Running

```bash
make bootstrap        # once
.venv/bin/pytest conformance -q
```

The suite is also part of the default `pytest` run (it is on `testpaths`), so CI
fails if the wrapper renames an action, changes a default, or diverges in ingest
encoding.
