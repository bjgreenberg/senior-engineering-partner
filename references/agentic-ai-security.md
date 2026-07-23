# Agentic AI Security — securing products that ARE agents

Companion reference for the senior-engineering-partner skill.

**Scope:** the *security* of software that gives a model **tools that act on the world** — a tool-calling loop, an orchestrator-workers system, an MCP-connected agent, or coordinated multi-agent workers. This is the surface the adjacent references deliberately don't own: `llm-apps.md` designs the loop but declares security "owned elsewhere"; `secure-data-processing.md` secures the *document-analysis* shape (parser → model → tenant boundary → RAG); `local-and-agentic-ai-tools.md` hardens the agentic *tools you run* (Claude Code, Ollama, MCP servers you connect); `multi-agent-coordination.md` governs *coding* agents racing in a git tree. This file applies when **the product you ship is itself an agent** — the model's autonomy is an attacker's lever, and every tool is a new trust boundary.

> **Rigor tier:** the least-agency (§2) and human-in-the-loop (§3) rules are **floor** for any agent that takes a consequential action (money, data mutation, outbound message, code execution) — no tier defers them. What scales with tier is *depth*: a Tier-0 single-tool spike names the surface; a Tier-2 multi-agent product runs the full MAESTRO threat model (§8) and the Agentic-Top-10 mapping (§7) as an audit artifact.

> *Framework codes, titles, and layer names below are version-volatile. The `ASIxx` titles in §7 are the official 2026-edition wording, verified against the OWASP primary document; MAESTRO's layers are verified against the current CSA reference. They can still revise between editions — reconfirm against the current OWASP GenAI / CSA sources before quoting a label externally.*

---

## 1. The shift — the agent is the attack surface

A single LLM call has one untrusted input (the prompt) and one output you validate. An **agent** dissolves that boundary: it reads tool results (untrusted), decides its own next action (model output you now *act on*), and carries state across steps (a poisoning target). The defining change is that **model output stops being a string you inspect and becomes an action you execute** — so the question shifts from "is this text safe to show?" to "is this action safe to take, with these arguments, right now?" Every section below answers a slice of that. The three loads that make an agent riskier than a chat feature: **excessive agency** (§2), **consequential action without a gate** (§3), and **trust in its own inputs** — tool results, memory, peers (§2, §5, §6).

## 2. Least agency — the core control

The agentic form of least privilege (SKILL.md *Principle of Least Privilege*): the model's *authority* is bounded, not just its file access.

