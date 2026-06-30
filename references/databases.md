# Database Standards (Postgres / Supabase, BigQuery, SQLite)

Companion reference for the senior-engineering-partner skill.

> **Rigor tier:** the RLS tenant-isolation matrix (pgTAP + HTTP, positive AND cross-tenant-deny), append-only evidence, and migration gates here are **Tier-2 (production/commercial) posture** from SKILL.md's *Project Phase & Rigor Ladder*. At Tier 0/1, parameterized queries + least-privilege roles + a basic migration are the floor; defer the full RLS test matrix with an explicit `TODO` — but the moment real tenant data or multi-tenancy appears, this is non-negotiable.

Covers the three databases this environment actually touches: Postgres-on-Supabase
(the multi-tenant B2B SaaS on Cloud Run), BigQuery (analytics), and SQLite (inside
portable single-file Python scripts). This file covers the parts of BigQuery that
make it "a database you write queries against" — parameterization and dataset-scoped
access. For the single-file pytest harness see `references/testing-single-file.md`.

> Tool/CLI/API specifics below were correct as of this writing; Supabase, the GCP
> client libraries, and Postgres move. **Verify any exact flag, role name, port, or
> client-library symbol against current docs before relying on it** — that
> verify-before-asserting discipline is the whole point of this skill.

---

## Universal rules (every database, every language)

These four are non-negotiable on Postgres, BigQuery, AND SQLite.

- **ALWAYS use parameterized / prepared statements. Never string-interpolate user
  data into SQL.** This is the SQL half of the command-injection rule in SKILL.md
  (Bash Command Injection Prevention) — same root cause, same severity. An
  f-string, `%`-format, `.format()`, or `+` concatenation that puts a caller value
  into the query *text* lets `'; DROP TABLE …; --` or `' OR '1'='1` re-parse as SQL.
  Use the driver's placeholder, and pass values as a separate argument:

  | Engine / driver | Placeholder | Example |
  |---|---|---|
  | Postgres (`psycopg`/`psycopg2`) | `%s` | `cur.execute("SELECT * FROM users WHERE id = %s", (uid,))` |
  | SQLite (`sqlite3`, stdlib) | `?` | `cur.execute("SELECT * FROM t WHERE id = ?", (uid,))` |
  | BigQuery (`google-cloud-bigquery`) | `@name` + `ScalarQueryParameter` | `job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("uid","STRING",uid)])` |

  The placeholder is for **values only** — it cannot parameterize an identifier
  (table/column name) or a keyword. If a caller must choose a column or sort
  direction, validate it against an explicit allowlist (`if col not in
  ALLOWED_COLUMNS: raise`), then interpolate the allowlisted literal. Never pass the
  raw string through. For dynamic identifiers in Postgres use
  `psycopg.sql.Identifier()` (psycopg3) / `psycopg2.sql.Identifier()` — compose with
  `sql.SQL(...).format(...)` and keep a `%s` placeholder for the value.

- **The application's DB role is not the owner and is never superuser.** The app
  connects as a least-privilege role with `SELECT/INSERT/UPDATE/DELETE` on exactly
  the tables it needs — never the schema owner, never `postgres`. On Supabase the
  app reaches Postgres as `authenticated`/`anon` (RLS applies); reserve the
  `service_role` (which carries `BYPASSRLS` — every policy on every table is skipped)
  for narrow, server-side use only. A leaked `service_role` key is a full-tenant
  breach, not a bug — treat it like a root password, and it must never appear in any
  browser/mobile/desktop bundle.

- **Connection strings and DB credentials come from 1Password or GCP Secret
  Manager — never from code, never committed.** Local/dev: `op read`. Cloud Run:
  mount from Secret Manager and read via env var; do not bake the DSN into the
  image. Same secrets rule as SKILL.md — and the Supabase `service_role` key, the
  `anon` key, and the direct-connection database password are three *separate*
  secrets with three different blast radii. Store them as three separate items.

- **Encryption in transit and at rest is mandatory.** Postgres/Supabase: connect
  with `sslmode=verify-full` (not `require` — `require` encrypts but does NOT verify
  the server cert, so it's defeated by a MITM; `verify-full` checks the cert chain
  AND hostname, and needs the CA cert / `sslrootcert`). Supabase, Cloud SQL, and
  BigQuery encrypt at rest by default — verify it's on, don't assume. SQLite has no
  built-in encryption: if the file holds sensitive data, `chmod 600` it and rely on
  FileVault, or use SQLCipher.

