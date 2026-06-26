# Infrastructure as Code (Terraform on GCP)

Companion reference for the senior-engineering-partner skill.


Every piece of cloud infrastructure for this stack is defined in Terraform and reaches GCP only through `terraform apply` — **zero console click-ops.** The the example SaaS review found NONE: no deploy artifacts, no IaC, the Cloud Run service / Cloud SQL instance / secrets / service accounts implied by `gcp.md` and `github-actions.md` exist only as prose. This file closes that gap. It is the *provisioning* layer; `gcp.md` is the resource-level standard for what each resource's settings must be, and `github-actions.md` is how `plan`/`apply` run in CI. Terraform does not restate those rules — it encodes them as code.

Anti-hallucination note: provider schemas evolve and resource/argument names are version-specific. The RULES, structure, and failure symptoms below are durable. Before pasting any exact resource type, argument, or attribute a user will run, **verify it against the current `hashicorp/google` provider docs** (`terraform providers schema -json | jq …`, or the registry docs for your pinned provider version) — a plausible-but-wrong argument name fails `terraform validate` at best and silently no-ops at worst. Pin the provider; don't float it.

---

## Repo & module structure (no copy-paste between environments)

- **Reusable modules + per-environment composition.** A module defines a resource shape once (e.g. a `cloud_run_service` module taking name, image, SA, scaling, secrets as inputs); each environment *composes* modules with its own variable values. The environments differ in `.tfvars`, never in copy-pasted resource blocks — copied HCL is config drift waiting to happen (a fix lands in prod, never backported to stage).
- **Layout — separate per-environment root dirs over workspaces, for this stack.** Each env is its own root module with its own backend (its own state, its own GCP project per `gcp.md` "one project per environment"):
  ```
  infra/
  ├── modules/
  │   ├── cloud_run_service/      # the API (HTTP, request-scaled)
  │   ├── cloud_run_job/          # batch extraction (run-to-completion)
  │   ├── cloud_sql_postgres/     # private-IP instance + db + user
  │   ├── secret/                 # a Secret Manager secret + accessor IAM
  │   ├── runtime_sa/             # a least-privilege runtime service account
  │   ├── evidence_bucket/        # GCS bucket, PAP enforced, CMEK
  │   ├── github_oidc/            # Workload Identity pool + provider + deployer SA
  │   └── monitoring/             # alert policies + notification channel
  └── envs/
      ├── dev/    { main.tf, backend.tf, dev.tfvars }
      ├── stage/  { … }
      └── prod/   { … }
  ```
  **Why dirs over `terraform workspace` here:** workspaces share one backend and one set of provider creds, and the only thing distinguishing prod from dev is the workspace name selected by ambient CLI state — the exact "wrong env because the shell was pointed there" footgun `gcp.md` warns about. Separate root dirs give each env a distinct backend key, distinct project, and a distinct CI job — the blast-radius wall extends into the IaC.
