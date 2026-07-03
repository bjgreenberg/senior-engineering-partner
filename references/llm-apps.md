# LLM Application Engineering — loop patterns, agent loops, RAG & evals

Companion reference for the senior-engineering-partner skill.

**Scope:** the *design* of software that contains model calls — which loop shape to reach for,
when to loop at all, how a loop stops, how retrieval fits (§7), and how you prove the feature
works (evals). The
*security* of that software is owned elsewhere and deliberately not repeated: hostile input /
indirect prompt injection / model-output validation live in `secure-data-processing.md`;
self-hosted models and agentic dev tools in `local-and-agentic-ai-tools.md`; per-tenant cost
metering and model-call observability in `observability-and-incident-response.md`; and the
model API is an outbound dependency like any other — it gets the full `resilience-engineering.md`
treatment (timeout, capped backoff+jitter, circuit breaker, kill-switch — and client retries
honor `retry-after`, per `secure-data-processing.md` §2).

> **Rigor tier:** a Tier-0 prototype may hand-wave the eval suite; anything with real users
> ships loops with brakes and features with evals. The cost-runaway rules in §5 are
> floor-adjacent — an unbounded model loop spends real money at machine speed.

> *Pattern names and the quoted guidance follow Anthropic's published engineering material
> ("Building Effective Agents", the Claude Agent SDK posts) as of this writing; the operational
> rules beyond the quotes are this skill's own discipline. API parameters, model names, and
> tool interfaces are version-specific — verify against current docs before pinning a specific
> version or parameter.*

---

## 1. Start simple — the escalation ladder

The published guidance is blunt: *"optimizing single LLM calls with retrieval and in-context
examples is usually enough."* Complexity is an escalation you justify, not a default — each
rung trades latency, cost, and **compounding error** for capability:

1. **A single call**, with a well-engineered prompt, retrieval, and in-context examples
   (retrieval architecture in §7).
2. **A workflow** — LLM calls orchestrated through *predefined code paths* (§2). Deterministic
   control flow, model-shaped steps.
3. **An agent** — the LLM *dynamically directs its own process and tool usage* (§4). Reach for
   this only when the path genuinely can't be predefined.

This is YAGNI applied to model architecture (SKILL.md *Modular & Reusable Code*): a loop nobody
demonstrably needs is dead complexity that still burns tokens and compounds errors. Before
adding a loop, show the single-call version failing on a real case.

## 2. The five workflow patterns (predefined code paths)

| Pattern | Shape | Use when | Watch out |
|---|---|---|---|
| **Prompt chaining** | steps in sequence, each call consumes the previous output | a task decomposes cleanly into fixed stages (draft → refine → format) | error compounds down the chain — validate between steps (a gate check), don't just pipe |
| **Routing** | classify the input, dispatch to a specialized handler | distinct input classes deserve different prompts/models | the router is a single point of misclassification — eval it separately |
| **Parallelization** | independent subtasks run simultaneously (**sectioning**), or the same task run N times for diverse takes (**voting**) | subtasks don't depend on each other; or independent perspectives raise confidence | voting needs a defined aggregation rule up front, not post-hoc cherry-picking |
| **Orchestrator-workers** | a central LLM decomposes dynamically, delegates to workers, synthesizes | subtasks can't be predicted ahead of time | the orchestrator's decomposition is itself model output — bound worker count and depth |
| **Evaluator-optimizer** | one call generates, a second evaluates and feeds back, in a loop | see §3 — the feedback loop has preconditions | the one that runs away without a brake (§5) |

## 3. Evaluator-optimizer — the feedback loop has preconditions

The generate → critique → regenerate loop (colloquially, loop prompting) is the pattern people reach for
first, and the guidance gates it on **two signs of good fit**: (a) *LLM responses can be
demonstrably improved when a human articulates their feedback*, and (b) *the LLM can provide
such feedback*. Both must hold.

- **Clear evaluation criteria, or don't loop.** If you can't write down what the critic checks
  (a rubric, a spec, named defect classes), the critic emits vibes and the loop converges on
  confident-sounding, not better. The criteria are a reviewable artifact — put them in the
  critic's prompt, not its weights.
- **Expect diminishing returns.** Most of the improvement lands in the first iteration or two;
  each pass multiplies token cost. A fixed small iteration cap (2–3) with a quality-floor exit
  usually beats "loop until the critic approves" — a critic that *never* approves is a hang,
  and one that *always* approves after flattery is worse.
- **Keep generator and critic prompts independent.** A critic that sees the generator's
  reasoning inherits its blind spots — the same independence rule as the skill's adversarial
  review lenses (`engineering-workflow.md` §4a, which is this pattern applied to a diff).

## 4. The agent loop — gather context → take action → verify work → repeat

When the path can't be predefined, the loop shape is the agent loop, and its load-bearing beat
is the third one: **verify work at every iteration** — that's what separates a controlled loop
from a black box.

- **Prefer deterministic verifiers.** A failing test, a compiler, a schema validation, a
  measurable score — these give the loop a ground truth that model self-assessment cannot
  (the *deterministic-first* rule, applied inside the loop). "Does it look done?" is not a
  verifier; `pytest` exiting 0 is.
