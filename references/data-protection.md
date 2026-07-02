# Data Protection & Privacy (GDPR / UK-GDPR / CCPA)

Companion reference for the senior-engineering-partner skill.


Engineering controls for privacy, mapped to the stack — not legal theory. Scope: **GDPR + UK-GDPR + CCPA/CPRA**. HIPAA is **out of scope**. Data residency is best-practice guidance here, not a hard mandate. The example multi-tenant SaaS processes dense PII (names, emails, IPs, message bodies, and an append-only audit trail), so privacy is load-bearing, not paperwork. Privacy obligations become *code*: data-subject rights are endpoints, retention is a cron job, erasure is a cascade. This file is the "make it a feature" layer; cross-ref `secure-data-processing.md` (the tenant/parser/model surfaces), `databases.md` (RLS + KMS), `compliance.md` (SOC 2 evidence), and `observability-and-incident-response.md` (breach response).

A privacy review surfaced three canonical gaps — flagged inline below as **GAP** — that this reference exists to close: no DB-level guarantee that `gs://` objects purge on tenant deletion; no documented no-train/retention posture on the PII path to the model provider; and content/PII at risk of landing in logs. Treat closing them as required controls.

---

## 1. Privacy-by-design & by-default (the governing principle)

- **Collect, store, and send only what the analysis needs (data minimization).** This is the single highest-leverage privacy control because the cheapest PII to protect is the PII you never held. Do not persist a whole uploaded document if extracted text + a content hash is what the pipeline needs downstream. Do not send more of a document to the model than the task requires — redact or scope before the API call (cross-ref `secure-data-processing.md` §2: "Don't send more of the document than the analysis needs").
- **By-default means the privacy-protective setting is the one you ship.** Retention timers on, evidence buckets private with public-access-prevention, logs scrubbed, no-train posture requested from every subprocessor. A feature that leaks PII unless a flag is flipped is a defect.
- **Every new column that holds personal data is a decision, not an accident.** Before adding one, answer: what lawful basis, what retention class, does it appear in the DSAR export, does the erasure cascade reach it? If you cannot answer all four, do not add the column.
- **Pseudonymize/redact at the boundary where you can.** A pseudonymized record (PII swapped for a per-tenant token) is still useful for analysis and far cheaper to breach. Redaction is not anonymization — re-identifiable data is still personal data under GDPR.

---

## 2. Data-subject rights as engineering features

GDPR Arts. 15–22 (and CCPA/CPRA equivalents) are not a legal mailbox — build each as a **tenant-scoped operation that runs through RLS**, so a request for tenant A can never touch tenant B's data. Resolve the requesting identity, open the RLS-scoped transaction (the token→session-GUC→RLS pipeline in `python-web-apis.md`), then act.

| Right (GDPR art.) | CCPA/CPRA analog | Engineering feature |
|---|---|---|
| Access / Portability (15, 20) | Right to Know / Access | A **DSAR export**: a tenant-scoped dump of *all* their data — DB rows + `gs://` evidence manifest — in a machine-readable format (JSON/CSV). One job, RLS-scoped, no cross-tenant bleed. |
| Rectification (16) | Right to Correct (CPRA) | An authenticated update path for tenant-supplied fields, written through RLS and the audit trail. |
| Erasure / "right to be forgotten" (17) | Right to Delete | The hard one — see §3. Soft-delete → hard-purge cascade reaching Postgres, object storage, *and* provider retention. |
| Restriction / Objection (18, 21) | Opt-out of sale/share | A status flag that suppresses processing without deleting (legal-hold tension — §4). |

- **Access/portability is the easy one done wrong.** The trap is an export that joins across tenants because it ran as a privileged role bypassing RLS. Run the export through the *same* RLS-scoped session as a normal request; assert in a test that tenant A's export contains zero tenant B rows.
- **Authenticate the data subject / the requesting tenant before acting.** A DSAR is a perfect pretext for a data-exfiltration social-engineering attack. Verify identity to the same bar as any privileged action.
- **Log every rights request as an audited event** (who, what, when, outcome) — this is both an accountability obligation (§9) and your evidence that you honored the clock (GDPR generally 1 month to respond).

