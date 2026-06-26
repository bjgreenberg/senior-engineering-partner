# Secrets & Key Rotation Lifecycle

Companion reference for the senior-engineering-partner skill.


SKILL.md says never hardcode secrets and 1Password-first; `gcp.md` says secrets live in Secret Manager and automation uses OIDC→WIF, never a downloaded SA key. This file is the **lifecycle** layer neither covers: secrets and keys are not set-and-forget — they expire, leak, and must rotate, and **rotation is a procedure that must not lose data or cause an outage.** The example multi-tenant SaaS is the worked example: per-tenant BYO keys are **KMS-envelope-encrypted** — `tenant_api_keys.key_ciphertext` (a KMS-wrapped blob) + `kms_key_version` + `status`/`last_verified_at` (`databases.md`, `secure-data-processing.md` §3). A KMS key rotation that doesn't re-wrap every tenant's ciphertext silently strands them; a leaked secret with no rotation runbook is an open door. Cross-ref `gcp.md` (Secret Manager/IAM), `observability-and-incident-response.md` (compromise = incident), `compliance.md` (rotation is SOC 2 CC6 evidence), `disaster-recovery.md` (key-material loss is the unrecoverable DR case).

The governing rule: **every long-lived credential has a named owner, a rotation trigger, and a tested rotation procedure — or it is a latent incident.** *Verify every exact `gcloud`/KMS/Secret Manager command and field against current docs before running it; the principles below are durable, the CLI surface is version-specific.*

---

## 1. The rotatable inventory (know what rotates, and on what trigger)

Enumerate every credential and, for each, its **owner**, **storage**, **rotation cadence**, and **compromise action**. For this stack:

| Credential | Stored | Scheduled rotation | On compromise |
|---|---|---|---|
| Per-tenant BYO provider key | KMS-wrapped in `tenant_api_keys.key_ciphertext` | tenant-driven (they rotate at the provider) | revoke at provider, mark `status='revoked'`, force re-entry |
| Platform Anthropic key | Secret Manager | periodic | new version, disable old, redeploy |
| Cloud SQL DB password (`app_api`/`app_worker`) | Secret Manager (prefer **IAM DB auth** to avoid a password entirely) | periodic | rotate immediately, restart connections |
| KMS key (wraps the BYO ciphertext) | Cloud KMS | scheduled key-version rotation | new version + **re-wrap all ciphertext** (§3) |
| Firebase / service-account identities | Workload Identity (no key file) | n/a — short-lived tokens | revoke the WIF binding |
| Dev/test secrets (`DEV_AUTH_SECRET`) | local `.op-env` only, never prod | per project | regenerate; prod must `FAIL CLOSED` on dev mode (`python-web-apis.md`) |

- **Two triggers, two postures.** *Scheduled* rotation is routine and zero-downtime (§2). *Compromise-driven* rotation is an incident — speed over grace (§5). Design the procedure to serve both.
- **Prefer credentials that can't leak.** IAM database auth (short-lived tokens) and Workload Identity remove a standing password/key from the inventory entirely — the cheapest secret to rotate is the one that doesn't exist. Reach for these before managing yet another rotating password.

---

## 2. Zero-downtime rotation = an overlap window (never a hard swap)

A rotation that invalidates the old credential before every consumer holds the new one is an outage. The universal pattern is **two valid credentials during an overlap window**:

1. **Create** the new version (old still active).
2. **Distribute** — every consumer can now read the new version (redeploy / refresh).
3. **Cut over** — consumers use the new version.
4. **Verify** nothing still authenticates with the old one (watch logs/metrics for old-version use).
5. **Retire** — disable, then after a safety window destroy, the old version.

- **Secret Manager** supports multiple enabled versions; add the new version, move traffic, then **disable** (reversible) before **destroy** (irreversible). Cloud Run picks up a new version on redeploy — confirm your `--set-secrets` reference resolves to the intended version (pinned vs `latest`) *against current docs*.
- **Never destroy old key material until you've proven nothing depends on it.** Disable first (a disabled key fails loudly and is instantly re-enableable); destroy only after the overlap window passes clean. A destroyed KMS key version is **unrecoverable** — and so is everything it encrypted (`disaster-recovery.md`).

---

## 3. KMS key-version rotation + re-wrapping `tenant_api_keys` (the specific gap)

The envelope pattern (`secure-data-processing.md` §3) means each BYO key is encrypted under a specific KMS key *version*, recorded in `kms_key_version`. Rotating the KMS key creates a new version for **new** encryptions but does **not** touch existing ciphertext — old ciphertext stays decryptable only while its version exists. So a naive "rotate the KMS key" leaves every existing tenant pinned to the old version, and destroying that version later destroys their keys.

