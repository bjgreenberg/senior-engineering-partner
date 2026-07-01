# Google Cloud Platform Standards

Companion reference for the senior-engineering-partner skill.


GCP is where the example app + web frontend run (Cloud Run), where the planned multi-tenant Supabase SaaS will deploy (Cloud Run + Stripe + BYO-key), and where analytics live (BigQuery, a BI dashboard). This file is the standard for shipping anything to that account safely. It assumes the secrets/least-privilege/injection rules already in SKILL.md and does not repeat them — it applies them to GCP. Secrets are 1Password-first; on GCP the runtime store of record is Secret Manager. Shell examples are Bash/POSIX (the shipped default). Authenticate via ADC + impersonation — **never a downloaded service-account key file**.

Anti-hallucination note: gcloud surfaces evolve. The RULES and failure symptoms below are durable; before pasting any exact flag a user will run unattended, sanity-check it with `gcloud <group> <cmd> --help`. Where a specific is genuinely version-dependent it is flagged "verify against current docs."

---

## Project & environment topology (do this first)

- **One GCP project per environment, never one project for everything.** dev / stage / prod are separate projects (e.g. `app-dev`, `-stage`, `-prod`). IAM, quotas, and a fat-fingered `gcloud … delete` all stop at the project boundary — a single shared project means a dev test can read prod data and a bad command can nuke prod. Per-environment projects are the blast-radius wall.
- **Never carry `project` in a flag you retype.** Use named `gcloud` configurations so the active project/account/region is explicit and switchable:
  ```bash
  gcloud config configurations create app-prod
  gcloud config set project app-prod
  gcloud config set run/region us-central1
  gcloud config configurations activate app-prod   # switch envs
  gcloud config configurations list                      # confirm IS_ACTIVE before any mutating cmd
  ```
  Confirm the active config before every destructive command. The classic outage is running a `delete`/`deploy` against prod because the shell was still pointed there from the last session.
- **`--format` + `--filter` over grep/awk.** `gcloud … --format=json | jq` (or `--format='value(...)'`) is stable and parseable; screen-scraping the human table breaks when the layout changes. For scripted reads, prefer `--format=json`.

---

## Cloud Run (primary deploy target)

Applies to the example app, its web frontend, and the planned Supabase SaaS service.