---

## 3. Erasure / right-to-be-forgotten — the cascade (canonical GAP)

A delete is a lie unless it reaches **every place the data went**. A privacy review found the canonical gap: **no DB-level guarantee that `gs://` objects purge when a tenant is deleted** — the Postgres row vanishes and the stored object orphans in the bucket forever. A delete that leaves data in object storage or in the provider's retention is a *reportable failure to erase*, not a tidy-up TODO.

**Encode this two-phase pattern:**

1. **Soft-delete first** (set `deleted_at`, flip status) — reversible, immediate from the user's view, and it lets you honor legal-hold/short grace windows before destruction.
2. **A hard-purge job** (a Cloud Run Job, idempotent, audited) that cascades the destruction:
   - Postgres rows — rely on `ON DELETE CASCADE` foreign keys *and verify the FK graph actually covers every PII table*; an un-cascaded table is silent retention.
   - **`gs://` objects — the gap.** The database cannot delete a bucket object. The purge job must enumerate the tenant's object paths and delete them explicitly; verify the bucket is empty of that tenant's prefix afterward. Do not rely on a DB trigger for this — it cannot reach GCS.
   - **Model-provider retention — revoke it.** Whatever the provider retains (see §5) must be deleted or its retention revoked per the provider's documented mechanism. If you sent PII to the API, deletion is not complete until the provider's copy is addressed. **Verify the current provider deletion mechanism against live docs before relying on a specific endpoint or window — do not hardcode a retention figure you cannot confirm.**

- **The purge job is a required test target.** "Deletion completeness" is already a named test case in `secure-data-processing.md` §3 — a tenant-delete must remove DB rows *and* the `gs://` objects, asserted, in CI. Extend it to assert the provider-retention step ran.
- **Idempotent + resumable.** A purge that dies halfway must be safely re-runnable to completion — partial erasure is worse than none because it looks done.
- **Erasure ≠ truncate the audit log.** You delete the *personal data*; you keep a tamper-evident record *that* an erasure happened (a hash/anonymized event), to prove compliance. Append-only audit tables (`secure-data-processing.md` §3) survive the purge by design.

---

## 4. Retention — explicit, per-class, automated

**Never keep-forever.** "We'll delete it eventually" is unbounded retention, which is a GDPR storage-limitation (Art. 5(1)(e)) violation and an ever-growing breach blast-radius. Every data class gets a **named retention period and an automated deletion job** — the same discipline as log rotation in SKILL.md, applied to PII.

