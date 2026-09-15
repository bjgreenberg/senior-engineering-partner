# Action Identity & Audit — every action identified, signed, recorded

Companion reference for the senior-engineering-partner skill.

SKILL.md already says *one credential per workload*, *sign your commits*, *emit provenance for builds*, and *cap and monitor every log*. This reference is the rule those four are instances of, extended to the actor the other rules forget: **the agent session**. It exists because "signed" and "identified" drift apart in practice, and because the most frequent actor on a developer machine — an AI agent running with the human's ambient credentials — is usually the one with no record at all.

---

## 1. The rule

No action without three things.

1. **An identity.** One principal per actor: a person, a named agent session, a scheduled job, a service. A credential *is* an identity: never shared, and an automation credential is never used interactively because it was convenient.
2. **A signature**, wherever the medium can carry one (commits, tags, artifacts, statements), bound to the identity in item 1 — not to a key any process on the machine can use.
3. **A durable, tamper-evident record**, written at the moment of the action, naming who or what ran it, what invoked it, and when. Durable means it survives a reboot, a log rotation, the OS aging out its own records, and the loss of the machine.

Where one of the three is impossible for an action, write the gap down with an owner. An implicit gap is the thing an audit later cannot explain.

## 2. Start from a threat model, or nothing can be judged sufficient

Controls are only "enough" against a named adversary. Rank these, cheapest first, and map every control to one:

| | Adversary | Typical shape |
|---|---|---|
| T1 | An honest mistake, by the human or the agent | Wrong merge, stale claim, release cut from the wrong commit |
| T2 | A misbehaving or prompt-injected agent session using the human's **ambient** credentials | The session can sign, merge, deploy and upload as the human, because the keys and tokens sit in the home directory |
| T3 | The workstation compromised or lost | Every local key, token and log at risk at once; a local-only audit log is worthless here |
| T4 | Supply chain | A shipped artifact that does not match the tagged source |

Say what is out of scope (platform insiders, state actors). A design that pretends to cover them covers nothing well.

## 3. Measure before designing — the questions that expose the drift

Ask these of the real system and write the answers in a table; the answers are usually worse than assumed.

- **Who does the host say merged?** On squash-merge the platform re-signs the commit with *its* key. The signature proves the platform did the squash; the merge actor is a login, and an agent using the owner's token and the owner clicking a button produce the **same** login.
- **Can any process on the machine produce the human's signature?** A signing key with no passphrase and no agent confirmation means yes. That signature proves *access to the home directory*, not *the human*.
- **Do agent actions persist anywhere on the machine?** Agent harnesses expose per-call hooks carrying a session id, working directory, tool name and arguments. If nothing writes them down, the session's work exists only in a transcript, which is not an audit source.
- **Can a commit be traced to the session that made it?** Not without a trailer.
- **Does every scheduled job state its trigger and outcome in a common shape?** Per-job logs in per-job formats cannot be reconciled.
- **Which log records age out?** Some OS log stores keep activity-type records for days and ordinary lines for weeks. Evidence read from a volatile store is captured to a file *when observed*, or it will be gone when someone re-runs the query.

## 4. Enforce where a gate can exist; record everywhere

A log line is a diary. A refused action is a control. Put enforcement at every point that can refuse:

- **Host rulesets:** signed commits required; required checks; a required review from the human on pull requests authored by the agent identity. (An author cannot approve their own pull request on most hosts — verify on a real PR — which is exactly why the agent needs its own identity.)
- **A pre-tool hook that refuses interactive use of automation credentials** (the deploy bot's token, the dashboard's read-only token) from an interactive session, and names the correct interactive credential instead. Prove it red first: run the forbidden command, see the refusal.
- **A CI gate for agent commits:** a pull request whose agent-signed commits lack the session trailer fails. Local git hooks are bypassable; the gate lives in CI.

## 5. Identity — make the agent structurally not the human

