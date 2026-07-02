# Security & Compliance Frameworks (NIST CSF 2.0 + SSDF, OWASP, SOC 2, Well-Architected)

Companion reference for the senior-engineering-partner skill.


These are **enforceable review checklists, not academic summaries.** In `REVIEW:` mode, walk the relevant list and name the concrete control that is present, missing, or wrong — mapped to *your* stack (e.g. Supabase RLS, GCP IAM, your SSO/IdP, your secret manager, GitHub PR-flow). A finding is "injection" only when you can point at the unparameterized query. Frameworks overlap heavily: one control (SSO + MFA) satisfies an OWASP auth item, NIST CSF Protect, *and* SOC 2 CC6 simultaneously — wire the evidence once, claim it three times. The standing rules in SKILL.md (1Password secrets, least-privilege FDA, parameterized queries, Bash command-injection, structured logging + dead-man's-switch, SSH-signed PR-flow) already implement most of these; this file is the map from "what the skill enforces" to "what an auditor asks for."

> **Version note (check before citing a number).** OWASP, NIST, and the SOC 2 TSC all revise periodically. The numbering and category names below are correct as of the **OWASP Top 10:2025** (finalized Jan 2026), **NIST CSF 2.0** (Feb 2024), and the current AICPA TSC. Before quoting a specific `Axx` code or control ID to anyone external, **verify against current docs** — the *controls* are durable, the *labels* drift.

---

## OWASP Top 10 — REVIEW-mode checklist

Run top-to-bottom on any web app, API, or Cloud Run service. Each item names the control that *must* be present in this stack and the failure symptom that proves it isn't. The **underlying controls don't change between editions — only the labels and ordering do**, so the checklist below is organized by control, with both the current **2025** code and the still-widely-cited **2021** code on each item (most scanners and a lot of audit boilerplate are still keyed to 2021).

**2025 vs 2021 crosswalk** (so you cite the right code):

| 2025 | Category (2025 name) | Was in 2021 |
|---|---|---|
| A01 | Broken Access Control | A01 (now **absorbs SSRF**, the old A10) |
| A02 | Security Misconfiguration | A05 (moved up) |
| A03 | **Software Supply Chain Failures** (NEW, expands old "Vulnerable & Outdated Components") | A06 |
| A04 | Cryptographic Failures | A02 |
| A05 | Injection | A03 |
| A06 | Insecure Design | A04 |
| A07 | Authentication Failures (renamed from "Identification and Authentication Failures") | A07 |
| A08 | Software or Data Integrity Failures | A08 |
| A09 | Security Logging and **Alerting** Failures (renamed from "…Monitoring…") | A09 |
| A10 | **Mishandling of Exceptional Conditions** (NEW) | — |

### Broken Access Control — `A01:2025` / `A01:2021`
The #1 cause of real breaches, and in 2025 it **also covers SSRF** (see the SSRF block below). Authorization is enforced **server-side, every request, per-tenant** — never in the client, never "the UI hides the button."
- **Supabase / Postgres:** every tenant table has `ENABLE ROW LEVEL SECURITY`, and for owner-proof isolation `FORCE ROW LEVEL SECURITY`, plus a policy keyed on the tenant claim (`auth.jwt() ->> 'tenant_id'` / `auth.uid()`). RLS-off-by-default is the trap: a table with RLS enabled but **no policy** denies all; a table with RLS never enabled is wide open to any authenticated role. The Supabase `service_role` key has the Postgres **`BYPASSRLS`** attribute — it **skips every policy** — so it belongs only in trusted server code (Secret Manager), never shipped to a browser or used as the app's default connection.
- **GCP IAM:** roles are least-privilege and resource-scoped, not project-wide `Owner`/`Editor`. A Cloud Run service runs as a **dedicated** service account with only the roles it needs (e.g. `roles/secretmanager.secretAccessor` for its own secrets, `roles/storage.objectViewer` on one bucket) — never the default Compute SA.
- **SSO / IdP:** app access is group-gated via **IdP groups**, provisioned to the app over **SCIM** — not per-user toggles.
- Symptom of failure: changing an `id` or `tenant_id` in a request returns another tenant's row (IDOR). Test it explicitly — see Test cases below.

### Security Misconfiguration — `A02:2025` / `A05:2021`
- **The public-assets exception is documented and deliberate.** The GCS bucket `public-assets` is **public by design** — its raw object URLs are hotlinked by production a BI dashboard dashboards; flipping it private breaks those dashboards. Do **not** "remediate" it to private. This is the canonical example of why a public-bucket finding must be checked against stated intent before flagging. *Every other* bucket defaults to private + uniform bucket-level access + public-access-prevention **enforced**; a newly-public bucket with no README exception is a real misconfiguration finding.
- **No Full Disk Access to system interpreters** and the `.app`-bundle TCC pattern (see `references/macos-app-bundles.md`) — granting FDA to `/bin/bash` is the macOS analogue of a wildcard IAM role.
- **Cloud Run / container hardening:** run as non-root, drop unnecessary capabilities, set `--no-allow-unauthenticated` unless the service is deliberately public, scope ingress. Don't ship debug endpoints, stack traces, or `DEBUG=1` to production.
- Symptom: default credentials, an over-permissive CORS `*`, a verbose error page leaking stack traces, an unauthenticated Cloud Run URL that should be IAM-gated.

### Software Supply Chain Failures — `A03:2025` (expands `A06:2021` "Vulnerable & Outdated Components")
2025 broadened the old "outdated components" item into the whole supply chain: dependencies, build pipeline, and publish step.
- **Pin everything** (SKILL.md dependency rule): `requirements.txt`/`pyproject.toml` pinned, `package-lock.json` committed, container base images pinned by **digest** (`@sha256:…`) not floating `:latest`.
- Scanners, run as gates (see QA section): `pip-audit` / `bandit` (Python), `npm audit` (JS), **`trivy`** for container image + filesystem CVEs (the Cloud Run image is in scope), and **OWASP Dependency-Check** as the deeper SCA pass when you need CVE-to-CVSS mapping across languages. GCP **Artifact Registry** has built-in vulnerability scanning — turn it on for the analyzer's images.
- **Build/publish integrity:** prefer **npm trusted publishing (OIDC)** for anything you publish — it issues short-lived credentials instead of a long-lived `NPM_TOKEN` and **auto-generates Sigstore provenance** (no `--provenance` flag needed; falls back to `npm publish --provenance` from CI if you're not on trusted publishing). Pull container base images **by digest** so the bytes can't change under you.
- Symptom: `npm audit` HIGH/critical, a `trivy` CRITICAL in a base layer, a `:latest` base image, an unverified curl-to-bash installer in a Dockerfile, a long-lived publish token in CI.

### Cryptographic Failures — `A04:2025` / `A02:2021`
- **TLS everywhere in transit.** Cloud Run is HTTPS-only by default; do not add a plaintext path. Supabase/Postgres connections use `sslmode=require` or stricter.
- **Encryption at rest** is on by default in GCS, BigQuery, and Supabase/Postgres — don't disable it; for regulated data note CMEK as the upgrade.
- **No plaintext secrets, ever.** Keys live in 1Password (`op read`) for human/dev workflows and **GCP Secret Manager** for Cloud Run runtime — injected as a secret-backed env var or mounted volume, never baked into the image or `Dockerfile`. BYO-key tenant API keys are stored encrypted (Secret Manager or an encrypted column), never logged.
- **Crypto-agility + post-quantum readiness — name it, don't hand-roll it.** NIST finalized the post-quantum standards in August 2024 — **FIPS 203 (ML-KEM)** for key establishment, **FIPS 204 (ML-DSA)** and **FIPS 205 (SLH-DSA)** for signatures — and NIST IR 8547 (draft) plots classical RSA/ECC **deprecation ~2030 and disallowal ~2035** (CNSA 2.0 runs a comparable clock). *All of these revise — verify current status and your platforms' PQC rollout against live docs before citing a date or an algorithm to anyone external.* The threat with a clock on it is **harvest-now-decrypt-later (HNDL)**: transport traffic or ciphertext recorded *today* is decrypted when a cryptanalytically-relevant quantum computer arrives — so the exposure that matters is **confidential data whose retention outlives the transition** (`data-protection.md` §4), and the surface is **key exchange/transport**, not everything labeled "crypto." Triage by surface: **AES-256 at rest is already PQ-adequate** (Grover halves the margin to a still-comfortable 128 bits); **signatures (ed25519 commit/deploy keys, cert ECDSA) are not HNDL-exposed** — a future forgery cannot rewrite an already-verified past — and migrate on the NIST/platform timeline. The strategy for this stack is **crypto-agility delegated to managed platforms**: major TLS front-ends (Google, Cloudflare, Chrome) already negotiate **hybrid X25519+ML-KEM** key exchange, so a Cloud Run service inherits post-quantum key exchange transparently — one more reason "TLS everywhere, platform-managed" is the rule and hand-rolled or vendored crypto stays a finding.
- Symptom: a secret value appears in `git log`, a container layer, a log line, or `gcloud run services describe` env output (the structured-logging rule already forbids emitting secrets at any level — verify it). PQ symptoms: a security-questionnaire answer of "post-quantum: not applicable — we use strong modern crypto"; a long-retention confidential data class with no named HNDL consideration in its retention/DPIA decision; a hand-pinned classical cipher-suite list that blocks the platform's hybrid key-exchange rollout.

### Injection — `A05:2025` / `A03:2021`
The standing rules already cover this; this is where you confirm they were followed.
- **SQL:** parameterized queries / bound parameters only — `cur.execute("… WHERE id = %s", (id,))`, never f-string/`%`/`.format()` interpolation into SQL. This holds for SQLite inside single-file scripts (`?` placeholders) and for any Postgres/Supabase access. Supabase RLS is **not** a substitute for parameterization.
- **Shell:** the Bash command-injection rule in SKILL.md — never interpolate user-controlled values into `eval`/`bash -c`/`ssh`/`osascript` strings; pass discrete quoted args; `--` before filenames.
- **Other interpreters:** no untrusted data into template renderers, `os.system`, or BigQuery query strings (use parameterized queries / query parameters there too).
- Symptom: a value containing `' OR 1=1 --` or `; rm -rf` changes control flow.

### Insecure Design — `A06:2025` / `A04:2021`
A flaw you cannot patch your way out of — it's the architecture.
- **Threat-model before building**, especially for the multi-tenant SaaS: where is the tenant boundary, what happens if a JWT is forged or replayed, what's the blast radius of a leaked `service_role` key, can tenant A's BYO-key be billed to tenant B's Stripe customer? Document the trust boundaries (this *is* SOC 2 CC-relevant design evidence).
- Enforce rate limits / abuse limits and quotas on expensive endpoints by design, not as an afterthought.

### Authentication Failures — `A07:2025` / `A07:2021`
- **SSO is the front door; MFA is enforced** via IdP policy. App-level auth (Supabase Auth / GoTrue) validates JWT signature, `exp`, `aud`, and issuer on **every** request — a JWT is not a session you trust forever.
- No homemade password hashing, no auth-by-obscurity, no long-lived non-rotating API tokens. BYO-key and service tokens are revocable and scoped.
- Symptom: a missing `exp` check, an unverified JWT signature, an endpoint reachable without a valid token, MFA optional where the data is sensitive.

### Software or Data Integrity Failures — `A08:2025` / `A08:2021`
This stack already produces strong integrity evidence — confirm it's intact.
- **SSH-signed commits + PR-flow** (SKILL.md): the default branch shows *Verified*; squash-merge preserves web-flow signing (rebase merge silently strips signatures — already documented). Unattended automation is signing-exempt per-invocation.
- **Supply-chain integrity:** verify checksums on downloaded binaries; pull container base images **by digest** so the bytes can't change under you (the publish-side provenance story lives in A03).
- No untrusted deserialization (`pickle` of external data, `yaml.load` without `SafeLoader`).
- Symptom: an unsigned commit on `main` with no documented exemption, a `:latest` base image, untrusted deserialization of external bytes.

### Security Logging & Alerting Failures — `A09:2025` / `A09:2021`
Directly satisfied by the SKILL.md logging standard — this is the audit framing of it. (2025 renamed "Monitoring" to **Alerting**, which sharpens the point: collecting logs nobody alerts on still fails the control.)
- **Structured logging** to `~/Library/Logs/` (local automation) or Cloud Logging (Cloud Run), with rotation/retention caps, **never emitting secrets**. Log security-relevant events: authn failures, authz denials, RLS-policy violations, admin actions.
- **Dead-man's-switch / freshness check** for unattended jobs — the silent non-run is the failure error-grepping can't catch. Alert on *new* events only (state-tracked), allowlist benign noise, summarize don't itemize.
- Cloud Run: ship logs to Cloud Logging, set **log-based metrics + alerting** on auth-failure spikes; consider a sink to BigQuery for retained security analytics.
- Symptom: no record of who accessed what, logs that rotate away before an incident window, a failed job that alerted no one, dashboards with no alert wired to them.

### Server-Side Request Forgery (SSRF) — now **inside `A01:2025`** (was `A10:2021`)
In the 2025 edition SSRF is no longer a standalone item — it folds into Broken Access Control. The control is unchanged: any feature that fetches a **user-supplied URL** (webhook, BYO-callback, image-by-URL, integration import) must **allowlist** destinations and **block link-local/metadata ranges**.
- On GCP the metadata server `169.254.169.254` (a.k.a. `metadata.google.internal`) is the crown-jewel target — it hands out the service-account token to any in-instance request. Deny `169.254.0.0/16`, RFC-1918, `127.0.0.0/8`, `::1`, and **resolve-then-validate** to defeat DNS-rebinding.
- GCP defense-in-depth you inherit: the v1 metadata API **requires the `Metadata-Flavor: Google` request header** (a naive SSRF that only forwards a URL can't set it), and the legacy `v1beta1` header-bypass path is deprecated. Prefer Workload Identity over long-lived SA keys so a stolen token is scoped and short-lived.
- Symptom: a fetch endpoint that will retrieve `http://metadata.google.internal/computeMetadata/v1/` (or `http://169.254.169.254/...`) or an internal `10.x` address and return the body.

### Mishandling of Exceptional Conditions — `A10:2025` (NEW)
2025's new category: failures in how the code handles errors, timeouts, and edge states — fail-open auth, swallowed exceptions, partial writes, and verbose error leakage.
- **Fail closed, not open:** an auth check that throws must deny, not skip. A timeout calling your IdP or database must not default to "allow."
- Don't leak stack traces or internal detail in error responses (overlaps A02); don't `except: pass` over a security-relevant failure; make multi-step operations (Stripe charge + provisioning) atomic or idempotent so a mid-flight error can't half-commit.
- Symptom: an exception path that grants access, a swallowed error that hides a failed RLS check, a 500 that prints the query and connection string.

### Going deeper
- **OWASP ASVS** (Application Security Verification Standard) is the per-requirement verification standard — use it when "did we cover Axx?" needs to become "which specific L1/L2 requirements pass?" Pick a target level (L2 for the B2B SaaS handling tenant data) and verify against it.
- **OWASP Dependency-Check** and **trivy** are the concrete SCA tools backing A03/A08; **OWASP ZAP** is the option for dynamic (DAST) scanning of a running Cloud Run service.

---

## NIST CSF 2.0 — the six Functions, mapped to existing tooling

CSF 2.0 (Feb 2024) added **Govern** as a sixth Function wrapping the original five. Treat it as an inventory of "do we *have* a control here," each line mapped to what this environment already does, with the NIST 800-53 control families that turn it into auditable practice.

| Function | What it means | Already implemented here | 800-53 family |
|---|---|---|---|
| **Govern (GV)** | Policy, roles, risk decisions are documented | Documented policies in `<org>/team-handbook` (`docs/git-workflow.md`); PR-flow, signing, backup-story rules are written down, not tribal | PM, PL |
| **Identify (ID)** | Know your assets & dependencies | Asset/dependency inventory: `Brewfile`/`mas` for Mac software, pinned `requirements.txt`/`package-lock.json`, `gcloud asset inventory` + `gcloud projects get-iam-policy` for cloud assets/roles | CM-8, RA |
| **Protect (PR)** | Safeguards limiting impact | 1Password + Secret Manager (no plaintext secrets), IAM least-privilege, least-FDA + `.app`-bundle TCC, Postgres RLS, SSO/MFA, TLS + encryption-at-rest | AC, IA, SC, MP |
| **Detect (DE)** | Find anomalies & events | Structured logging + log-monitor with state-tracked new-error alerting; **dead-man's-switch freshness checks**; Cloud Logging log-based metric alerts; Artifact Registry image scanning | AU, SI-4 |
| **Respond (RS)** | Act on detected incidents | Source-level alerting (non-zero exit + notification), runbooks in the team-handbook, escalation to email for critical events | IR |
| **Recover (RC)** | Restore after an incident | **3-2-1-1-0** backups (Cloud SQL/Supabase **PITR** + immutable/out-of-domain copy), **scheduled restore drills**, BIA-justified RTO/RPO, GitHub remotes as code backup, Time Machine for local-only repos (`disaster-recovery.md`, `business-continuity.md`) | CP |

**800-53 families that map to concrete daily practice** (cite these by ID when a finding needs a control reference):
- **AC** (Access Control) → RLS policies, IAM bindings, IdP groups. *AC-6 least privilege* is the one you invoke most.
- **AU** (Audit & Accountability) → the structured-logging standard; *AU-9* (protect logs — `chmod 600`, don't world-read), *AU-4* (capacity — the rotation cap).
- **CM** (Configuration Management) → version-controlled config, pinned deps, image digests, infrastructure as declarative state.
- **IA** (Identification & Authentication) → SSO + MFA, JWT validation, SSH-signed commits as developer-identity proof.
- **SC** (System & Communications Protection) → TLS, encryption at rest, SSRF egress controls, network/ingress scoping.
- **SI** (System & Information Integrity) → `bandit`/`trivy`/`npm audit` (flaw remediation, *SI-2*), input validation (*SI-10*), log monitoring (*SI-4*).

Keep it actionable: a CSF "gap" is only real when you can name the missing artifact (no PITR configured, no asset inventory, IAM has a project-wide `Editor`). Don't report "improve governance" — report "no documented backup policy for repo X."

---

## NIST SSDF (SP 800-218) — secure *SDLC*, mapped to what the skill already enforces

CSF is *operational* security; **SSDF is the secure-development-lifecycle framework** (the one behind US EO 14028 and the **CISA Secure Software Development Attestation Form** that federal and many enterprise buyers now require). It is outcome-based and tool-neutral, organized into four practice groups. The skill already *implements* most of it across its references — the value here is **naming the mapping** so a procurement/audit ask ("are you SSDF-aligned?") has an answer. *Verify the current SSDF revision and any attestation-form specifics against NIST/CISA before claiming alignment.*

| Group | What it asks | Already implemented here |
|---|---|---|
| **PO — Prepare the Organization** | Define security requirements, roles, toolchains; secure the dev environment itself | The rigor ladder + security floor (SKILL.md); `dev-environment-isolation.md` (never dev against prod, per-project isolation); documented house standards in `<org>/team-handbook` |
| **PS — Protect the Software** | Protect code & releases from tampering; provide provenance | Per-repo deploy keys + SSH-signed commits + branch protection (SKILL.md SCM); **SBOM + SLSA build-provenance attestation + image signing** (SKILL.md *Supply-chain integrity*, `github-actions.md`, `containers-and-orchestration.md`) |
| **PW — Produce Well-Secured Software** | Threat-model, secure-design, secure-coding, review, test, **verify** | `threat-modeling-and-api-design.md` (STRIDE); the security floor + injection rules; the **SAST/secret-scan/dep-audit/type-check** gates + `testing.md` (incl. fuzzing) + the spec→plan→TDD→review workflow (`engineering-workflow.md`) |
| **RV — Respond to Vulnerabilities** | Find, triage, remediate vulns; root-cause to prevent recurrence | Dependabot trio + zero-open-alerts triage (SKILL.md); the `DEBUG:` root-cause method (`debugging.md`); the incident lifecycle + blameless postmortem (`observability-and-incident-response.md`) |

A real SSDF gap is, again, a *named missing artifact* — "no SBOM published for the released image (PS.3)," not "improve our SDLC."

### Going deeper — AI-governance counterparts to the CSF/SSDF spine

If the product ships AI features, the governance analogues to the CSF (operational) + SSDF (development) spine above are **pointers, not a separate checklist** — governance is lighter-touch here than the security floor. **NIST AI RMF (NIST AI 100-1)** is the voluntary AI risk-management operating model — four functions, **Govern / Map / Measure / Manage** (the AI-specific echo of CSF's Functions); its **Generative AI Profile (NIST AI 600-1)** catalogs the GenAI-specific risk classes (prompt injection, confabulation, data-privacy and IP leakage, value-chain risk) — use it as a risk *menu* to scope what an AI feature must defend, mapping straight onto `references/threat-modeling-and-api-design.md` and the agentic-tool rules. **ISO/IEC 42001:2023** is the certifiable **AI management-system (AIMS)** standard — the ISO counterpart to running SSDF/SOC 2 as a system, often run *with* the AI RMF inside it. *All three revise and the GenAI guidance is young — verify the current publications against NIST and ISO before citing a document number or a named risk class.* Keep it a pointer: invoke these when an AI feature needs a governance reference, not as a gate on every change.

### OpenSSF Scorecard — run it on your OWN repo, not just your dependencies

`foss-adoption.md` uses Scorecard to vet an *inbound* dependency; the same tool run on your **own** repo is a cheap, automatable **posture self-assessment** that scores exactly the PS/PW/RV practices above — Branch-Protection, Token-Permissions, Pinned-Dependencies, Signed-Releases, Dangerous-Workflow, SAST, Dependency-Update-Tool — most of which this skill already enforces. Add the `ossf/scorecard-action` as a scheduled + push-to-`main` workflow with `publish_results: true`; it emits a public score a README badge reads (an honest, live badge — SKILL.md *Documentation*). **Treat a dropped score as a regression to triage**, the same posture as a Dependabot alert.

Notes from running it (verify against current action docs — surfaces drift):
- **SHA-pin the action** (the supply-chain rule) and keep the workflow **minimal — `checkout` + `scorecard-action`.** The optional SARIF→code-scanning upload is *not* needed for the badge, adds action surface, and can break publishing: scorecard's publish-time **workflow verification rejects a `github/codeql-action` pin it treats as an "imposter commit"** (and default-setup CodeQL rejects third-party SARIF anyway).
- `id-token: write` is required to publish (OIDC); a top-level `read-all` is the documented broad read Scorecard needs.
- **Publishing is public** — the score posts to `api.securityscorecards.dev`. For a well-run repo that's a feature; make it a conscious choice, not an accident.

### OpenSSF Best Practices badge — the one lever for Scorecard's `CII-Best-Practices` check

Scorecard *measures* posture automatically; the **OpenSSF Best Practices** badge (bestpractices.dev, formerly the CII Best Practices badge) is the *self-attested* maturity questionnaire that **complements** it — and it is the **single lever** for Scorecard's `CII-Best-Practices` check (that check reads your badge status and nothing else: `passing` scores **5**, `silver` ~**7**, `gold` **10**; no badge scores **0**). A **Tier-2 / serious-public-repo** step, not a Tier-0 one: earning `passing` is a few hours filling the form honestly, and it lifts both the human "is this maintained?" signal and the automated Scorecard number.

Answer it the way this skill answers everything — **honestly, don't over-claim `Met`.** A project that **uses no cryptography** and **ships no running service** answers the whole `crypto_*` block and the `dynamic_analysis` criteria as **N/A** (or **Unmet** where the form offers no N/A option — never a false `Met`); a false `Met` is the same stale-claim failure as a false badge (SKILL.md *Documentation*). The badge you then add is a **live, dynamic** one (the project's `badge.svg` from bestpractices.dev renders current status by construction) — so it can't drift the way a hardcoded level claim would.

---

## Well-Architected — the cloud-architecture pillars (mostly covered; name the framework + the one hole)

The GCP/AWS Well-Architected frameworks review a system across pillars; map them so an architecture review has a vocabulary:
- **Security** → the whole security floor + `threat-modeling-and-api-design.md`, `secure-data-processing.md`. **Reliability** → `disaster-recovery.md`, `business-continuity.md`, `resilience-engineering.md`, `observability-and-incident-response.md`. **Cost** → per-tenant cost metrics + scale-to-zero + BigQuery cost guardrails (`gcp.md`, `observability`). **Operational excellence** → IaC, CI/CD gates, runbooks, DORA. **Performance** → `scalability-and-system-design.md`, the load/perf test tier.
- **Sustainability — the one genuinely-thin pillar.** Add it as a design consideration: prefer **low-carbon GCP regions** (Google publishes per-region carbon data), lean on **scale-to-zero** (idle compute is wasted carbon *and* cost — the two align), and right-size rather than over-provision. Low priority for a solo product, but it's the pillar with no current coverage — name it so it's a conscious deferral, not a blind spot.

---

## SOC 2 — engineering that GENERATES the audit evidence

The CIO-relevant angle: SOC 2 is an *evidence* exercise. Auditors don't read your code — they ask for artifacts proving controls operated over the audit window. **Write code and run processes whose normal output IS that evidence.** The good news: the existing GitHub + logging disciplines already produce most of it.

### The five Trust Services Criteria
| TSC | Scope | In scope for the SaaS? |
|---|---|---|
| **Security** (Common Criteria, CC) | Mandatory for every SOC 2 | Always — this is the core |
| **Availability** | Uptime/SLA commitments | If you commit to an SLA (Cloud Run, status page) |
| **Confidentiality** | Protecting confidential data | Yes — tenant data, BYO-keys |
| **Processing Integrity** | Complete/accurate/timely processing | If correctness of processing is a customer promise |
| **Privacy** | PII handling vs. notice/consent | If you collect PII beyond account basics |

You always do **Security/CC**; add the others only where you make the corresponding promise. Don't over-scope.

### Common Criteria → enforceable practice → the evidence it emits
- **CC6 — Logical & Physical Access.** Controls: SSO + **MFA** enforced, GCP IAM least-privilege, Postgres **RLS** tenant isolation, encryption in transit + at rest, key management via 1Password/Secret Manager.
  *Evidence auto-generated:* your IdP's access-and-MFA reports, `gcloud projects get-iam-policy` exports + IAM recommender, RLS policy DDL in version control, the access-review you can produce from group membership. A periodic IAM-policy snapshot committed to a repo is a turnkey CC6 artifact.
- **CC7 — System Operations.** Controls: monitoring + alerting, the **dead-man's-switch** freshness check, vulnerability scanning (`trivy`/`bandit`/`npm audit`/Artifact Registry), incident detection.
  *Evidence:* the rotating digest logs, alert history, scan reports, the dead-man's-switch catching a stopped job. This is exactly the SKILL.md monitoring standard — it *is* your CC7 control narrative.
- **CC8 — Change Management.** This is the big one, and **you already have it.** The **PR-flow + branch protection + required CI + CHANGELOG + SSH-signed commits** workflow IS the change-management evidence trail an auditor wants: every change is reviewed (PR approval), tested before merge (required status checks), traceable to an author (signed commit), and documented (CHANGELOG + Conventional Commit + structured PR description: *What/Why/Testing*). Squash-merge keeps signatures *Verified* on `main`. Don't build a separate "change management process" — **export the GitHub PR/commit history**; that's the artifact.
- *(CC1–CC5 — control environment, communication, risk assessment, monitoring, control activities)* map to the documented policies in the team-handbook (Govern) and the threat-modeling discipline (Insecure Design / A06). Point at the docs.

### Which existing disciplines already produce SOC 2 evidence (name these)
- **GitHub PR-flow / branch protection / required CI** → CC8 change management (review + test-before-merge).
- **SSH-signed commits** → CC8 author attribution / integrity; CC6 developer identity.
- **CHANGELOG + Conventional Commits + structured PR descriptions** → CC8 change documentation.
- **Structured logging + rotation + dead-man's-switch** → CC7 operations + A09 logging/alerting; AU/SI control families.
- **1Password + Secret Manager + IAM least-privilege + RLS** → CC6 logical access.
- **Pinned deps + `trivy`/`bandit`/`npm audit` + Artifact Registry scanning** → CC7 vulnerability management.
- **`pg_dump`/PITR + GitHub remotes + Time Machine** → Availability (recovery capability) + CSF Recover.

When the SaaS approaches a real SOC 2 Type II, the engineering task is mostly **making this evidence exportable and timestamped over the audit window** — not inventing new controls. Bias every new automation toward leaving an auditable trail (logged, committed, signed) by default.

---

## PCI DSS — scope is the whole game (keep card data off your servers)

If the product takes card payments, the one decision that dominates your PCI DSS burden is **whether raw card data (the PAN) ever touches your servers.** A **hosted card form** — a vendor-hosted checkout page or vendor-hosted embedded fields that post the PAN **directly to the processor** — keeps cardholder data out of your environment entirely, which qualifies you for the **shortest self-assessment (SAQ A)** and shrinks scope to a handful of requirements; the anti-pattern is routing raw PAN through your own API or storing it, which drags you into the **full controls set (SAQ D)** across all 12 PCI DSS requirements. So: **never proxy or persist the PAN** — embed the processor's hosted fields, take back only a token, and treat the token (not the card) as what your code ever sees. *PCI DSS revises: v4.0.1 was published June 2024, and the future-dated v4.x requirements became mandatory 2025-03-31. The new payment-page script controls (6.4.3 script authorization/inventory, 11.6.1 tamper detection) apply to SAQ A-EP / SAQ D scope — and the 2025 SAQ A revision **removed** them for SAQ A merchants, who now only attest the page isn't susceptible to script attacks. Verify your exact SAQ eligibility and the current requirement text against the PCI SSC and your processor before claiming a level.* This is distinct from **HIPAA and FedRAMP, which this skill declares out of scope** (as it does for HIPAA in `data-protection.md`): PCI is *in scope the moment you touch payments*, and the controls that keep its scope small are the same ones the skill already enforces — secrets in a manager, TLS in transit, no sensitive data in logs.

---

## Putting it together in REVIEW mode
1. Identify what the code is (web app / API / Cloud Run service / data pipeline / automation) and which framework lens applies.
2. Walk the **OWASP Top 10** as the concrete bug-finding pass — each finding names the line and the failing control (cite the current 2025 code; add the 2021 code if the audience's tooling still uses it).
3. Map systemic gaps to **CSF Functions** + an **800-53 family** ID so the finding has a control reference.
4. For anything customer-facing, note which **SOC 2 CC** it supports and whether the change *generates or breaks* audit evidence (e.g. a direct-push to `main` bypasses the CC8 trail).
5. Honor the documented exceptions — **public-assets stays public**, unattended commits are signing-exempt — and never flag a deliberate, README-stated decision as a vulnerability.