- **Define a retention schedule per data class** (raw upload, extracted text, evidence object, analysis result, audit event, usage_event). Document it; make the timer real (a scheduled Cloud Run Job that deletes past-retention records via the same cascade as §3).
- **Name the tension and resolve it deliberately: regulated-data retention / legal hold vs. erasure.** Some records may need to be retained for legal admissibility or under a litigation hold *at the same time* a data subject demands erasure. These conflict. Encode a **legal-hold flag** that suppresses the purge for held records, with the basis recorded — and surface, don't silently swallow, an erasure request that hits held data. The lawful-basis-to-retain (legal claim) is a recognized GDPR exception to erasure; it must be an explicit, auditable decision, not a default that quietly ignores deletion requests.
- **Retention deletion uses the §3 cascade**, not a bare `DELETE` — same gap, same fix (DB + `gs://` + provider).
- **Long retention inherits harvest-now-decrypt-later (HNDL) risk.** A confidential data class retained for years (evidence, exports, archives) must keep its secrets *through* the classical→post-quantum transition: transport traffic or ciphertext recorded today becomes decryptable when a cryptanalytically-relevant quantum computer arrives. For any long-retention confidential class, **name the post-quantum consideration in the retention/DPIA decision** (the same explicit-decision discipline as the legal-hold tension above), and prefer **platform-managed TLS/KMS** so hybrid post-quantum key exchange arrives transparently — the triage-by-surface detail (what is and isn't HNDL-exposed) lives in `compliance.md` A04.

---

## 5. Subprocessors, DPAs & the no-train posture (canonical GAP)

**Every third party that touches personal data is a subprocessor and needs a DPA** (Data Processing Agreement) plus a documented data-handling posture. On this stack the PII-touching subprocessors are:

| Subprocessor | What it touches | Required posture |
|---|---|---|
| Anthropic (Claude API) | Extracted document text / PII on the inference path | DPA in place; **no-training-on-API-data + zero-or-minimal retention** posture, verified against current API data-handling terms. |
| Google Cloud (Cloud SQL, GCS, Firebase Auth) | Evidence at rest, identities | DPA / DPA-equivalent terms; region + encryption configured (§6). |

- **GAP — no documented no-train/retention posture on the PII path.** A privacy review flagged that the path sending PII to the model had no recorded no-train/retention posture. Make it a **required control**: confirm and document that API data is not used for training and the retention is zero-or-minimal, *per the provider's current terms* — and re-confirm on provider terms changes. Note that consumer-tier and API-tier data-handling terms differ; the commercial API path is what matters here. **Verify the exact current posture against Anthropic's live data-handling documentation — state the principle, don't assert a specific retention window from memory.**
- **Maintain a subprocessor list** as a real artifact (a doc in the repo). GDPR/CPRA require you to know and disclose your subprocessors; CPRA requires the subprocessor contract to bind them to equivalent obligations. A new vendor on the PII path = a new DPA + a list update, not a silent integration.
- **Minimize before you send** (§1): the less of the document that crosses to a subprocessor, the smaller the DPA's surface and the breach exposure.

---

## 6. Cross-border / residency (best-practice, NOT mandated)

Residency is **guidance** here, not a hard constraint — but do it where feasible, because it shrinks transfer-mechanism complexity (SCCs, UK IDTA, adequacy) for EU/UK personal data.

- **Pin location at every layer for EU/UK data where feasible:** the GCP region, the Cloud SQL instance location, the GCS bucket location, and — where the provider supports regional routing — model-inference routing. Co-locate so EU/UK data doesn't transit a US region incidentally.
- **Document a data-flow map.** For each data class: where it's collected, stored (region), processed, and which subprocessors (and their regions) see it. This map is what makes a transfer-mechanism assessment possible at all and is core DPIA input (§8). **Verify the current set of GCP region names and any provider regional-inference options against live docs — don't invent region identifiers or routing flags.**
- Treat residency as a *design preference with a documented rationale when you can't meet it*, not a promise you silently break.

---

## 7. Breach notification — the 72-hour clock

GDPR Art. 33 starts a **72-hour clock** to notify the supervisory authority once you become *aware* of a personal-data breach. This is an engineering trigger, not just a legal one — your detection plumbing starts the clock. Ties directly to `observability-and-incident-response.md` (this is the privacy-specific overlay on the IR runbook).

**The path:**
1. **Detect** — alerting on the access/audit logs and anomalous cross-tenant or bulk-read patterns surfaces the event (cross-ref observability). The dead-man's-switch and access-log review are your awareness mechanism.
2. **Assess — is *personal data* involved?** Not every incident is a *personal-data* breach. A leaked build artifact may not be; cross-tenant evidence exposure absolutely is. This assessment scopes everything downstream.
3. **Contain** — revoke the path, rotate the implicated KMS key/credentials, stop the bleed.
4. **Notify** — supervisory authority/DPA within 72h of awareness (unless unlikely to risk individuals' rights); notify affected data subjects without undue delay where the risk is high. CCPA/CPRA has its own breach-notification regime (state AG / consumers) — different triggers, run both assessments.

- **Keep the audit trail intact** — append-only evidence/audit tables (`secure-data-processing.md` §3) are what let you scope a breach (whose data, how much). A mutable log is useless here.
- **The clock is short — pre-write the runbook.** You cannot improvise breach assessment in 72 hours. The runbook (who decides "personal data: yes/no", who notifies, the contact for the DPA) lives in `observability-and-incident-response.md`.

---

## 8. DPIA for high-risk processing

**Large-scale PII analysis is high-risk processing** (special-category-adjacent data, automated analysis, potentially vulnerable data subjects) — it qualifies for a **Data Protection Impact Assessment** under GDPR Art. 35. Do it before the processing goes live, not after a regulator asks.

- The DPIA documents: the processing, its necessity/proportionality, the risks to data subjects, and the mitigations (everything in this file — minimization, RLS isolation, encryption, retention, erasure, subprocessor posture). It is the artifact that *ties all the controls together* into a defensible record.
- The **data-flow map** (§6) and **subprocessor list** (§5) are direct DPIA inputs — build them once, reuse them here.
- Re-run the DPIA when the processing materially changes (new data class, new subprocessor on the PII path, new region).

---

## 9. PII in logs, prompts & at rest — the technical controls

These are where privacy meets the code you write every day. Most overlap `secure-data-processing.md` and `observability-and-incident-response.md` — restated here as the privacy mandate.

- **Never log document content or PII at INFO (or any level) in production.** This is the third canonical gap. Log token counts, `error_code`, job IDs, tenant IDs (pseudonymous), content hashes — **never** the prompt, the model response, or extracted text (cross-ref `secure-data-processing.md` §2: "log token counts and `error_code`, not content"; observability for the log-scrubbing discipline). A logged prompt is PII at rest in `~/Library/Logs/` or Cloud Logging with none of the access controls the database has. SKILL.md's "never log secrets at any level" extends verbatim to PII.
- **Pseudonymization / redaction** reduces what's exposed if a log or export leaks — apply it at the boundary (§1).
- **Encryption in transit and at rest is table stakes.** TLS everywhere; Cloud SQL + GCS encrypted at rest. On top of that, the **KMS per-tenant key envelope-encryption pattern** for tenant secrets (`tenant_api_keys.key_ciphertext` + `kms_key_version`, decrypt only in the worker) — cross-ref `databases.md` and `secure-data-processing.md` §3. The raw key never lands in a column, a log, or the model client's environment.
- **Accountability = the audit/access logs.** GDPR Art. 5(2) requires you to *demonstrate* compliance; append-only audit tables + access logs are that demonstration, and they double as SOC 2 evidence (cross-ref `compliance.md`). "We log who accessed what evidence, immutably" is the answer to both a regulator and an auditor.

---

## 10. CCPA / CPRA specifics (mostly light for B2B)

Map the California regime, but note its B2B footprint is small here — the example SaaS's data subjects are largely the *content* of evidence, and B2B contact data has had carve-outs that have shifted under CPRA. Confirm current applicability rather than assuming.

- **Right to opt out of "sale" or "sharing."** You almost certainly don't *sell* personal data — but "sharing" has a broad cross-context-behavioral-advertising meaning under CPRA. As long as you don't share PII for advertising, this is light; document that you don't, rather than building an opt-out you don't need.
- **"Do Not Sell or Share My Personal Information"** is a consumer-facing control on consumer sites; for a B2B SaaS it's typically a policy statement, not a UI toggle — **but verify current CPRA B2B applicability against live guidance; the carve-outs have moved.**
- **The substantive CCPA rights — Know/Access, Delete, Correct — are already covered** by the DSAR export (§2) and erasure cascade (§3). Build those once and they satisfy both regimes. Don't build a parallel CCPA pipeline; build the rights as features and map both regimes onto them.
- **Service-provider contract terms (CPRA):** your subprocessors (§5) must be bound as "service providers"/"contractors" with the CPRA-required terms — the same DPA artifact, with the CPRA clauses present.

---

## Quick gate checklist (what must be true before shipping a PII-touching change)

- [ ] New PII column → has a retention class, appears in the DSAR export, and the erasure cascade reaches it.
- [ ] DSAR export runs RLS-scoped; a test asserts zero cross-tenant rows.
- [ ] Tenant-delete cascade reaches **DB rows + `gs://` objects + provider retention**, asserted in CI.
- [ ] No document content / PII / prompt / response logged at any level.
- [ ] Any new subprocessor on the PII path → DPA + subprocessor-list update + no-train/retention posture confirmed against live docs.
- [ ] Data-flow map and DPIA updated if the data classes, regions, or subprocessors changed.
