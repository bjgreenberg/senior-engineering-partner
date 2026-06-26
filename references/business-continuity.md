# Business Continuity (BC)

Companion reference for the senior-engineering-partner skill.

> **Rigor tier:** the *floor* — a stated backup story and a one-page "what do we do if X is down" — holds at every tier (SKILL.md *Backup & Continuity Floor*). The full BIA, provider-outage runbooks, and a maintained comms plan are **Tier-2 posture**; defer the depth at Tier 0/1 with a `TODO`, but anything with paying tenants or legal data is Tier 2 on sight.

**Disaster recovery is a subset of business continuity.** DR (`disaster-recovery.md`) restores the *data and systems*; BC keeps the *business operating* through the disruption — including the parts that aren't a server: third-party outages, the comms plan, and the human single-points-of-failure. This file is the wider plan; `resilience-engineering.md` is how the software itself degrades instead of dying; `observability-and-incident-response.md` is the live incident. The governing rule: **identify what the business cannot operate without, how long it can survive without each, and a tested plan to keep going — before the disruption, not during it.**

---

## 1. Business Impact Analysis (BIA) — the step that justifies the numbers
RTO/RPO are not picked by feel; they fall out of a BIA. Even a lightweight one beats none:
- **List the critical processes/functions** the product delivers (e.g. tenant login, evidence ingestion, billing, report export).
- **For each, estimate the impact of an outage over time** — what breaks at 1 hour, 1 day, 1 week; the financial, legal/compliance, and reputational cost; any hard regulatory deadline (a DSAR clock, a court deadline) that a delay would blow.
- **Rank by criticality** and let that drive the RTO/RPO per data class in `disaster-recovery.md` §1 and the redundancy you invest in. A function with a 1-hour tolerance and one with a 1-week tolerance do not get the same DR budget.
- **Record it** (a short table in `docs/` or an ADR). The BIA is the *why* behind every recovery target; without it the numbers are unfalsifiable.

---

## 2. Dependency & provider continuity (the outage you don't control)
Most real outages are someone else's. Inventory the external dependencies the product cannot run without and plan for each being down:
- **The critical-dependency list:** cloud region/provider (GCP/Cloud Run), the database, the payment processor (Stripe), the LLM/model provider, email/notifications, DNS, the auth provider. For each: what fails if it's down, and what's the plan.
- **Provider-outage plan per dependency:** graceful degradation in-code (`resilience-engineering.md` — queue the work, serve a degraded mode, fail clear) **plus** the operational response (status-page comms, a documented manual fallback, or simply a stated "we wait it out and our RTO reflects that"). A "we have no plan and didn't know we depended on it" is the failure this prevents.
- **Region/zone redundancy is a tier decision, not a default.** Multi-region is real cost and complexity; for the solo + Cloud-Run posture it's usually a deliberate Tier-2 `TODO`, not assumed. State the choice and what single-region means for RTO (a region outage = down until it recovers, vs. failover). Don't silently assume single-region is fine *or* that multi-region is required.
- **SaaS lock-in is a continuity risk too:** know how you'd export your data from each managed provider (the DSAR/erasure machinery from `data-protection.md` doubles as an exit plan).

---

## 3. Communications & decision plan
When something is down, the *information* path matters as much as the *restore* path:
- **Who declares an incident and who decides** (roll back, fail over, notify) — pre-assigned, even if it's the same one person wearing both hats. Cross-ref the incident roles in `observability-and-incident-response.md`.
- **Status comms:** how affected tenants/users are told (status page, email), the holding-statement template, and the regulatory clocks that may start (a tenant-boundary breach is SEV1 with a 72h privacy clock — `data-protection.md`, `observability-and-incident-response.md`).
- **Where the runbooks live and are reachable when prod is down** — a runbook only in the system that's offline is useless; keep DR/BC runbooks in a separate, always-reachable place.

---

## 4. The solo-operator / bus-factor reality (don't skip this one)
This is a solo developer + agents running a fleet of automation and a commercial SaaS. The single largest continuity risk is often **you being unavailable**, not a server.
- **Name the bus-factor-1 points** — credentials only you hold (1Password, the founder GCP/Stripe/GitHub accounts), knowledge only in your head, automation only you can fix.
- **Reduce them deliberately:** a documented, access-controlled break-glass path (how a trusted party reaches the 1Password Emergency Kit / recovery, the registrar, the cloud billing account); runbooks written so *someone else* could execute the critical restores; the DR drill (`disaster-recovery.md` §5) occasionally run by reading the runbook cold, to prove it's followable without you.
- **The automation fleet needs its own dead-man's-switch** — the health-monitor / freshness checks from SKILL.md monitoring are the continuity control for "a job silently stopped while I was away." Make sure *something* escalates durably (not just an ephemeral notification) when a critical job dies.

---

## Checklist
- [ ] A BIA (even lightweight) ranks critical functions and justifies each RTO/RPO.
- [ ] Critical external dependencies inventoried; each has an outage plan (degrade in-code + operational response).
- [ ] Single- vs multi-region is a *stated* decision with its RTO consequence, not an assumption.
- [ ] Comms plan: who declares/decides, how users are told, which regulatory clocks apply, where runbooks live when prod is down.
- [ ] Bus-factor-1 points named and reduced (break-glass access, followable runbooks, durable dead-man's-switch on the automation fleet).

### Cross-references
- Data/system restore mechanics + 3-2-1-1-0 backups — `references/disaster-recovery.md`.
- In-code graceful degradation that keeps you up *through* a dependency failure — `references/resilience-engineering.md`.
- Live incident lifecycle, severity, postmortem, the 72h breach clock — `references/observability-and-incident-response.md`.
- Privacy obligations, retention, data export as an exit plan — `references/data-protection.md`. Repo/data backup-story floor — `SKILL.md`.