---

## Postgres / Supabase

### Row-Level Security is the make-or-break tenant-isolation control

For the multi-tenant SaaS, RLS is not optional and not a nice-to-have — **one tenant
table with RLS forgotten is a cross-tenant data leak**, and it leaks silently
(queries succeed, just returning rows they shouldn't). Discipline:

- **`ALTER TABLE … ENABLE ROW LEVEL SECURITY` on every tenant-scoped table.**
  Enabling RLS with *no* policy is deny-by-default — the table returns zero rows to
  non-owners, which is the safe failure. The dangerous state is RLS *off*: then the
  table is wide open to any role with table grants. New table = enable RLS in the
  same migration, never "later."
- **Write an explicit policy per operation.** A single `FOR ALL` policy is a smell
  for anything past read-only — `SELECT`, `INSERT`, `UPDATE`, `DELETE` have
  different correct predicates. `USING` filters which existing rows are visible/
  affected; `WITH CHECK` validates rows being written. An `INSERT` policy needs
  `WITH CHECK`; forgetting it lets a tenant insert rows tagged with *another*
  tenant's id.
- **Also add `… FORCE ROW LEVEL SECURITY`** so the table owner is subject to its
  own policies — by default RLS does not apply to the table owner, and if your
  migrations or a misconfigured role connect as owner, RLS is silently bypassed.
- **Reserve `BYPASSRLS` / the `service_role` for narrow server-side jobs** (admin
  reports, cross-tenant maintenance) that run server-side only and never with a
  caller-supplied tenant id in scope. Default app traffic always goes through RLS.
- **The TEST is the control.** A policy you didn't test is a policy you don't have —
  see the RLS isolation test below.

```sql
-- tenant isolation policy keyed off the Supabase JWT claim
ALTER TABLE engagements ENABLE ROW LEVEL SECURITY;
ALTER TABLE engagements FORCE  ROW LEVEL SECURITY;

CREATE POLICY tenant_select ON engagements FOR SELECT
  USING (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);

CREATE POLICY tenant_insert ON engagements FOR INSERT
  WITH CHECK (tenant_id = (auth.jwt() ->> 'tenant_id')::uuid);
```

### Setting RLS identity without Supabase Auth: session GUCs + a `SECURITY DEFINER` resolver

When you are NOT on Supabase Auth (e.g. Firebase Auth or your own JWT, as in the
the example SaaS API), RLS can't read `auth.jwt()`. Instead the app sets **session
GUCs** per request and the policies read those. The application half lives in
`references/python-web-apis.md`; the database half is here.

- **Policies read custom GUCs via accessor functions**, e.g. `app.current_user_id()` →
  `current_setting('app.current_user_id', true)::uuid`, and an `app.current_company_ids()`
  returning the request's company array. The `true` argument makes a *missing* setting
  return NULL (→ default-deny) instead of raising.
- **Set the GUCs with `SET LOCAL` (the `set_config(name, value, true)` form), inside the
  request transaction.** `SET LOCAL` clears at COMMIT/ROLLBACK, so a pooled connection
  **cannot leak one request's identity into the next** — the single most important
  property for a pooled multi-tenant app. A plain session-level `SET` on a pooled
  connection is a cross-tenant leak waiting to happen.
- **Drop to the least-privilege role per request with `SET LOCAL ROLE app_api`.** It
  can't be parameterized (it's an identifier) — allowlist the role name to code
  constants and quote with `psycopg.sql.Identifier`, never an f-string (cross-ref
  `python-web-apis.md`).
- **The chicken-and-egg, and why `SECURITY DEFINER` is the right tool:** under `FORCE`'d
  RLS with no GUCs set yet, the request role is in default-deny — it cannot read
  `users`/`memberships` to discover *who it is*. Resolve identity with a `SECURITY
  DEFINER` function (`app.resolve_session(firebase_uid)`) that runs as its owner to do
  exactly one lookup. The safety rule that keeps that safe: **it takes the external id
  as an argument, never reads a GUC, and returns only that one user's identity** — so
  bypassing RLS cannot widen cross-tenant visibility. Same pattern for first-time
  onboarding (`app.onboard_user`), where a brand-new user belongs to no company and so
  could satisfy no policy. Keep `SECURITY DEFINER` functions tiny, argument-driven, and
  `search_path`-pinned (`SET search_path = …`) so a caller-controlled `search_path`
  can't hijack them.