- **Pin everything that floats.** `required_version` for Terraform, `required_providers` with a `~>`-pinned (or exact) `hashicorp/google` version, and a committed `.terraform.lock.hcl` (provider checksum lock — the IaC analogue of `requirements.txt`/`package-lock.json` in SKILL.md's dependency rule). Run `terraform init -upgrade` deliberately, never let provider versions drift between machines.

---

## Remote state (GCS backend with locking — never local, never committed)

- **State lives in a GCS backend, never on a laptop and never in git.** Local `terraform.tfstate` is unshareable, unlocked, and a single `rm` from gone; a committed state file leaks every ID and (often) secret value it captured. `.gitignore` `*.tfstate*`, `.terraform/`, and `*.tfvars` that hold secrets.
  ```hcl
  # envs/prod/backend.tf — verify exact backend args against current provider docs
  terraform {
    backend "gcs" {
      bucket = "app-tfstate-prod"   # a dedicated, locked, versioned bucket
      prefix = "cloud-run-api"                 # one prefix per root module
    }
  }
  ```
- **State locking is non-negotiable for any shared/CI-run state.** Two concurrent `apply`s against one unlocked state corrupt it. The GCS backend acquires a lock object for the duration of an operation — symptom of a contended lock is `Error acquiring the state lock` naming the holder; only `force-unlock <LOCK_ID>` after you've **confirmed** no apply is actually running (a stuck CI job). Never `force-unlock` reflexively. (Verify the current locking mechanism for your backend/provider version against the docs.)
- **The state file IS sensitive — treat it like a secret.** State captures resource IDs, connection details, generated passwords, and any `sensitive` value in plaintext. Lock the state bucket down hard:
  - UBLA on, **public-access-prevention enforced** (this bucket is *never* the `public-assets` exception — `gcp.md`), object **versioning on** (a corrupt apply is recoverable by rolling back a generation).
  - IAM scoped to exactly the human admins + the CI deployer SA — `roles/storage.objectAdmin` on that one bucket, nobody else. No `allUsers`, no broad project grants.
  - Separate state bucket (or at least prefix) per environment; prod state is readable only by prod's deployer identity.

---

## Secrets in Terraform (reference, don't embed; never emit)

- **Reference Secret Manager — never hardcode a secret value in HCL or a committed `.tfvars`.** Terraform *creates* the secret container and IAM; the *value* is written out-of-band (1Password → `gcloud secrets versions add`, or a tightly-scoped manual step), or the app fetches it at runtime via `--set-secrets` (`gcp.md`). The pattern: Terraform owns `google_secret_manager_secret` + the `secretAccessor` binding for the runtime SA; the plaintext never appears in a `.tf` file. (Verify resource/argument names against current provider docs.)
- **Mark every secret-bearing variable and output `sensitive = true`.** It keeps the value out of `plan`/`apply` console output and CI logs (SKILL.md "never log secrets" reaches CI). Note `sensitive` redacts *display* only — it does **not** keep the value out of state.
- **Never emit a secret as an `output`.** An output is stored in state in plaintext and is readable by anything that can read state or `terraform output`. If a downstream module needs a secret, pass the *secret reference* (the resource ID / version name), not the value.
- **Avoid putting secret *values* in state at all where possible.** A resource that takes a plaintext secret as an argument (a generated DB password, an inline secret-version payload) writes that value into state forever. Prefer: let the value be set outside Terraform and have Terraform reference it; or accept it's in state and lock the state bucket accordingly (above). If Terraform must generate a credential (`random_password`), that value lives in state — that is the strongest reason the state bucket is treated as a secret store.

---

## Least privilege + auth (the Terraform SA is the most powerful identity you have)

The identity that runs `apply` can create, mutate, and **delete** every resource in the project — it is strictly more powerful than any runtime SA. Scope and authenticate it accordingly.

- **Run `plan`/`apply` from CI via OIDC → Workload Identity Federation — no downloaded SA key.** GitHub Actions mints a short-lived token federated to the deployer SA (`google-github-actions/auth` + `id-token: write`); there is **no long-lived `*.json` key** in repo secrets (`gcp.md` IAM "never long-lived SA keys"; `github-actions.md` deploy stage). The WIF pool/provider/deployer SA are themselves a Terraform module (`modules/github_oidc`) — bootstrapped once, then self-managed.
- **Scope the deployer SA tightly, per environment.** It needs the roles to manage exactly the resources in *its* env's state (Cloud Run admin, Cloud SQL admin, Secret Manager admin, IAM admin scoped to the project's own SAs, storage admin on the state + evidence buckets) — granted at the **project** level for that env's project, never `roles/owner`, never org-wide. Prod's deployer cannot touch dev and vice versa (separate projects, separate WIF bindings). The `iam.disableServiceAccountKeyCreation` org policy from `gcp.md` structurally blocks anyone from minting a key for it.
- **Local dev uses ADC + impersonation, never a key.** `gcloud auth application-default login` then impersonate the (dev-only) deployer SA — `gcloud config set auth/impersonate_service_account <dev-deployer-sa>` or the provider's `impersonate_service_account` setting (verify the exact argument against current provider docs). A human never holds the deployer SA's key because it never exists.

---

## Plan-review is the change gate (the plan IS the review artifact)

This is how IaC inherits SKILL.md's PR-flow: the diff a human reviews is `terraform plan`.

- **`terraform plan` runs in CI on the PR; a human reads it before merge.** The plan is posted to / attached to the PR (saved with `-out=tfplan` and rendered) so a reviewer sees *exactly* what will change — created, updated, **destroyed** (replacements are the dangerous line — a `-/+ must be replaced` on a Cloud SQL instance means data loss; a reviewer must catch it). A plan with surprise destroys does not get approved.
- **`apply` happens only after merge, against the saved plan, with approval.** Apply the *reviewed* `tfplan` artifact (`terraform apply tfplan`), so what merges is byte-for-byte what was reviewed — not a fresh plan computed at apply time that may have drifted. Production `apply` is gated on a manual approval step (GitHub Environments protection), mirroring branch protection: agent-authored infra PRs get a **human review before apply**, never blind self-apply (SKILL.md team-model: a human reviews every agent-authored PR; sensitive paths — anything touching prod state, IAM, or the evidence bucket — warrant a second approval).
- **No out-of-band `apply` from a laptop against prod.** Local `apply` is for a dev sandbox only. Prod changes flow through the PR → reviewed plan → approved apply path, or the state and reality silently diverge (drift, below).