**The re-wrap procedure (idempotent, audited, worker-only):**
1. Rotate the KMS key (new primary version). New writes use it automatically.
2. A re-wrap job (a Cloud Run Job, runs as the worker SA — the only identity allowed to KMS-decrypt) iterates every `active` `tenant_api_keys` row: **decrypt** `key_ciphertext` under its recorded `kms_key_version`, **re-encrypt** under the new version, **update** `key_ciphertext` + `kms_key_version` in one transaction.
3. **Verify**: no `active` row still references the old `kms_key_version`; spot-decrypt a sample.
4. Only **after** zero rows reference the old version, schedule its destruction (with the disable-first safety window of §2).

- **Idempotent + resumable** — a re-wrap that dies halfway must re-run safely (skip rows already on the new version). Partial re-wrap that then destroys the old version = data loss.
- **The plaintext key never leaves the worker** and never lands in a log, a column, or the API role's reach (`databases.md`: `app_api` can't even read `key_ciphertext`). Re-wrapping is decrypt→encrypt in memory in the worker, nothing persisted in between.
- This is a **required test target** — extend the deletion/secrecy tests (`testing.md`, `secure-data-processing.md` §3) with "after a simulated key rotation, every ciphertext decrypts under the new version and none under the old."

---

## 4. Detecting staleness & compromise (rotation you can't see is rotation you won't do)

- **Track age and last-verified.** `last_verified_at` exists on `tenant_api_keys` for a reason — a periodic verifier (a 1-token provider ping) flips `status` to `invalid` on failure and surfaces it; a key unverified past a threshold is an alert (`observability-and-incident-response.md`, dead-man's-switch). The same age-tracking applies to platform secrets.
- **Alert on use of a credential you're retiring** (the overlap-window signal from §2) and on **anomalous use** — a BYO key spending far above its tenant's baseline can mean a leak (cross-ref the per-tenant cost alert in observability + `secure-data-processing.md` §2).
- **A leaked secret in git history is still leaked after you delete the commit.** `git-secrets`/scanning is the prevention (SKILL.md); if one lands, rotation — not history surgery alone — is the remediation, because it's already been cloned/cached.

---

## 5. Compromise response (forced re-issue, fast)

Treat a suspected secret/key compromise as a **SEV1** (`observability-and-incident-response.md` §3): **contain before tidy.**
1. **Revoke at the source** — disable the Secret Manager version / revoke the provider key / mark `tenant_api_keys.status='revoked'`; for a tenant key, also revoke it at the provider.
2. **Rotate** in the new credential (§2/§3) — no grace window; brief downtime beats continued exposure.
3. **Assess blast radius** from audit/usage tables (`databases.md` append-only): what did the leaked credential touch, for how long.
4. **If personal data was reachable, the privacy clock may have started** — hand off to the breach path (`data-protection.md` §7, `observability` §4).
- Pre-write this as a runbook **before** you need it; you cannot improvise a key-compromise response at 3am.

---

## 6. What must never happen
- A KMS key version destroyed while `active` ciphertext still references it (irreversible tenant-key loss).
- A secret rotated by hard-swap with no overlap window (outage).
- The plaintext of a tenant key written to a log, an `output`, state, or a non-worker role.
- A "rotation" that updates the secret store but never redeploys/refreshes consumers (they keep using the old one).
- Long-lived SA key files or DB passwords where Workload Identity / IAM DB auth would remove the credential entirely.

---

## QA, testing & checklist
- A **rotation drill**: in staging, rotate the KMS key and run the re-wrap job end-to-end; assert all ciphertext moves versions and decrypts. A rotation procedure never executed is a hypothesis (mirrors the DR drill — `disaster-recovery.md`).
- Test the **prod-fail-closed** dev-secret guard (`python-web-apis.md`): dev mode + a prod signal must refuse to boot.
- Pre-merge checklist for any secret/key change:
  - [ ] New credential has an owner, a rotation cadence, and a compromise action recorded.
  - [ ] Rotation uses an overlap window (create→distribute→cutover→verify→retire); destroy only after old-version use is provably zero.
  - [ ] KMS rotation includes the idempotent re-wrap of `tenant_api_keys` + a verify step before any version destroy.
  - [ ] No plaintext key reachable outside the worker; none logged.
  - [ ] Prefer IAM DB auth / Workload Identity over a new standing password/key.

### Cross-references
- Secret Manager, KMS, IAM, OIDC→WIF resource settings — `references/gcp.md` (this file is the *lifecycle*; that file is the *resource standard*).
- Where the ciphertext lives + the column-grant secrecy boundary — `references/databases.md`; the envelope-encryption pattern + deletion-completeness tests — `references/secure-data-processing.md` §3.
- Compromise = incident; the SEV1 path and the breach clock — `references/observability-and-incident-response.md`, `references/data-protection.md`.
- Key-material loss is the unrecoverable disaster case — `references/disaster-recovery.md`.
- Rotation as SOC 2 CC6 evidence — `references/compliance.md`. Never-hardcode-secrets + 1Password-first — `SKILL.md`.