### Append-only tables for evidence / audit integrity

For audit trails and most compliance-relevant tables, **enforce
append-only at the database, not in app code**: a policy/trigger that permits `INSERT`
but rejects `UPDATE`/`DELETE`, so a tampered or deleted record is impossible even for a
compromised app role. Pair it with a content hash (`content_sha256`) on stored objects so
later tampering is detectable. For a regulated product this is an audit /
legal-admissibility requirement; elsewhere it is a SOC 2 audit-integrity control
(cross-ref `compliance.md`, `secure-data-processing.md`). Test it — see the append-only
pgTAP gate below.

- **Append-only ≠ unscoped: the INSERT policy still needs a tenant-scoped `WITH CHECK`.** A `WITH CHECK (true)` on an append-only audit/usage table is forgeable across tenants — any app-role caller can insert a row tagged with *another* `company_id`. Scope the insert (`WITH CHECK (company_id = any(app.current_company_ids()))`), matching the tenant tables; route genuinely platform-level writes (rows not owned by the caller's tenant) through a narrow `SECURITY DEFINER` writer, never a blanket `true`.
- **Test the DENY, not just the allow (negative authz).** A pgTAP suite that only asserts an admin *can* write an admin-gated row proves nothing about the gate. Assert the negative too — a non-admin or wrong-tenant caller is *denied* the insert/update (`throws_ok`/zero-rows) — for every admin-gated and tenant-scoped policy. An RLS test without a deny assertion is a false green (cross-ref `testing.md` §2).

### Migrations: versioned, forward-only, idempotent, reviewed

- **Every schema change is a checked-in, versioned migration** (Supabase CLI
  migrations, Alembic, or Sqitch — pick one per repo and stay consistent). No
  hand-run `ALTER TABLE` in the Supabase SQL editor against prod; that drifts the
  schema from the repo and the next migration fails to apply or — worse — silently
  diverges between environments.
- **House tool: `dbmate`** (containerized + pinned, run via `scripts/dbmate.sh` over
  docker-compose — no host install). Plain timestamped `.sql` files with `-- migrate:up`
  / `-- migrate:down` sections, applied with `dbmate --wait up` (it waits for the DB to
  accept connections first). Keeping the tool in a pinned container means every dev Mac
  and the CI runner apply byte-identical migrations — the same reproducibility argument
  as pinned dependencies (SKILL.md).
- **Forward-only in production.** Down/rollback migrations are for local dev and
  CI; in prod you roll *forward* with a new corrective migration plus PITR as the
  real safety net (see Backups). Test that down migrations work in CI anyway (see
  migration tests) — a broken `downgrade` is a documentation lie.
- **Idempotent where the engine allows it** (`CREATE TABLE IF NOT EXISTS`,
  `CREATE INDEX IF NOT EXISTS`, guarded `DO` blocks) so a partially-applied
  migration can be re-run.
- **Migrations are code → they go through PR + required CI + squash-merge** like
  everything else (SKILL.md Source Code Management). A migration is the highest-blast-
  radius change in the repo; it gets the most review, not the least.
- **Build indexes in prod with `CREATE INDEX CONCURRENTLY`.** A plain `CREATE INDEX`
  takes a `SHARE` lock on the table, which conflicts with `ROW EXCLUSIVE` and so
  blocks all `INSERT/UPDATE/DELETE` for the whole build — a self-inflicted outage on
  a live tenant table. `CONCURRENTLY` instead holds only `SHARE UPDATE EXCLUSIVE`
  (reads and writes proceed) but cannot run inside a transaction block, so it needs
  its own migration step — and if it fails it leaves an `INVALID` index behind that
  you must `DROP` and rebuild.

### Connection pooling (mandatory on Cloud Run)

Cloud Run scales to many concurrent instances; each opening direct Postgres
connections will blow past `max_connections` and the app starts throwing
`FATAL: sorry, too many clients already`. **Route app traffic through a pooler** —
Supabase's Supavisor (or PgBouncer if self-hosting).

- **Use the transaction-mode pooler connection string for the app** (Supavisor
  port `6543`), the direct connection (port `5432`) only for migrations and admin.
  Transaction-pooling mode does not give a client a dedicated backend, so
  session-level features break by default (server-side prepared statements reused
  across calls, `SET` that must persist, `LISTEN/NOTIFY`); if a library assumes them
  you'll see odd "prepared statement already exists" / state-leak errors — configure
  the driver for transaction pooling (e.g. disable client-side prepared-statement
  caching, or `?prepared_statements=false` depending on the driver) or use session
  mode deliberately. (Current Supavisor and PgBouncer ≥ 1.21 can support named
  prepared statements in transaction mode — verify your versions before relying on
  it rather than assuming.)

### Timeouts (set them or a runaway query takes the service down)

- **`statement_timeout`** — cap how long any single query runs. Without it, one
  pathological query pins a connection and a backend CPU indefinitely. Set a sane
  per-role default (e.g. a few seconds for interactive app traffic; longer, scoped,
  for batch jobs).
- **`idle_in_transaction_session_timeout`** — kill transactions left open and idle.
  An app bug that opens a transaction and never commits holds locks and bloats
  autovacuum's dead-tuple horizon; this timeout reaps it. The symptom you're
  preventing: rising lock waits and table bloat with no obvious culprit query.

### Indexes justified by EXPLAIN ANALYZE, not by hunch

Add an index because `EXPLAIN ANALYZE` shows a `Seq Scan` on a hot path with a
selective predicate — not speculatively. Read actual rows vs. estimated rows
(bad estimates → bad plans, often a stale-statistics or missing-`ANALYZE` problem).
Every index has a write cost; an unused index is pure overhead. For multi-tenant
tables, the tenant-id column belongs in composite indexes (usually leading) so RLS
predicates stay index-backed.

### Backups: pg_dump + Point-In-Time Recovery

PITR (continuous WAL archiving — available on Supabase paid tiers / Cloud SQL) is
the primary recovery story: it recovers to a specific second, which is what you
need after a bad migration or an accidental mass `DELETE`. `pg_dump` (logical,
periodic, stored off-platform) is the secondary, portable copy and the way to move
a single tenant or schema. Have both. A backup you've never restored is a hypothesis
— periodically restore into a scratch project and confirm row counts.

---

## BigQuery (it's also a database you query)

BigQuery is the analytics store. The database-discipline parts:

- **Parameterize.** Use named (`@param`) query parameters via
  `ScalarQueryParameter` / `ArrayQueryParameter` on a `QueryJobConfig`, never
  f-string the value into the SQL — injection applies to BigQuery exactly as to
  Postgres, and interpolation also defeats BigQuery's query-result caching (every
  distinct query string is a cache miss → repeated cost).