- **One increment per iteration.** An agent asked to do everything at once does too much and
  verifies nothing; scope each iteration to one verifiable step (the same
  small-steps-with-checks rule as the engineering workflow's plan phase).
- **Checkpoint between iterations** for long-running loops — persist progress so a re-entry
  resumes instead of restarting, and make iteration actions **idempotent**: an at-least-once
  loop *will* re-run a step (the same rule as queue consumers,
  `scalability-and-system-design.md`).
- **Tool results are untrusted input.** Whatever the loop reads from the world (a fetched page,
  a file, another model) goes through the same validation as any external data
  (`secure-data-processing.md`) — an agent loop is an injection surface on every iteration.

## 5. Every loop gets a brake — stopping criteria & budgets

An LLM loop with no cap is a **reinforcing loop with a credit card** — the
`scalability-and-system-design.md` "name the loop" lens and the billing-DoS/retry-storm rules
(`secure-data-processing.md` §2) apply verbatim. The published guidance notes it's *common* to
include stopping conditions (such as a maximum number of iterations) to maintain control; this
skill makes it a mandate. Every loop ships with **all three**:

1. **A deterministic done-condition** — the test passes, the schema validates, the score
   clears the threshold. Not "the model says it's done" alone.
2. **An iteration/turn cap** — a hard maximum, chosen deliberately, alerting when hit (a loop
   that regularly hits its cap is a design smell, not a config to raise silently).
3. **A token/cost budget** — per run and per tenant, metered where the money is counted
   (`usage_events` — `observability-and-incident-response.md`), with a per-tenant spend alert.
   Cost is a security property here, not an optimization.

Add a **kill-switch** for any loop that acts on the world (`resilience-engineering.md`) —
flippable without a deploy — and fail *closed* on verifier errors: a loop that can't verify
must stop, not shrug and continue (SKILL.md *Reliability for Automation*).

## 6. Evals — the outer loop

The loops above are inner loops; the one that makes any of them safe to change is the outer
one: **every LLM feature ships with an eval suite, and a prompt change is a code change** —
branch → PR → eval validation, the same gate discipline as everything else in this skill.

- **Scenario suites with expected/anti behaviors.** Encode what a good response must contain
  *and* what it must not (the anti-behaviors catch the failure the happy-path check misses).
  Use deterministic asserts where the output allows; an **LLM-as-judge** where it doesn't —
  and treat the judge as a component with its own failure modes.
- **Record a baseline BEFORE changing anything.** A prompt edit validated against "seems
  better" is hope; validated against a recorded baseline it's a measurement. Re-run both modes
  under the same harness and compare like-for-like.
- **Judge variance is real — measure the noise floor.** Single-scenario flips are noise until
  causally analyzed (re-run the flipped scenario, read the transcript, trace the miss to a
  text change or clear it as variance). Multi-scenario shifts are signal. Never delete or
  soften a scenario to get green — the flaky-test rules (`testing.md`) apply to evals.
- **Close the loop on mistakes.** Every failure a human catches becomes a durable instruction
  (a prompt rule, a scenario, a skill edit) — the CLAUDE.md/skill feedback loop. A mistake
  caught twice without a new guard is a process gap, not bad luck.

## 7. RAG — grounding the model in your data (retrieval as architecture)

Retrieval-augmented generation is rung 1 of the ladder (§1) — *a single call with retrieval*
— not an agent pattern. Like every other rung, it earns its complexity only after a simpler
shape demonstrably fails:

- **Escalate into RAG, don't start there.** If the corpus fits the context window, put it in
  the context (with prompt caching for the stable prefix — `caching.md`); a vector database
  serving a corpus that would fit in one prompt is YAGNI with infrastructure bills. Reach for
  retrieval when the corpus outgrows the context, changes faster than you'd re-prompt, or must
  stay tenant-scoped. Fine-tuning is for style/format, not knowledge freshness — a later
  resort, not the next rung.
- **The retrieval pipeline is deterministic software — engineer it like any other.** Chunking,
  embedding, indexing, and query construction are testable, versionable code paths (the
  deterministic-first rule). Pin the embedding model version — a silent embedding-model swap
  invalidates the whole index (vectors from different models don't compare); re-embed
  deliberately, like a schema migration. Version the chunking strategy, and rebuild the index
  as a reproducible batch job, not an accretion.
- **Evaluate the retriever separately from the generator.** A wrong RAG answer is usually a
  retrieval miss, not a generation failure — and you can't fix what you can't attribute.
  Keep a labeled query→relevant-chunks set and measure retrieval deterministically
  (recall@k-style metrics), then eval the end-to-end answer per §6. Log which chunks each
  answer used, so a bad answer traces to what the model actually saw.
- **Ground truth, or say so.** Retrieved chunks carry provenance (source document, section);
  the answer cites its sources so a human can verify. Set a relevance floor: below it, answer
  "not found in the corpus" or fall back — stuffing weak matches into the prompt trades a
  visible "I don't know" for a confident wrong answer.
- **The index is a derived cache of the corpus** — `caching.md`'s invalidation rule applies:
  re-embed on document change, and **erasure must reach the vector store** — embeddings and
  stored chunks of an erased document are still that document's data (`data-protection.md`'s
  verified-cascade rule extends to the index).
- **Cost:** bounded top-k retrieval caps the prompt size — for a large corpus RAG is also the
  cost-control shape; meter tokens per §5 either way.

The security half — tenant isolation in the vector store, the poisoned-corpus injection path,
the embedding-call egress — is `secure-data-processing.md` §4, and it is floor, not
tier-scaled polish.

## Sources

- Anthropic, *Building Effective Agents* — the five workflow patterns, agent definition, the
  evaluator-optimizer fit criteria, start-simple, and stopping-condition guidance
  (anthropic.com/research/building-effective-agents).
- Anthropic engineering: *Building agents with the Claude Agent SDK* (the gather → act →
  verify → repeat loop) and *Effective harnesses for long-running agents* (incremental
  iterations, checkpointing); Claude Code best-practices (deterministic success criteria).
