# Changelog

## Unreleased — PRO-1299: canonical `--database` / `--collection` flags

Finishes the vocabulary alignment PRO-1298 started. The commands were renamed to the
canonical verbs, but their scope *flags* still said "tenant" — the one word CONTRACT §1
bans. This is what lets `plugins/cli.mdx` be written entirely in canonical terms.

### Added
- Canonical `--database` / `-d` and `--collection` on every command taking a scope:
  `query`, `ingest`, `list`, `inspect`, `delete`, `relations`, `verify`, `login`, and the
  `database {collections,stats,readiness,monitor}` sub-commands.
- `HYDRADB_API_URL` is now honoured as a deprecated alias of `HYDRADB_BASE_URL`. It is the
  spelling the CLI's own docs page shipped, so §1's per-client scoping rule makes it one of
  this client's legacy names; `conformance/vectors.json` already listed it.

### Changed
- `--tenant-id` / `--sub-tenant-id` still work but are hidden from `--help` and emit a
  one-line stderr deprecation warning naming the canonical flag. The canonical spelling
  wins, silently, when both are given.
- `login` now writes the canonical `database` / `collection` config keys rather than the
  deprecated `tenant_id` / `sub_tenant_id` ones. Both are still read.
- `login --output json` gains a `database` field; the existing `tenant_id` field is kept
  verbatim because it is part of the documented `--output json` contract (§3).
- "No database specified" now points at `--database` and `config set database`.

### Fixed
- `__version__` said `0.1.0` while `pyproject.toml` said `0.1.1`, so `hydradb --version`
  would have misreported after release.

## Unreleased — PRO-1298: migrate onto `hydradb-sdk` behind a hand-owned wrapper

The CLI now calls the generated `hydradb-sdk` (pinned exactly at `2.1.2`) through
a thin hand-owned wrapper instead of a hand-rolled HTTP client, and adopts the
shared HydraDB canonical vocabulary.

### Added
- Canonical commands: `query`, `ingest`, `list`, `inspect`, `delete`,
  `relations`, `verify`, `database {create,delete,list,collections,stats,readiness,monitor}`,
  `doctor`.
- Canonical env vars `HYDRADB_API_KEY` / `HYDRADB_DATABASE` / `HYDRADB_COLLECTION`
  / `HYDRADB_BASE_URL`. The CLI's own legacy `HYDRA_DB_*` names still work as
  deprecated aliases (one warning each).
- Canonical config-file keys `database` / `collection` (`hydradb config set database …`).
- A conformance runner (`conformance/`) that drives the shared `vectors.json`
  through the wrapper against a mocked SDK transport.

### Changed
- Every legacy command (`tenant`, `memories`, `knowledge`, `recall`, `fetch`,
  `whoami`) is now a **deprecated alias** that prints a one-line stderr warning
  naming its canonical replacement. Behaviour is preserved.

### Breaking (`--output json`)
These two commands change their JSON shape as a direct result of the v1 → v2 API
migration and the canonical vocabulary. The documented `jq` contract
(`query … | jq '.chunks[0].chunk_content'`) is **unchanged** and covered by
golden tests.

- **`list`** (and its `memories list` / `fetch sources` aliases): items are now
  under `sources` (v2), not `user_memories`. Memory items appear in the same
  `sources` array.
- **`database monitor`** (and the `tenant monitor` alias): now returns a merged
  `{ "database", "stats", "readiness" }` object instead of the single v1 monitor
  payload. The underlying single-purpose data is also available as separate
  clean commands — `hydradb database stats` and `hydradb database readiness` —
  with `monitor` kept only as the merged façade/alias.

### Fixed
- Ingest result rendering no longer shows `unknown` when the server returns the
  source identifier as `id` (v2) instead of `source_id` — the formatter now
  falls back to `id`.
- `ingest --kind knowledge --text … --source-id foo` sends the item via
  `app_knowledge` so the client-assigned `id` is preserved verbatim as the
  source_id; a later `delete foo` matches. (A `documents` upload would get a
  server-minted id and silently fail to delete.) Raw file uploads still use
  `documents`.
- `delete` of a non-existent id no longer reports success: the v2 no-op
  (`200 {success:false}`) now yields a non-zero exit and `{"success":false,…}`
  in JSON mode.
- Multi-file `ingest <files>` loops one SDK call per file (the SDK's `documents`
  takes a single file) and merges results — files are never silently dropped.