- **Least privilege, dataset-scoped.** The service account a job uses gets a read
  role on the *specific dataset* plus a job-running role at the project level (as of
  this writing, `roles/bigquery.dataViewer` granted on the dataset, and
  `roles/bigquery.jobUser` to run query jobs) — not `dataEditor`/`admin`, not
  project-wide data access. Verify the exact role names against current GCP IAM docs;
  Google renames and adds roles. Scope the data role to the dataset, not the project.
- **Parameterization + dataset-scoped roles are the two controls that map 1:1 to the
  Postgres rules above** — same reasoning (no injection, least privilege), different
  surface.

---

## SQLite (inside portable single-file Python scripts)

SQLite shows up in the portable, `scp`-and-run scripts (example app family).
Treat it as a real database, not a flat file.

- **Parameterized queries via the DB-API `?` placeholder** (stdlib `sqlite3`). Same
  rule as everywhere; `sqlite3`'s default `execute()` will also reject multiple
  statements in one call, but never rely on that as your injection defense.
- **`PRAGMA foreign_keys = ON;` on every connection.** SQLite ships with foreign-key
  enforcement *off* by default and the pragma is **per-connection, not persisted** —
  forget it and `FK` constraints are silently ignored, letting orphaned rows
  accumulate with no error. Set it immediately after `connect()`.
- **WAL mode where concurrency matters** (`PRAGMA journal_mode = WAL;`): lets readers
  proceed during a write. Caveats that bite: SQLite is still **single-writer** —
  WAL does not give you concurrent writers, a second writer gets
  `database is locked` / `SQLITE_BUSY` (set a `busy_timeout`); WAL adds
  sidecar `-wal`/`-shm` files, so the DB is no longer one file to copy; and WAL
  relies on shared memory, so it **does not work over a network filesystem** (NFS,
  SMB) — it falls back or corrupts. For a strictly single-process script, the
  default rollback journal is fine — don't add WAL reflexively.
- **`chmod 600` the DB file if it holds sensitive data** (SKILL.md file-permissions
  rule). SQLite has no access control of its own — the filesystem is the only gate.