1. **Discipline / best practices**
   - **Dedicated least-privilege runtime service account per service — NEVER the default compute SA.** `--service-account=app-run@<proj>.iam.gserviceaccount.com`. The default `*-compute@developer.gserviceaccount.com` carries broad project Editor-class reach; a container compromise then has it. Make a purpose-built SA, grant only the exact roles the service calls (e.g. `roles/secretmanager.secretAccessor` for the secrets it reads, `roles/cloudsql.client` / Supabase network egress as needed) and nothing else. This is the GCP application of the least-privilege rule in SKILL.md.
   - **Secrets come from Secret Manager at runtime, never baked at build.** Mount with `--set-secrets=DB_PASSWORD=supabase-db-pw:latest` (env) or as a mounted volume — do **not** `--set-env-vars` a plaintext secret and never `COPY` one into the image. A secret in `--set-env-vars` is visible in the revision config to anyone with `run.services.get`, and a secret baked into a layer is permanent in Artifact Registry history. For BYO-key tenants, the tenant key is fetched per-request from the secret store, never logged.
   - **Tune scaling/concurrency/CPU deliberately.** `--min-instances` (0 for the bursty analyzer to avoid idle spend; ≥1 only where cold-start latency is unacceptable), `--max-instances` (a real cap — an open-ended max + a request storm or retry loop is a runaway-bill event), `--concurrency` (default 80; drop toward 1 for CPU-bound or non-thread-safe request handling — the example app doing heavy per-request work wants low concurrency), and `--cpu`/`--memory` sized to the workload. **`--no-cpu-throttling` (CPU always allocated) only if you run background work between requests** — it bills CPU for the instance's whole life, not just during requests; default (throttled) is cheaper and correct for request/response services.
   - **Ingress + auth: locked by default, public only by intent.** `--ingress=internal-and-cloud-load-balancing` for anything fronted by a load balancer / not meant for the open internet; `--no-allow-unauthenticated` so callers must present an IAM identity. Use `--allow-unauthenticated` **only** for a deliberately public endpoint (e.g. a public web frontend if it's meant to be reachable). For the Supabase SaaS, terminate at a load balancer with Cloud Armor and keep the service ingress internal.
   - **Revisions are your rollback.** Each deploy is an immutable revision. Use `--no-traffic` + `--tag=canary` to deploy without shifting traffic, validate the tagged URL, then `gcloud run services update-traffic --to-revisions=<rev>=100`. Instant rollback = shift traffic back to the prior known-good revision (`--to-revisions`). Don't fix-forward a broken prod deploy when a one-command traffic shift restores service.
   - **Cloud Run Jobs vs Services.** A **Service** answers HTTP and scales on requests (the app's web frontend, the SaaS API). A **Job** runs to completion and exits (a batch job over a corpus, a scheduled BigQuery ETL, a one-off migration) — triggered by Cloud Scheduler or manually, no request listener. Don't model a finite batch task as an always-listening Service.
   - **Structured JSON logs to Cloud Logging.** Write single-line JSON to stdout/stderr; Cloud Run ingests it into Cloud Logging and parses `severity`, `message`, and any fields. This is the GCP rendering of the structured-logging rule in SKILL.md — `severity` replaces the local level, the platform handles rotation/retention (so the `~/Library/Logs` `tail -n 500` pattern is for local scripts, not Cloud Run). **Never log secrets, tenant BYO-keys, or full PII** at any severity. For request correlation, propagate `X-Cloud-Trace-Context` into a `logging.googleapis.com/trace` field.

2. **QA & quality gates**
   - Build with a pinned base image consumed **by digest** (`<region>-docker.pkg.dev/...@sha256:…`), not `:latest` (see Artifact Registry below). The example app's pinned `requirements.txt` (SKILL.md dependency rule) is the lockfile the image must reflect.
   - In CI (GitHub Actions, `<org>/*` PR-flow with required checks): authenticate via **Workload Identity Federation**, not a stored key (see IAM). Gate the merge on container vulnerability scan results from Artifact Registry plus the existing `bandit` / `ShellCheck` / `npm audit` gates.
   - Deploy from CI only after checks are green; deploy with `--no-traffic --tag` first so the PR can be smoke-tested at the tagged URL before promotion.

3. **Test cases**
   - **Pre-deploy, local:** run the container locally and hit `/` + health endpoint; assert it binds the `PORT` env var Cloud Run injects (a hardcoded port = container starts but receives no traffic; symptom: "The user-provided container failed to start and listen on the port defined by the PORT=8080 environment variable").
   - **Auth boundary:** assert an unauthenticated request to a `--no-allow-unauthenticated` service returns **HTTP 403**, and an authenticated one (`curl -H "Authorization: Bearer $(gcloud auth print-identity-token)"`) returns 200.
   - **Secret wiring:** assert the service reads the secret from the mounted path/env at runtime and that the value is **absent** from `gcloud run services describe … --format=json` output (catches an accidental `--set-env-vars` leak).
   - **Scaling guardrail:** load-test toward `--max-instances` and confirm it caps (not unbounded); confirm `--min-instances=0` services actually scale to zero when idle.
   - **Rollback drill:** deploy a deliberately broken revision with `--no-traffic`, confirm prod traffic is unaffected, then practice the traffic-shift rollback.

4. **Security testing**
   - Audit which services are public: `gcloud run services list --format='value(metadata.name)'` then for each check the IAM policy for `allUsers`/`allAuthenticatedUsers` on `roles/run.invoker`:
     ```bash
     gcloud run services get-iam-policy <svc> --region=<r> \
       --format='table(bindings.role, bindings.members)' | grep -E 'allUsers|allAuthenticatedUsers'
     ```
     A hit that isn't a *deliberately* public endpoint is a finding.
   - Confirm `--no-allow-unauthenticated` + correct `--ingress` on every internal service; confirm the runtime SA is the dedicated one, not `*-compute@`.
   - Feed the service URL through the input-validation rules in SKILL.md (validate webhook payloads, canonicalize paths). For the Supabase SaaS, the auth/tenant-isolation boundary is RLS — see the BigQuery/Supabase note and the separate database standard.

---

## Cloud Storage (GCS)

1. **Discipline / best practices**
   - **Uniform bucket-level access (UBLA), never legacy object ACLs.** Create buckets with `--uniform-bucket-level-access`. Per-object ACLs are the classic way a single object silently becomes world-readable inside an otherwise-locked bucket; UBLA makes IAM the *only* access surface so you can reason about a bucket from one policy.
   - **Public Access Prevention enforced everywhere — EXCEPT documented intentional-public buckets.** Default new buckets to `--public-access-prevention=enforced`. The discipline is **not** "blanket-lock every bucket"; it is "every bucket is either locked or carries a written, reviewed reason it is public."
   - **The `public-assets` bucket is public by design and must NOT be flipped private.** BI dashboards hotlink its raw object URLs; making it private (PAP enforced, or removing `allUsers:objectViewer`) returns 403 on those URLs and **breaks production dashboards**. It is the canonical documented exception: PAP is intentionally `inherited`/unenforced, `allUsers` has `roles/storage.objectViewer`, and that grant is recorded as intentional. Treat its object names as a published API — do not rename, do not bulk-relock. Any "tighten all public buckets" sweep must explicitly skip it.
   - **Object versioning** on buckets holding state you can't regenerate: `gcloud storage buckets update gs://<bucket> --versioning` (legacy equivalent `gsutil versioning set on gs://<bucket>`) so an overwrite or delete is recoverable. Versioning + lifecycle (below) together — unbounded versions accrue cost, since every noncurrent version bills at the live rate.
   - **Lifecycle rules** to control cost and retention: transition cold objects to Nearline/Coldline, expire scratch/temp prefixes (and prune old noncurrent versions on versioned buckets). Apply via a JSON lifecycle config (`gcloud storage buckets update gs://<bucket> --lifecycle-file=lifecycle.json`) — never hand-delete to manage cost.
   - **Signed URLs for temporary third-party access** instead of making an object or bucket public. A V4 signed URL grants time-boxed access to one object and expires — the right tool when someone needs "a link to this file," reserving actual public buckets for the deliberate hotlinking case like public-assets.
   - **CMEK** (customer-managed Cloud KMS keys) optionally for buckets holding sensitive output, when key-rotation/control requirements exceed Google-managed default encryption.

2. **QA & quality gates**
   - Bucket creation goes through IaC or a reviewed script, not console click-ops, so UBLA + PAP settings are consistent and diffable. New-bucket default in any helper script: UBLA on, PAP enforced.
   - CI/audit step: enumerate buckets and assert PAP state matches an allowlist (the allowlist contains exactly `public-assets` and any other reviewed exception).

3. **Test cases**
   - Assert a non-exception bucket has PAP enforced and UBLA enabled: `gcloud storage buckets describe gs://<bucket> --format='value(iamConfiguration.publicAccessPrevention,iamConfiguration.uniformBucketLevelAccess.enabled)'` returns `enforced` and `True`.
   - Assert `public-assets` is still publicly readable (a HEAD on a known object returns 200) — a regression test that catches an accidental lockdown.
   - Signed URL: assert a freshly generated URL serves the object and that the **same URL 403s after expiry**.
   - Versioning: overwrite an object, assert the prior generation is still retrievable.

4. **Security testing — public-bucket audit (respecting the exception)**
   ```bash
   for b in $(gcloud storage buckets list --format='value(name)'); do
     pap=$(gcloud storage buckets describe "gs://$b" \
            --format='value(iamConfiguration.publicAccessPrevention)')
     iam=$(gcloud storage buckets get-iam-policy "gs://$b" --format=json \
            | jq -r '.bindings[]?.members[]?' | grep -E 'allUsers|allAuthenticatedUsers' || true)
     if [[ -n "$iam" && "$b" != "public-assets" ]]; then
       echo "FINDING: $b is publicly granted ($iam), PAP=$pap"
     fi
   done
   ```
   Note the PAP field is nested under `iamConfiguration.publicAccessPrevention` — a top-level `value(publicAccessPrevention)` returns empty and silently hides the state. `public-assets` is allowlisted by name. Any *other* bucket with an `allUsers`/`allAuthenticatedUsers` binding or unenforced PAP is a finding to triage, not auto-remediate (auto-relocking is exactly the action that would have broken a BI dashboard). Cross-check findings against Security Command Center's "Public bucket" detector.

---

## BigQuery

1. **Discipline / best practices**
   - **Parameterized queries, always — never string-interpolate values into SQL.** This is the SKILL.md injection rule applied to BQ: `bq query --use_legacy_sql=false --parameter='id:STRING:…'`, or named/positional parameters in the Python client (`bigquery.ScalarQueryParameter`). A tenant id or user-supplied filter concatenated into the query string is an injection vector and a cross-tenant data-leak vector.
   - **Authorized views + column-level security over broad table grants.** Don't grant analysts `roles/bigquery.dataViewer` on a raw table with sensitive columns. Expose a curated **authorized view** (or materialized view) in a separate dataset and grant on that; use **policy tags / column-level security** to gate sensitive columns. Grant at the **dataset** level, not per-table sprawl.
   - **Partition + cluster for cost and speed.** Partition large tables (commonly by ingestion date / an event-date column) and cluster on the high-selectivity filter columns. An unpartitioned table forces full scans — you pay for every byte every query.
   - **Estimate bytes before you run.** `bq query --dry_run --use_legacy_sql=false '<sql>'` reports bytes that *would* be billed without running. Make this reflexive for any new or ad-hoc analytical query.
   - **`--maximum_bytes_billed` guardrail** on jobs (or `maximum_bytes_billed` in the client) so a runaway `SELECT *` over a huge table fails fast instead of billing a fortune. Set a per-environment ceiling.
   - **Never `SELECT *`** on wide/large tables — BigQuery bills by columns scanned; select only the columns you need. `SELECT *` defeats column pruning and inflates cost.

2. **QA & quality gates**
   - Lint SQL for `SELECT *` and missing partition filters in review; require a `--dry_run` byte estimate in the PR description for any new scheduled query.
   - Scheduled queries / ETL jobs run under a dedicated SA with dataset-scoped IAM, not a human's ADC and not Editor.

3. **Test cases**
   - Run every parameterized query against a value containing `'; DROP`/`--`/`' OR '1'='1` and assert it is treated as a literal (no error, no extra rows) — proves parameterization, not concatenation.
   - Assert a partition-filtered query scans materially fewer bytes than the unfiltered form (compare `--dry_run` totals).
   - Assert `--maximum_bytes_billed` actually aborts a deliberately oversized query.
   - For the multi-tenant analytics path: assert a query scoped to tenant A returns zero tenant-B rows (the analytics analogue of the Supabase RLS isolation test).

4. **Security testing**
   - `gcloud asset search-all-iam-policies` / dataset IAM review: confirm no broad `roles/bigquery.dataViewer` on datasets holding sensitive columns; confirm policy tags are attached where required.
   - Confirm `allUsers`/`allAuthenticatedUsers` appear nowhere in any dataset IAM policy.

---

## IAM (the account-wide control plane)

1. **Discipline / best practices**
   - **Least privilege, predefined roles — never primitive `roles/owner` or `roles/editor` on a service account.** Owner/Editor are project-wide god-mode; a compromised SA holding Editor can read every bucket, every secret, every dataset. Grant narrow predefined roles (`roles/run.invoker`, `roles/secretmanager.secretAccessor`, `roles/storage.objectViewer`) scoped to the specific resource. Custom roles when no predefined role fits tightly.
   - **No long-lived service-account key files. Ever.** A downloaded `key.json` is a permanent, exfiltratable credential — the exact failure that leaked creds into `founders-journey`/`succession-planning` (see the PR-flow memory). Instead:
     - **CI / GitHub Actions →** Workload Identity Federation (federate the GitHub OIDC token to a GCP SA; no stored key).
     - **Local dev →** `gcloud auth application-default login` (ADC) + `--impersonate-service-account=<sa>` to *act as* a service account short-term without ever holding its key.
     - **GCP-to-GCP →** attached SAs + ADC (the workload already has an identity).
     - If a static credential is genuinely unavoidable, it lives in 1Password / Secret Manager and is rotated — never committed, never in an env file in the repo.
   - **IAM Recommender** to shrink over-grants: it flags roles a principal hasn't used and proposes a tighter role. Review and apply periodically — over-grants accrete silently.
   - **Org policies as guardrails:** `iam.disableServiceAccountKeyCreation` (structurally blocks the key-file footgun above), `iam.allowedPolicyMemberDomains` (domain-restricted sharing — only org-domain principals), and `iam.automaticIamGrantsForDefaultServiceAccounts` (block the default SA's broad auto-grant). Org policy is the wall that makes "don't create SA keys" enforced rather than aspirational.

2. **QA & quality gates**
   - Any new role grant is reviewed; the PR/commit states *why* the principal needs *that* role on *that* resource. No `roles/editor` grants pass review without an explicit, exceptional justification.
   - WIF is the default auth for every new CI pipeline; a PR that adds a `key.json` path is rejected.

3. **Test cases**
   - Negative test: a service's runtime SA is **denied** an action outside its role set (e.g. the analyzer SA cannot read an unrelated bucket) — proves the grant is actually narrow.
   - Impersonation works for an intended principal and fails for one without `roles/iam.serviceAccountTokenCreator`.

4. **Security testing**
   - **IAM Policy Analyzer** — "who can do what on which resource": find every principal that can access a sensitive bucket/dataset, and every principal holding Owner/Editor.
     ```bash
     gcloud asset analyze-iam-policy \
       --organization=<ORG_ID> \
       --identity-selector …    # verify exact selector flags against current docs: gcloud asset analyze-iam-policy --help
     ```
   - **Audit for SA keys:** `gcloud iam service-accounts keys list --iam-account=<sa> --managed-by=user` across SAs — any **user-managed** key listed is a finding (Google-managed system keys are excluded by the filter and are fine). The goal state is zero user-managed keys.
   - **IAM Recommender:** `gcloud recommender recommendations list --project=<proj> --location=global --recommender=google.iam.policy.Recommender` to list and act on over-grant recommendations.
   - Confirm the org policies above are enforced (`gcloud org-policies describe <constraint> --project=<proj>` / `gcloud org-policies list`).

---

## Secret Manager

- **The runtime store of record for cloud secrets** (1Password remains the human/source-of-truth vault; values are injected/synced into Secret Manager for runtime). **Never** in code, env files committed to the repo, image layers, or `--set-env-vars` plaintext. This extends the SKILL.md secrets rule onto GCP.
- **Per-secret IAM.** Grant `roles/secretmanager.secretAccessor` on the *specific secret*, to the *specific runtime SA* that needs it — not project-wide. The analyzer's DB password secret is readable only by the analyzer's SA.
- **Versioning.** Secrets are versioned; reference `:latest` for rolling rotation or pin a version where you need stability. Rotation = add a new version + disable the old, no redeploy of the secret name.
- **Cloud Run consumes it via `--set-secrets`** (env or mounted volume), so the plaintext never lands in the service config. For BYO-key SaaS tenants, the per-tenant key is a per-tenant secret with per-tenant accessor IAM.
- **Security test:** confirm no human principals and no broad SAs hold `secretAccessor` on production secrets; confirm secret values never appear in Cloud Logging (grep the logs for a canary substring and expect zero hits).

---

## Artifact Registry

- **Store container images and language packages here** (it supersedes Container Registry/gcr.io). One repo per purpose/environment.
- **Enable vulnerability scanning.** Artifact Registry / Container Analysis scans pushed images for CVEs. Treat HIGH/CRITICAL findings as merge/deploy blockers — the GCP analogue of the `bandit`/`npm audit` gates in SKILL.md.
- **Consume images by digest, pin tags as immutable.** Deploy `…@sha256:<digest>`, not `:latest` — `:latest` is a moving target and makes a Cloud Run revision non-reproducible (you can't prove which bytes ran). Enable **immutable tags** on the repo so a pushed tag can't be silently repointed under you.
- **Per-repo IAM:** push from CI (`roles/artifactregistry.writer`), pull from the Cloud Run runtime SA (`roles/artifactregistry.reader`) — not project-wide grants.
- **Security test:** assert the deployed revision references a digest, not a floating tag; assert no image with an unresolved HIGH/CRITICAL CVE is promoted to prod; confirm immutable tags are enabled.

---

## gcloud CLI hygiene (summary)

- **Named configurations per project/env**; activate and confirm before any mutating command (see topology section). Never trust the ambient active config for a destructive op.
- **ADC + `--impersonate-service-account`** for local work; **WIF** for CI. No `GOOGLE_APPLICATION_CREDENTIALS` pointing at a downloaded key.
- **`--format=json` / `--format='value(...)'`** for anything scripted; **`--dry_run`** (bq) and Cloud Run `--no-traffic --tag` to preview before committing real changes.
- Destructive commands (`delete`, traffic shifts, IAM changes) get an explicit project echo first: `gcloud config get-value project` and confirm it's the intended environment.

---

## Account-wide security testing (run periodically)

- **Security Command Center** — the console for cross-project findings: public buckets, public Cloud Run services, over-privileged SAs, user-managed SA keys, open firewall rules. First stop for "what's exposed in this account." Triage findings; do not blanket-auto-fix (the public-bucket detector will flag `public-assets` — that one is the documented intentional exception, not a vuln).
- **Cloud Asset Inventory** — `gcloud asset search-all-resources` / `search-all-iam-policies` / `gcloud asset export` for a point-in-time snapshot of every resource and binding; diff over time to catch drift. Basis for the public-bucket audit and the IAM analysis above.
- **Public-bucket audit** — the GCS script above, with `public-assets` allowlisted by name.
- **IAM Policy Analyzer + IAM Recommender** — find over-grants and Owner/Editor holders; shrink them.
- **SA-key audit** — enumerate user-managed keys across SAs (`keys list --managed-by=user`); goal state is zero (org policy `iam.disableServiceAccountKeyCreation` makes it stick).
- Confirm findings are routed to a human (and, for unattended jobs, surfaced per the SKILL.md monitoring/alerting rules) — a security report nobody reads is not monitoring.

---

### Cross-references

- Secrets-never-in-code, input validation, injection prevention, structured logging, least privilege, FDA-never-to-system-interpreters — `SKILL.md` (this file applies them to GCP; it does not restate them).
- Local LaunchAgent `.app`/TCC packaging for any Mac-side tool that *calls* gcloud — `references/macos-app-bundles.md`.
- More-than-one-writer rules for the repos that deploy here (`<org>/*` PR-flow, branch protection, required CI, WIF auth in CI) — `references/multi-agent-coordination.md`.
- Single-file testing strategy for the example app that deploys to Cloud Run — `references/testing-single-file.md`.
- Supabase Postgres + Row-Level Security tenant-isolation specifics for the SaaS — covered by the database standard / SaaS plan, not duplicated here (this file stops at the GCP/Cloud Run boundary).