- **Every tool is least-privilege by construction.** A tool is an API you handed the model — scope it to exactly the task. No `run_shell(cmd)` where `restart_service(name: enum)` suffices; no `query(sql)` where three named parameterized queries do. **Free-form string parameters (shell, SQL, path, URL) are the highest-risk tool shape** — the model can be argued into any value, so the *tool*, not the prompt, must constrain it.
- **Validate tool arguments as a trust boundary — the model is the untrusted caller.** Treat the arguments the model emits exactly like an internet request body (SKILL.md *Input Validation*; the injection-prevention rules apply verbatim): bound strings, enumerate choices, canonicalize paths, reject SSRF-shaped URLs (incl. cloud metadata `169.254.169.254`). An injected instruction reaches your systems *through a tool call* — the arg validator is where it dies.
- **Tool results are untrusted input on every iteration.** A fetched page, a DB row, a peer agent's message can carry an injection that becomes the agent's *next* prompt. Fence tool results as untrusted content (`secure-data-processing.md` §2's two-zone fence); never concatenate them into the instruction zone. (`llm-apps.md` §4 states this for the loop; it is load-bearing enough to restate at the security boundary.)
- **Bound the loop** — iteration cap, cost budget, deterministic done-condition, kill-switch. Owned in full by `llm-apps.md` §5; not repeated here. An uncapped agent is both a billing-DoS and an unbounded-blast-radius actor.

## 3. Human-in-the-loop for consequential actions

`local-and-agentic-ai-tools.md` Part A makes "no blind auto-accept" the rule for the coding agents *you* run; this applies the same rule to the agent *you ship*.

- **Classify every tool by reversibility; gate the irreversible set.** Money movement, data deletion/mutation of record, third-party outbound messages, credential/permission changes, code execution, purchases → an explicit human confirmation *before* execution. Read-mostly tools run unattended.
- **Gate the *resolved call*, not the plan.** Confirming "I'll process the refund" is not confirming `refund(order=X, amount=$4,900)` — show the resolved arguments, because injection changes the arguments, not the narration. (This is the sharp edge; the rest of the gate is standard least-privilege.)
- **Consequential tools carry an idempotency key + append-only audit** — a retried at-least-once loop *will* re-fire (`scalability-and-system-design.md`), and "the agent did it" is not an audit trail (`secure-data-processing.md` §3). Record the call, its arguments, and the approving human.

## 4. Identity, privilege & secrets

- **Scoped, attributable identity — never a shared god-credential.** Each agent (and, multi-tenant, each *tenant's* run) uses a least-privilege per-workload credential, DI'd not read from the process env (SKILL.md *one credential per app/workload*; `secure-data-processing.md` §2). A hijacked agent then reaches exactly its scope, attributed to the right principal.
- **Secrets never enter model context — reference, don't resolve** (`local-and-agentic-ai-tools.md`): the runtime resolves an `op://`-style reference at tool-exec time, outside the model's view. A secret the model can read is one an injected instruction can exfiltrate through the next tool call.
- **No privilege escalation across the loop.** The agent's authority at step N equals its authority at step 1 — no tool grants new scope mid-run, no "the model asked nicely" widening.

## 5. Memory & context poisoning

An agent that persists state (conversation memory, a scratchpad, learned preferences, a shared blackboard) has a **write-once, trust-forever** surface: content written in one (possibly injected) turn steers every later turn.

- **Stored memory is untrusted on read-back**, like a RAG chunk (`secure-data-processing.md` §4's poisoned-corpus rule). A "remembered" note — "the user authorized skipping confirmations" — must not silently become policy; re-fence it, and let recalled memory carry *data*, never *instructions*.
- **Scope memory to the principal and session.** Cross-user/cross-tenant memory bleed is the shared-key-cache failure (`caching.md`): the memory key encodes tenant/user, or one agent's context leaks into another's.
- **Consequential decisions don't rest on unverifiable memory.** If "we already confirmed this refund" comes only from memory, re-verify against the system of record before acting.

## 6. Multi-agent — inter-agent trust & cascading failure

The moment agents call agents, two failure modes appear that a single agent lacks. (Product security — distinct from `multi-agent-coordination.md`'s git-concurrency of *coding* agents.)

- **A peer agent's message is untrusted input, not a trusted RPC.** Agent-to-agent (A2A) messages get the same fence + arg-validation as any tool result — a hijacked sub-agent emits hostile instructions to its caller. Authenticate the sender; validate the payload; don't manufacture trust from "it's one of ours."
- **Bound cascades.** Error propagation and retry storms across a cluster are `resilience-engineering.md` failure modes (timeout, capped backoff, circuit breaker, bulkhead) applied to inter-agent calls. A supervisor that re-dispatches a failing worker without a breaker builds a reinforcing loop.
- **Bound emergent behavior explicitly.** Delegated chains drift (goal drift) and coordinating agents can converge on unintended strategies — cap with the loop brake (`llm-apps.md` §5) *plus* a supervisor-level done-condition and a **cluster-wide** cost/iteration budget, not just per-agent.

## 7. Name the framework — OWASP Top 10 for Agentic Applications (2026)

The sections above *implement* the controls; this **names the mapping** so an audit ask ("are you aligned to the OWASP Agentic Top 10?") has a one-line answer — the same move as `secure-data-processing.md` §5 (LLM Top 10) and `compliance.md`. Titles below are the official `ASI01`–`ASI10` of the **2026 edition** (published 2025-12-09 by the OWASP GenAI Security Project), **verified against the primary document**. *Labels can still revise between editions — reconfirm against the current OWASP GenAI list before quoting externally.*

| Code | Title (2026 edition) | Where this skill handles it |
|---|---|---|
| `ASI01` | Agent Goal Hijack | §2 tool-results-untrusted + `secure-data-processing.md` §2 fence — injected content must not redirect the objective |
| `ASI02` | Tool Misuse & Exploitation | §2 least-privilege tools + arg validation — a weaponized-via-parameters tool dies at the constrained signature |
| `ASI03` | Identity & Privilege Abuse | §4 — scoped attributable identity, no mid-loop escalation, secrets out of context |
| `ASI04` | Agentic Supply Chain Vulnerabilities | SKILL.md *Supply-chain integrity* applied to agent components; review a connected MCP server per `local-and-agentic-ai-tools.md` Part C |
| `ASI05` | Unexpected Code Execution (RCE) | §2 — no free-form `run_shell`/`eval`-shaped tool without a hard sandbox (SKILL.md *Bash Command Injection Prevention*) |
| `ASI06` | Memory & Context Poisoning | §5 in full |
| `ASI07` | Insecure Inter-Agent Communication | §6 — A2A messages fenced, senders authenticated, payloads validated |
| `ASI08` | Cascading Failures | §6 + `resilience-engineering.md` — breakers, bulkheads, cluster-level budgets |
| `ASI09` | Human-Agent Trust Exploitation | §3 — consequential actions gated on the *resolved* call; `llm-apps.md` §6 evals catch confident-wrong |
| `ASI10` | Rogue Agents | §2 loop brakes + §4 bounded static privilege + §3 gates — a misaligned agent is capped in authority, budget, reach |

## 8. Threat-model multi-agent systems with MAESTRO

For a multi-agent product, walk **CSA MAESTRO** ("Multi-Agent Environment, Security, Threat, Risk, & Outcome"; Ken Huang / Cloud Security Alliance, 2025) as the agentic threat-modeling pass — the sibling to STRIDE-per-trust-boundary in `threat-modeling-and-api-design.md`. Do both: STRIDE per boundary, MAESTRO per layer. The seven layers, each with a threat checklist:

1. **Foundation Models** — the model/API/inference engine (adversarial examples, jailbreak, model DoS).
2. **Data Operations** — memory stores, vector DBs, RAG pipelines (poisoning — §5, `secure-data-processing.md` §4).
3. **Agent Frameworks** — orchestration, tool bindings, routing (tool misuse — §2; router misclassification — `llm-apps.md` §2).
4. **Deployment & Infrastructure** — containers, K8s, cloud (`containers-and-orchestration.md` / `gcp.md`).
5. **Evaluation & Observability** — monitoring, anomaly detection (per-tenant cost + agent-loop tracing — `observability-and-incident-response.md`).
6. **Security & Compliance** — authn/authz, audit logging. **CSA frames this as a *vertical* layer that cuts across all the others** — treat it as the plane the other six sit inside, not a peer.
7. **Agent Ecosystem** — UIs, agent marketplaces, integration APIs (the exposed edge — `threat-modeling-and-api-design.md`, `frontend-web-security.md`).

MAESTRO's added value over per-layer checks: **cross-layer attack chains** (an L2 poisoned memory triggering an L3 tool misuse) and **emergent threats** — reasoning collapse, covert inter-agent coordination, goal drift in delegated chains (§6). Deliverable: layer findings + cross-layer cascade scenarios + a defense-in-depth roadmap, defaulting to zero-trust between layers and least privilege within each.

## Sources

- OWASP GenAI Security Project — *OWASP Top 10 for Agentic Applications* (2026 edition, published 2025-12-09); codes `ASI01`–`ASI10`, titles verified against the primary document. Reconfirm against the current edition before quoting externally.
- Cloud Security Alliance — *MAESTRO: Agentic AI Threat Modeling Framework* (Ken Huang, 2025-02-06); the seven-layer architecture, Layer 6 vertical/cross-cutting.
- Within this skill: `llm-apps.md` (loop design + brakes), `secure-data-processing.md` (fence, output validation, tenant boundary, RAG), `local-and-agentic-ai-tools.md` (agentic-tool least privilege; MCP-server review, Part C), `threat-modeling-and-api-design.md` (STRIDE, API contract), `resilience-engineering.md` (breakers/bulkheads), `multi-agent-coordination.md` (coding-agent concurrency — a *different* multi-agent concern).