- **Back up via the online `Connection.backup()` API, not a live file copy.** `cp`-ing
  a SQLite file that's being written (especially in WAL mode, where committed data
  lives in the `-wal` sidecar until checkpoint) yields a torn, possibly corrupt
  snapshot. Use the backup API:

  ```python
  import sqlite3
  src = sqlite3.connect("data.db")
  dst = sqlite3.connect("backup.db")
  with dst:
      src.backup(dst)          # consistent online snapshot, even with writers active
  dst.close(); src.close()
  ```

---

## QA & quality gates

- **pytest against a real Postgres, with per-test rollback.** Don't mock the
  database for anything that exercises SQL, constraints, or RLS — mocks can't catch
  a wrong predicate or a missing policy. Run tests against an ephemeral Postgres
  (testcontainers, or a dedicated CI Supabase/Postgres service) and wrap each test
  in a transaction that **ROLLS BACK** in teardown, so tests are isolated and the
  schema stays clean. Where rollback can't capture the behavior (e.g. testing
  `COMMIT`-time triggers), use a fresh ephemeral schema per test instead.
- **Migration up + down tests.** CI applies every migration from empty to head
  (`up`), then — for migrations that ship a `down` — applies `down` back to empty,
  proving the rollback path isn't a lie. Also assert "no model/schema drift": the
  migrations reproduce exactly the schema the code expects.
- **Data-factory seeds, not hand-built dict literals.** Use a factory (factory_boy
  or small `make_tenant()` / `make_engagement()` helpers) so every test seeds valid,
  tenant-tagged rows. Hard-coded fixtures rot and quietly stop matching the schema.
- **Single-file scripts:** the SQLite-backed helpers are testable with the
  `conftest.py` argv-patch harness — seed an in-memory or `tmp_path` SQLite DB, run
  the helper, assert. See `references/testing-single-file.md`.

### The RLS isolation test (the one test you cannot skip)

Seed two tenants, then assert tenant A — connecting with A's JWT/role, NOT the
service role — **cannot read, update, or delete tenant B's rows**, and cannot insert
a row tagged as B. This is the executable proof that tenant isolation holds; add one
for every tenant table, and a new tenant table is not "done" until it has one.

```python
def test_tenant_a_cannot_read_tenant_b_rows(seed_two_tenants, as_tenant):
    with as_tenant("A") as cur:               # connect with A's claims, RLS enforced
        cur.execute("SELECT id FROM engagements")
        ids = {r[0] for r in cur.fetchall()}
    assert ids == seed_two_tenants["A_ids"]   # zero rows from tenant B
    assert seed_two_tenants["B_ids"].isdisjoint(ids)
```

