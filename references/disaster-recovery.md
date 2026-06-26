# Disaster Recovery, Backups & Restore Drills

Companion reference for the senior-engineering-partner skill.

> **Rigor tier:** full RTO/RPO targets and scheduled restore drills are **Tier-2 (production/commercial) posture** from SKILL.md's *Project Phase & Rigor Ladder*. But the **backup floor is universal** — *every* tier states a backup story and treats "a backup is not a backup until a restore is verified" as non-negotiable (SKILL.md *Backup & Continuity Floor*). What scales with tier is the measured restore-drill cadence, immutability/air-gap, and multi-region — defer those at Tier 0/1 with an explicit `TODO`, but anything holding real customer/tenant or legal data is Tier 2 on sight. Business-*continuity* breadth (BIA, provider-outage, comms, the solo-operator path) lives in `business-continuity.md`; this file is the data-restore layer.

`compliance.md` requires a "backup story" and SKILL.md requires every repo and every data-holding system have one; `observability-and-incident-response.md` runs the incident; `business-continuity.md` is the wider plan. This file is the **disaster-recovery** layer between them: **a backup you have never restored is a hope, not a backup.** Worked example: the example multi-tenant SaaS spans Cloud SQL Postgres (tenant + evidence *metadata*), GCS (the evidence *objects*), Cloud KMS (the keys that decrypt tenant secrets), Secret Manager (platform secrets), and Terraform-defined infra. For a product holding regulated records, **restore-tested, immutable, and tamper-evidence-preserved** is the standard, not "backups are enabled." Cross-ref `gcp.md` (the resources), `databases.md` (Postgres backup/PITR), `secrets-and-key-rotation.md` (key-material recovery — the unrecoverable case), `iac-terraform.md` (infra is re-creatable from code), `data-protection.md` (retention vs DR tension), `observability-and-incident-response.md` (DR is executed *during* a SEV1).

The governing rule: **define RTO/RPO per data class, make backups that are independently restorable AND tamper-proof, and prove it with a scheduled drill — an untested or mutable backup is the silent failure DR exists to prevent.** *Verify exact `gcloud`/Cloud SQL/GCS backup-and-restore commands against current docs before relying on them; the strategy is durable, the CLI is version-specific.*

---

## 1. RTO/RPO — name the targets first
- **RPO** (how much data you can lose) and **RTO** (how long restore may take) are *decisions*, set per data class, not afterthoughts. Evidence objects and the tenant/matter database warrant a tight RPO (minutes, via PITR) and a documented RTO; an analytics rebuild can tolerate more.
- **Derive them from a Business Impact Analysis, don't pick them by feel** — which processes are mission-critical, what an hour of downtime or a day of lost data actually costs, drives the number (`business-continuity.md` §1). A defensible RTO/RPO is one you can trace to an impact, not a round number.
- Write them down — they drive backup frequency, retention, and what "DR succeeded" means in the drill (§5). A DR plan with no RTO/RPO has no pass/fail criterion.

---

## 2. The backup rule: 3-2-1-1-0 (the modern floor)
The classic 3-2-1 is necessary but no longer sufficient — ransomware now targets the *backups* in the great majority of attacks, so a backup an attacker (or a fat-fingered `terraform destroy`, or a compromised service account) can delete is half a backup. The current standard adds an immutable copy and verified-zero-error restore:

- **3** copies of the data (production + two backups),
- **2** different media / storage classes or providers (not two buckets in the same project),
- **1** copy **offsite** — a different failure domain from production (separate cloud project *and* separate IAM/credentials, ideally a separate account or provider),
- **1** copy **immutable or air-gapped** — WORM / object-lock / retention-lock so that *no one*, including a privileged admin or a stolen credential, can alter or delete it inside its retention window,
- **0** errors — every backup is **restore-tested** and integrity-verified; an untested backup counts as zero backups.