- **A machine identity for the agent on the code host** — an installed app or a dedicated bot account. Agents open and merge as that identity; the human reviews. The human's approval then becomes a signed, durable object a ruleset can *require*, instead of an instruction in a chat transcript. This is the keystone: without it every other control still collapses agent and human into one login.
- **Separate signing keys per actor class.** The human's key behind a hardware or biometric agent (a Secure Enclave / TPM-backed SSH agent, or at least a passphrase with agent confirmation), so a human signature requires a human present. A separate key for the agent, registered on the host, with its own principal in `allowed_signers`, so `git log --show-signature` tells them apart.
- **Keep per-workload credentials for scheduled jobs and services** exactly as SKILL.md already requires. Do not merge them "for simplicity".

## 6. Record — tamper-evident, off-host, correlated, and read

- **The action log.** A post-tool hook appends one JSON line per agent tool call: timestamp, host, session id, working directory, tool, the command text or the edited path plus a content hash, the outcome, and the invoking chain read from the parent process (terminal, scheduler, editor). **Each line carries the hash of the previous line**, so a deleted or altered line breaks the chain.
- **Off-host, append-only, at write time.** Ship lines as they are written to a sink the writer can only *append* to — an object store with a put-only credential and retention lock, or a separate repository that receives a signed daily digest. This is the answer to T3: the machine can be lost and the record survives. A log the audited actor can edit is not an audit log.
- **Correlation, honestly.** Every artifact an agent produces carries the session id: the commit trailer (`Agent-Session:`/`Agent-Host:` — a *pointer*, distinct from any authorship credit), a comment on the pull request, the release note. The join key is *session id + artifact id*, reconciled by a scheduled job. Do not pretend a magic environment variable threads it through; the reconciliation job does the linking and reports gaps.
- **A common run header for scheduled jobs:** `START <label> pid=<n> host=<h> trigger=<interval|calendar|manual>` and `END status=<n>`, so one reader handles every job.
- **A reader for everything.** Actions in the last 24 h by session and job, chain integrity, reconciliation gaps — on the dashboard the human already looks at. A record nobody reads is a stamp with no reader.

## 7. Provenance — attest what ships, not only who committed

- **Artifacts built in hosted CI:** use the host's build-provenance attestation (keyless, short-lived certificate bound to the workflow identity). On GitHub, private repositories use a host-run signing instance with no public transparency log, so nothing about the repository leaks — verify the current terms for your host and plan.
- **Artifacts built on a workstation** (a store-submitted binary, a signed installer): the build script emits a provenance statement — source tag and commit, builder script hash, toolchain version, timestamps — signs it with the *actor's* key, and attaches it to the release. The release checklist verifies it before upload.

## 8. The audit tests itself

- **Nightly reconciliation** of the action log against the host's event stream (merges, pushes, releases) and the commit trailers; every gap becomes a visible work item.
- **Quarterly drills, each proven red first:** delete a log line and confirm the chain check flags it; push a commit without a trailer and confirm CI rejects it; use an automation token interactively and confirm the hook blocks it; alter a provenance statement and confirm verification fails. Record the results with dates.

## 9. Fleet-wide, forever — the conformance gate

A standing rule makes compliance likely. A gate makes non-compliance visible. Keep an **inventory** of every repository, scheduled job, deployed service and shipped artifact, with one column per control, and a **scheduled check** that regenerates it from the real rulesets, workflows and logs and files a work item for every "no" the rule says should be "yes". A project created next month that skips the structure then shows up within a day instead of during an incident.

## 10. What this does not solve — write it down

Actions taken in the human's own browser session (a vendor support form, a console click) stay on the human's identity; the record is the transcript plus the vendor's case identifier. Approval given in chat before the agent has its own identity is a transcript, not an artifact. Both are gaps with an owner, not omissions.

---

## Sources

- SLSA — Supply-chain Levels for Software Artifacts (slsa.dev)
- Sigstore — keyless signing and transparency logs (sigstore.dev)
- NIST SP 800-92 — Guide to Computer Security Log Management
- OWASP Top 10 for Agentic Applications — see `references/agentic-ai-security.md`