---

## The resources this stack provisions

All in Terraform; each must satisfy its `gcp.md` settings. (Resource type names below are illustrative of the *hashicorp/google* provider — **verify each against the current provider docs** before use; do not trust the exact name from memory.)

| Resource | Module | Must encode (cross-ref) |
|---|---|---|
| Cloud Run **Service** (the API) | `cloud_run_service` | dedicated runtime SA (not default compute), `--set-secrets` for `DATABASE_URL`/model/Firebase creds, `min-instances=0`, a real `max-instances` cap, low concurrency for CPU-bound work, `no-allow-unauthenticated` + correct ingress (`gcp.md` Cloud Run) |
| Cloud Run **Job** (batch extraction) | `cloud_run_job` | run-to-completion (off the request path — `secure-data-processing.md` §1: hostile-file extraction must not exhaust the API's request budget), its own least-privilege SA, resource/time bounds |
| Cloud SQL **Postgres** | `cloud_sql_postgres` | smallest viable tier, **private IP / connector** (no public IP), automated backups + PITR, `DATABASE_URL` into Secret Manager — never an output; **this is self-managed Cloud SQL, not Supabase** |
| **Secret Manager** secrets | `secret` | `DATABASE_URL`, model key, Firebase creds, per-tenant BYO keys; per-secret `secretAccessor` to the one runtime SA that reads it (`gcp.md` Secret Manager) |
| **Artifact Registry** repo | (env root) | one repo per env, vuln scanning on, immutable tags; deploy images by digest (`gcp.md`) |
| Runtime **service accounts** | `runtime_sa` | one per service/job, narrow predefined roles only — **never the default compute SA**, never Owner/Editor (`gcp.md` IAM) |
| **GCS evidence bucket** | `evidence_bucket` | UBLA on, **public-access-prevention enforced**, CMEK, versioning + lifecycle — the deliberate *opposite* of the public `public-assets` exception (`gcp.md` GCS; `secure-data-processing.md` §3) |
| **KMS** keyring + keys | `evidence_bucket` / `secret` | envelope-encrypt tenant BYO keys (`tenant_api_keys.key_ciphertext` + `kms_key_version` — `databases.md`/`secure-data-processing.md` §3) and CMEK the evidence bucket; rotation schedule encoded |
| **Workload Identity** pool/provider + deployer SA | `github_oidc` | GitHub OIDC federation for CI deploys, repo-scoped attribute condition so only this repo's workflows can assume it (`github-actions.md`) |
| **Cloud Monitoring** alert policies | `monitoring` | error-rate / latency / Cloud SQL-CPU / budget alerts → a notification channel (cross-ref `observability-and-incident-response.md`) |

---

## Cost lives in the IaC too (local-first → GCP, scale-to-zero)

The local-first → GCP strategy (develop on docker-compose + plain `postgres:16`, deploy to GCP to get scale-to-zero) is half-encoded here — the IaC is what makes the GCP half cheap:

- **Cloud Run `min-instances = 0`** on the bursty analyzer (scale to zero — no idle billing; `gcp.md`). Set `min-instances ≥ 1` only where a documented cold-start SLA forbids zero.
- **Request-based scaling with a real `max-instances` cap** — an open-ended max + a retry storm is a runaway-bill event (`gcp.md`; cost-as-security in `secure-data-processing.md` §2).
- **Smallest viable Cloud SQL tier**, scaled up only on evidence, with a budget alert wired in `monitoring` so a tier bump or a runaway query surfaces before the invoice does.
- **Lifecycle rules** on the evidence + state buckets (expire scratch prefixes, prune noncurrent versions) so storage cost stays bounded (`gcp.md` GCS).

---

## IaC QA, quality gates & security

Wire these as CI jobs (`github-actions.md` — one gate per provable claim, least-privilege `permissions`, same script locally and in CI):

1. **`terraform fmt -check -recursive`** — canonical formatting; a diff fails the gate (catch it locally with `terraform fmt -recursive`).
2. **`terraform validate`** — config is internally consistent and provider-valid (run per root module after `init`).
3. **`tflint`** — provider-aware linting beyond `validate`: deprecated arguments, invalid instance/tier values, missing-required, naming rules. Enable the Google ruleset.
4. **A security scanner on every PR.** Use **`trivy config`** (which absorbed the former tfsec engine) **or `checkov`** — *verify which you've standardized on and pin its version*; do not assume a standalone `tfsec` binary is current. It flags public buckets, unencrypted resources, over-broad IAM, missing PAP, plaintext secrets in HCL — the static analogue of the runtime audits in `gcp.md`. Fail the gate on its findings; document any inline waiver with *why* (SKILL.md's "an undocumented skip is a hidden waiver").
5. **The reviewed `plan`** (above) is itself the highest-value gate — a human-read diff of every create/update/**destroy**.
6. **Drift detection — a scheduled `terraform plan`.** Console click-ops, manual hotfixes, or out-of-band changes make reality diverge from state; a nightly/weekly `plan` (read-only, in CI) that reports a non-empty diff is the dead-man's-switch (SKILL.md monitoring) for "someone changed infra outside Terraform." A non-empty scheduled plan is an alert, not noise — reconcile it (import the change into code, or revert it) promptly. Everything through Terraform means a drift finding is always a bug to fix, never the normal way changes land.

### Test cases (what to verify about the infra itself)

- **Auth boundary:** the deployed `no-allow-unauthenticated` Service returns HTTP 403 unauthenticated, 200 with a valid identity token (`gcp.md` test cases) — the IaC produced the locked config.
- **Secret wiring:** the secret value is **absent** from `terraform show`/state-readable outputs and from `gcloud run services describe --format=json` (catches an accidental `--set-env-vars` leak or a secret emitted as an output).
- **No public exposure:** the evidence bucket and the **tfstate bucket** both report PAP `enforced` + UBLA `True` (`gcp.md` GCS script); neither carries an `allUsers` binding.
- **Least-privilege deployer:** a negative test that the runtime SA (and the deployer SA) is *denied* an action outside its role set (`gcp.md` IAM test cases) — proves the grants are actually narrow.
- **Replacement safety:** a plan that would `-/+` replace the Cloud SQL instance or the evidence bucket is caught in review and blocked — these are data-loss operations, not routine updates.
- **No long-lived keys:** assert zero user-managed SA keys exist (`gcloud iam service-accounts keys list --managed-by=user` per `gcp.md`) — the WIF + org-policy path means there should be none.

### Security testing

- Run the config scanner (#4) in CI and periodically over the whole `infra/` tree; route findings to a human (SKILL.md monitoring), not auto-fix — the `public-assets`-style intentional exception must not be "remediated" by a blanket sweep (that public bucket is *not* in this Terraform anyway; the evidence bucket is its opposite).
- Confirm the state bucket's IAM, PAP, and versioning by the same `gcp.md` public-bucket audit (it must show as **not** public and locked to the admin + deployer identities).
- Confirm WIF attribute conditions actually restrict assumption to this repo's workflows (a misconfigured `attribute.repository` condition lets any GitHub repo's OIDC token assume the deployer SA — a critical finding; verify the condition syntax against current docs).
- Map the IaC controls to SOC 2 change-management evidence: every infra change is a reviewed PR with a recorded plan and an approved apply — the audit trail is the git history (cross-ref `compliance.md`).

---

### Cross-references

- Resource-level settings for everything provisioned here (Cloud Run scaling/ingress/secrets, GCS UBLA/PAP, Cloud SQL, Secret Manager IAM, Artifact Registry, the no-SA-keys → WIF rule, the `public-assets` public exception this file is the opposite of) — `references/gcp.md` (this file *provisions* what that file *specifies*; it does not restate the settings).
- How `plan`/`apply` run as least-privilege CI jobs, OIDC→WIF auth, the deploy stage that consumes the image and resources defined here — `references/github-actions.md`.
- Containers/images the Cloud Run resources run (digest pinning, multi-stage, non-root, scanning) — `references/containers-and-orchestration.md`.
- Cloud SQL Postgres + RLS tenant-isolation, `dbmate` migrations (migrations are *not* Terraform — schema is its own gate), KMS-encrypted `tenant_api_keys`, append-only evidence — `references/databases.md` and `references/secure-data-processing.md`.
- Monitoring alert policies and the incident path the `monitoring` module feeds — `references/observability-and-incident-response.md`.
- Branch protection / CODEOWNERS / human-reviews-every-agent-PR (the team model the plan-review gate inherits) — `references/github-teams.md` and SKILL.md Source Code Management.
- Never-commit-secrets, least privilege, input validation, structured logging — `SKILL.md` (this file applies them to Terraform; it does not restate them).