**Immutability is the part teams skip and the part that defeats ransomware.** Map it onto the stack concretely:
- **GCS objects:** plain **object versioning is NOT immutability** — a noncurrent version is still deletable by anyone with `storage.objects.delete`, a lifecycle rule, or a compromised SA. For a real immutable copy use a **bucket retention policy + Bucket Lock** (locks the policy itself so it can't be shortened) and/or **object holds**; keep versioning on *as well* (it protects against overwrite, lock protects against deletion). State which control you actually applied.
- **Cloud SQL:** automated backups + PITR live **in the same project as prod** — a project-scoped compromise or `terraform destroy` takes prod *and* its backups together. Add an out-of-domain copy: scheduled **exports to a retention-locked bucket in a separate project/account** (or cross-project backup), so the restore path survives the loss of the prod project.
- **Don't let the immutable copy expire silently** — retention windows are a setting; a too-short window is a backup that quietly stops existing.

---

## 3. What must be recoverable — and the order to restore it
List every stateful dependency; a restore is only complete when **all** are back **and** they reconcile (the DB row pointing at a `gs://` object is useless if the object is gone, and vice-versa).

| Asset | Backup mechanism | Recovery note |
|---|---|---|
| **Cloud SQL Postgres** | automated backups + **PITR** (WAL) + out-of-project export to a locked bucket | restore to a timestamp; the schema re-applies via `dbmate` if rebuilding (`databases.md`) |
| **GCS evidence objects** | **versioning** (overwrite) **+ retention policy/Bucket Lock** (deletion/immutability) + optional dual-region | a deleted/overwritten object is recoverable only if the protection was on *before* the loss; versioning alone does not stop a malicious purge |
| **Cloud KMS keys** | **the key cannot be "backed up"** — guard against destruction | if the key version that wrapped `tenant_api_keys.key_ciphertext` is destroyed, the ciphertext is **permanently unrecoverable** (`secrets-and-key-rotation.md`) |
| **Secret Manager** | versions retained until destroyed | re-create from 1Password source of truth if lost |
| **Infrastructure** | **Terraform** (`iac-terraform.md`) | re-create the whole environment from code into a fresh project — the IaC *is* the infra backup |

- **Restore dependency order:** infra (Terraform) → KMS keys (must exist) → Cloud SQL → GCS reconcile → secrets → app deploy. Document it; a restore done out of order stalls.
- **The reconcile step is the one people forget:** after DB + GCS are both back, verify referential integrity — every evidence row resolves to an object and orphans are flagged.

---

## 4. Backups that exist vs. backups that are *verified*
- **Turn the mechanisms on and prove their settings** (`gcp.md` audit style): Cloud SQL automated backups + PITR enabled and retained to your RPO; GCS **versioning on AND a retention policy/Bucket Lock** for evidence/state buckets; the state bucket itself versioned + locked (`iac-terraform.md`).
- **A backup you can't read is not a backup.** Periodically confirm backups are *non-empty, recent, and restorable* — the existence of a backup job is not evidence it produced a usable artifact (the dead-man's-switch logic from SKILL.md monitoring, applied to backups). This is the **0** of 3-2-1-1-0.
- **3-2-1-1-0 spirit, restated:** the restore path must not share a single failure domain with production, and at least one copy must be tamper-proof for its retention window (a backup only inside the same project/credentials that a compromise or `terraform destroy` could take out with prod is half a backup; a *mutable* one a ransomware actor can encrypt or delete is no backup at all).

---

## 5. The restore DRILL (the heart of DR)
- **Schedule a real restore into a scratch environment** — restore Cloud SQL to a timestamp + a sample of GCS objects into an isolated project, bring the app up against them, and **measure against RTO/RPO.** This is the dead-man's-switch of DR: the worst DR failure is discovering at the incident that the backup never worked.
- **Game-day the runbook** (cross-ref `observability-and-incident-response.md` §5 and `business-continuity.md` §4) — walk the §3 order end-to-end; the drill finds the stale flag, the missing permission, the step that assumed a tool you removed, *before* the real outage. Start with a **tabletop** (talk through the steps) before a live restore; keep a kill switch.
- **Record the measured RTO/RPO** each drill; a regression (restore got slower, or the PITR/immutability window shrank) is an alert, not a shrug.
- Treat dashboards/alerts/runbooks as code (`iac-terraform.md`) so the DR procedure is versioned and reproducible, not tribal knowledge.

---