Run the same shape for `UPDATE`/`DELETE` (assert `rowcount == 0` against B's rows)
and `INSERT` (assert a row tagged `tenant_id = B` is rejected by the `WITH CHECK`).

### SQL-level RLS testing with pgTAP (the gate that proves isolation in the database)

The pytest test above proves isolation *through the app*; **pgTAP proves it in the
database itself** — the layer that actually enforces it. The house gate
(`scripts/db-test.sh`, a required CI job — cross-ref `github-actions.md`) applies the
`dbmate` migrations to an ephemeral, pgTAP-enabled Postgres and runs the suite with
`pg_prove`.

- **The pattern per test file:** `BEGIN` → seed rows as the connecting **superuser**
  (which bypasses even `FORCE`'d RLS, so seeding always succeeds) → `SET LOCAL ROLE
  app_api` + set the identity GUCs (`set_config(..., true)`) so RLS is now enforced for
  the assertions → assert with pgTAP functions (`results_eq`, `throws_ok`, `is`) → a
  trailing `ROLLBACK` discards all seed + role/GUC state, so files are independent.
- **A superuser-run suite cannot verify the production RLS-bypass invariant — add a
  parity gate.** The seed-as-superuser convenience above hides a trap. When the gate
  applies the migrations *as the superuser*, the `SECURITY DEFINER` helpers are **owned by
  the superuser**, so they bypass RLS via **superuser status** — a property that **does not
  exist in production**. Managed Postgres (Cloud SQL, RDS) exposes no true superuser; there
  the helpers must be owned by a **non-superuser role carrying `BYPASSRLS`**, and it is
  *that attribute* — not superuser — that lets them through `FORCE`'d RLS. So the suite
  proves the *policies* are correct but **never proves the deployed ownership model bypasses
  RLS as required**: an owner role provisioned without `BYPASSRLS` passes every test, then —
  the first time it runs against real tenants — breaks onboarding and the recursion-avoiding
  definer helpers (they hit default-deny and error). This is the general hazard —
  **a test harness running with more privilege than production cannot verify a security
  invariant that depends on the privilege difference** (the superuser *masks* it). Close it
  with a **production-parity gate**: a second CI job that re-runs the *same* migrations + the
  *same* pgTAP suite under the prod model — the superuser pre-creates the extensions and a
  non-superuser `app_owner` (`LOGIN BYPASSRLS CREATEROLE`), then `dbmate` runs the migrations
  **as `app_owner`** so every definer helper is *owned by it*; the suite **must PASS**. Pair
  it with a **fail-first negative** (identical, but `app_owner` is `NOBYPASSRLS`) that **must
  FAIL**, and **invert** the assertion so a *passing* negative fails the gate — otherwise the
  positive proves nothing (a green that can't go red is not a test; see `testing.md` §3).
  Have the gate **assert its own preconditions** (`app_owner` is not a superuser, its
  `rolbypassrls` matches the scenario, and *every* `SECURITY DEFINER` helper is owned by it
  via `pg_proc.proowner`) rather than just print them, so a future mis-ownership refactor
  fails here instead of passing for the wrong reason. **Gotcha:** `CREATE EXTENSION` needs
  superuser, so pre-create `citext`/`pgcrypto` as the superuser first and confirm the
  migration's `create extension if not exists` no-ops cleanly for the non-superuser owner
  (a `NOTICE`, not a permission error). Mirror the eventual managed-DB runbook: the admin
  pre-creates the extensions + the `BYPASSRLS` owner; migrations run **as that owner**.
- **The suite is the executable spec for the tenant boundary.** The house suite covers
  two-tenant **isolation**, **matter/visibility ACL**, **append-only** (UPDATE/DELETE
  rejected), **key-secrecy** (one tenant can't read another's encrypted key material),
  **onboarding** (the `SECURITY DEFINER` bootstrap), and **default-deny** (no GUCs → zero
  rows). A new tenant table or policy isn't done until it has a pgTAP file.
- **The pgTAP image is test-only and must NEVER ship to prod.** Build it off the *same*
  `postgres:16` the stack uses, adding only `pgtap` + `pg_prove`; production runs Cloud
  SQL / plain Postgres with no test scaffolding. Don't let pgTAP leak into a production
  migration.

---

## Security testing

- **Scan for tenant tables missing RLS** — the highest-value automated check for the
  SaaS. Query the catalog and fail CI on any tenant table where RLS is off:

  ```sql
  SELECT c.relname
  FROM   pg_class c
  JOIN   pg_namespace n ON n.oid = c.relnamespace
  WHERE  n.nspname = 'public' AND c.relkind = 'r'
    AND  NOT c.relrowsecurity;        -- RLS not enabled
  ```

  Maintain an explicit allowlist of non-tenant tables (reference/lookup tables);
  anything else in the result set is a finding. Add a sibling check for
  `relforcerowsecurity = false` (RLS enabled but not forced — owner bypasses it).
- **Audit role grants for least privilege.** Confirm the app role is not an owner /
  not superuser / not `BYPASSRLS` (`SELECT rolname, rolsuper, rolbypassrls FROM
  pg_roles;`), and review `information_schema.role_table_grants` for grants wider
  than the app needs. Verify the `service_role` key is used only where intended.
- **Scan code and config for hardcoded connection strings and keys** before every
  commit — `git-secrets`/`gitleaks` patterns for `postgres://`, `postgresql://`,
  Supabase `service_role`/`anon` JWTs, and `sslmode=disable`. This is the secrets
  side of SKILL.md's pre-commit secrets check.
- **For app endpoints, the parameterization review is the primary defense against
  injection.** In `REVIEW:` mode, grep the diff for query-building by `f"… {…} …"`,
  `% (`, `.format(`, or `+` on SQL strings — every hit is a finding until proven to
  be an allowlisted identifier, not a value. `bandit`'s `B608`
  (`hardcoded_sql_expressions`) flags string-built SQL but only at **LOW
  confidence** and is not exhaustive; the human read is the gate.
- **`sslmode`** in every connection string must be `verify-full` for app traffic;
  flag `disable`/`allow`/`prefer`/`require` as findings (the first three may run
  plaintext; `require` encrypts but skips cert verification).