## 6. Key-material recovery (the unrecoverable case — design around it)
- **KMS key destruction is the one disaster a restore can't fix.** Restore the DB and the buckets all you like — if the KMS key version that wrapped a tenant's `key_ciphertext` is gone, that ciphertext is dead. So the control is **prevention**: never destroy a key version while `active` ciphertext references it (`secrets-and-key-rotation.md` §3), use KMS's destroy-scheduling/delay so a destroy is reversible within a window, and lock destroy permission to a tiny set of identities.
- Re-deriving secrets from the **1Password source of truth** is the recovery path for Secret-Manager-held secrets; tenant BYO keys, by contrast, you cannot re-derive — the tenant must re-enter them (which is acceptable and fail-clear, but must be a documented post-DR step).

---

## 7. Data integrity across a restore
- **Re-verify `content_sha256` on restored evidence** — a restore must reproduce the exact bytes; the integrity hash (`databases.md`, `secure-data-processing.md` §3) is how you prove the restored evidence is unaltered. A restore that silently corrupts evidence is worse than no restore for a legal-admissibility product.
- **Preserve tamper-evidence:** the append-only audit trail (`databases.md`) is part of what must be restored and reconciled; the restore itself is an auditable event.

---

## 8. Local & single-machine backups (the non-cloud half)
The cloud SaaS is not the only thing that can be lost. A laptop, a local-only sensitive-data repo, or a script's output directory needs the same discipline — and the common trap is **mistaking sync for backup**.
- **Sync is not backup.** A dotfile-sync tool, Dropbox/iCloud, and a Git remote all *propagate* a bad change (a deletion, a corruption, a malicious commit) to every copy. Backup means a *separate, point-in-time, restorable* copy — Time Machine, a versioned/locked bucket, or a snapshot — that a bad commit can't reach.
- **Local-only data repos** (the no-remote, `pre-push`-guarded case from SKILL.md) must state their *actual* backup mechanism in the README, not just the no-remote policy — e.g. Time Machine **plus** a periodic encrypted copy to an offsite/immutable target, so the 3-2-1 minimum holds even with no Git remote.
- **The data your scripts produce** (reports, extracted artifacts, databases) is data too — give it a backup story or document that it's reproducible-from-source and therefore deliberately not backed up. Silence is an unflagged data-loss risk.
- **Secrets recovery:** 1Password is the source of truth; confirm its own recovery path (Emergency Kit / account recovery) exists, since losing it loses every downstream secret. Per-repo deploy keys and signing keys are machine-local — document how each machine re-establishes them after a wipe.

---

## Runbook & checklist
A DR runbook is a flat, tested checklist (symptom → restore order → verify → measure). Pre-write it; you cannot author DR during the outage.
- [ ] RTO/RPO defined per data class, traced to a BIA, and recorded.
- [ ] 3-2-1-1-0 satisfied: ≥3 copies, ≥2 media/domains, ≥1 offsite (separate project+IAM), ≥1 immutable/air-gapped (retention-lock/Bucket Lock), 0 untested.
- [ ] Cloud SQL PITR + out-of-project locked export; GCS versioning **and** retention policy/Bucket Lock on; verified recent/non-empty.
- [ ] A scheduled restore **drill** runs into a scratch env and meets RTO/RPO; results recorded; a tabletop precedes the live run.
- [ ] KMS-key-destruction guarded (delay window + tight IAM + the §3 re-wrap precondition).
- [ ] Restore order documented (infra→KMS→DB→GCS reconcile→secrets→deploy); reconcile step verifies DB↔object integrity.
- [ ] Restored evidence re-verified against `content_sha256`; audit trail intact.
- [ ] Local/single-machine data has a real backup (not just sync); local-only repos name their backup mechanism; 1Password recovery path confirmed.

### Cross-references
- The wider plan (BIA, provider-outage, comms, solo-operator continuity) — `references/business-continuity.md`; the in-code resilience that prevents the outage — `references/resilience-engineering.md`.
- The cloud resources + their backup/versioning/lock settings — `references/gcp.md`; Postgres backup/PITR + migrations re-apply — `references/databases.md`.
- Key-material loss is the unrecoverable case; rotation re-wrap precondition — `references/secrets-and-key-rotation.md`.
- Infra re-creatable from code (the infra "backup") + dashboards/alerts as code — `references/iac-terraform.md`.
- DR is executed during an incident; game-day rehearsal — `references/observability-and-incident-response.md`.
- Evidence integrity (`content_sha256`) + append-only audit — `references/secure-data-processing.md` §3. Retention-vs-DR tension — `references/data-protection.md`. The repo-level backup-story rule — `SKILL.md`.
