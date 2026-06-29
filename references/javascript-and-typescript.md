# JavaScript & TypeScript Standards

Companion reference for the senior-engineering-partner skill. The **rules** live in SKILL.md (*Coding Standards* — "modern ES6+, modular/functional, `try/catch` on every network/external call"); this file is the deep toolchain reference — the TS analog of the Python `mypy --strict` + TypedDict mandate, plus the Node back-end patterns that mirror `python-web-apis.md`. Read it when writing or reviewing TypeScript, or any Node service.

The governing principle, mirroring the Python side: **types are only a guarantee if a checker enforces them, and a type only describes the *inside* of the program — every value crossing a trust boundary is `unknown` until validated at runtime.** TypeScript's static types are erased at compile time; they prove nothing about the JSON a client actually sent. *Verify exact compiler-flag names and library APIs against current docs — they are version-specific; the principles are durable.* (Flags below confirmed against the official tsconfig reference — see Sources.)

---

## TypeScript strict mode — the `mypy --strict` analog

SKILL.md mandates `mypy --strict` (or `pyright`) as a **merge-blocking** gate for Python. TypeScript's equivalent is `tsc --noEmit` under a strict `tsconfig.json`, run the same way: locally and as a required CI check, exactly like `bandit`/`semgrep`. New code is clean-on-add; ratchet a legacy untyped codebase (gate touched files, widen over time) rather than blanket-`// @ts-ignore`.

**`"strict": true` is necessary but NOT sufficient.** It turns on the *strict family* (`strictNullChecks`, `noImplicitAny`, `strictFunctionTypes`, `useUnknownInCatchVariables`, …) — but several of the highest-value safety flags are **separate** and off even under `strict`. The mandate is strict mode **plus** these:

```jsonc
// tsconfig.json — the floor, not the ceiling
{
  "compilerOptions": {
    "strict": true,                          // the strict family (null checks, no implicit any, …)
    "noUncheckedIndexedAccess": true,        // arr[i] / obj[k] is T | undefined — forces the guard
    "exactOptionalPropertyTypes": true,      // { x?: T } ≠ { x: T | undefined } — no silent undefined
    "noImplicitOverride": true,              // an override must say `override` — catches base-method drift
    "noFallthroughCasesInSwitch": true,      // a missing `break` is an error, not a surprise
    "noPropertyAccessFromIndexSignature": true, // index-sig access must use obj["k"], not obj.k
    "noImplicitReturns": true,               // every code path returns
    "isolatedModules": true                  // each file transpiles alone (required by esbuild/swc/Babel)
  }
}
```

- **`noUncheckedIndexedAccess` is the one most often missed and the most valuable.** Without it, `const x = arr[i]` is typed `T` even when the index is out of range — a `TypeError: cannot read property of undefined` at runtime that the type-checker swore couldn't happen. With it, every indexed read is `T | undefined` and the compiler forces the guard. This is the TS analog of Python's "don't return `dict[str, Any]`": a too-loose type that defeats the checker.
- **`exactOptionalPropertyTypes`** stops `{ x?: number }` from silently accepting `{ x: undefined }` — the difference between "absent" and "present-but-undefined" that bites at trust boundaries.
- **`useUnknownInCatchVariables`** (on under `strict`) types a caught error as `unknown`, not `any` — you must narrow before using it. Don't fight it with `catch (e: any)`; narrow with `instanceof` / a type guard. This is the static-typing twin of "model output / external input is untrusted."
- **`any` is the type black hole** — it disables checking for every value it touches and propagates silently. Ban it: ESLint `@typescript-eslint/no-explicit-any` as an error. When a type is genuinely unknown, use `unknown` and narrow — `unknown` forces a check, `any` skips it. (`any` is to TS what a bare `except: pass` is to Python.)
- **Lint + format alongside the type-check**, mirroring `ruff`: ESLint (with `typescript-eslint`) + Prettier as their own gate. `tsc` checks types; ESLint checks the patterns types can't (no-floating-promises, no-explicit-any, exhaustiveness).

**`tsc` is a type-checker, not a security boundary.** It is erased at runtime. A green `tsc` says nothing about what a caller actually passes — that is the next section's job.

---

## Typed boundaries — runtime validation (the Pydantic analog)

`python-web-apis.md`'s rule — "every request body is a Pydantic model with field constraints; validation runs before the handler" — has an exact TS counterpart, and it's the single most important pattern here because **static types lie at the boundary.** A `req.body as OnboardRequest` cast is a *no-op at runtime*: it tells the compiler to trust you and emits zero checking code. The JSON could be anything.

- **At every trust boundary — HTTP request bodies/params/headers, env vars, message-queue payloads, third-party API responses, parsed files — validate at runtime with a schema library and derive the static type from the schema.** Keep it tool-agnostic (the runtime-validation ecosystem has several mature options); the discipline is what matters: one schema is both the runtime validator and the source of the TS type, so they can never drift.
  ```typescript
  // schema is the single source of truth; the type is INFERRED from it
  const OnboardRequest = schema.object({
    companyName: schema.string().min(1).max(200),
    type: schema.enum(["individual", "company"]).default("company"),
  });
  type OnboardRequest = Infer<typeof OnboardRequest>;   // derived, never hand-written

  // at the handler boundary: parse, don't cast
  const body = OnboardRequest.parse(req.body);          // throws → 400, never reaches logic as bad data
  ```
- **Parse, don't cast.** `as` is an assertion the compiler cannot verify and never checks at runtime; `.parse()` actually inspects the value. A reviewer seeing `req.body as T`, `JSON.parse(x) as T`, or `: any` on an inbound path should treat it as an unvalidated-input finding — the same weight as a missing Pydantic model.
- **Bound every string (`max`) and enumerate every choice (an enum/literal union).** Identical reasoning to the Python side: an unbounded string is a multi-MB-field DoS and a downstream-injection vector; numbers get min/max. This is the boundary mirror of SKILL.md's "validate all inputs at system boundaries."
- **Never take the tenant id (or any authorization fact) from a validated body.** Schema validation proves the *shape* is well-formed, not that the caller is *allowed* — tenant/role come from the verified token server-side (`python-web-apis.md`, `frontend-web-security.md`), never from the request.
- **A schema can validate but not *trust*.** Validating that `text` is a string doesn't make its content safe to render or feed to a model — indirect-prompt-injection and output-sanitization rules still apply (`secure-data-processing.md`, `frontend-web-security.md`).

---

## Node back-end patterns (mirrors `python-web-apis.md`)

For a Node HTTP service the lifecycle, error, and shutdown disciplines mirror the FastAPI reference one-for-one — the language differs, the failure modes don't.

- **No unhandled promise rejections — ever.** An async error with no `.catch()` / `await` in a `try` is the Node analog of a swallowed exception, and an unhandled rejection can **crash the process** (it terminates by default on current Node). The rules:
  - `await` every promise inside a `try/catch`, or attach a `.catch()`. SKILL.md's "`try/catch` on every network/external call" *is* this rule — async makes it easy to forget.
  - Enable ESLint `@typescript-eslint/no-floating-promises` as an **error** — it statically catches the fire-and-forget call that drops a rejection. This is the single highest-leverage lint rule for a Node service.
  - Install **last-resort** handlers that **log and exit non-zero**, not swallow: `process.on('unhandledRejection', …)` and `process.on('uncaughtException', …)` should log structured detail and let the process restart clean — a process in an unknown state after an uncaught error must not keep serving. (Last resort, not a substitute for handling errors where they occur.)
- **Graceful `SIGTERM` shutdown — the same hook as the FastAPI `lifespan` `finally`.** Cloud Run sends **`SIGTERM`** before evicting an instance (with a termination grace window — verify the current default); a container that ignores it drops in-flight requests and leaks pool connections on the hard `SIGKILL` that follows.
  ```typescript
  const server = app.listen(Number(process.env.PORT ?? 8080));
  async function shutdown(signal: string) {
    server.close();                 // stop accepting new connections; let in-flight drain
    await pool.end();               // close the DB pool cleanly
    process.exit(0);
  }
  process.on("SIGTERM", () => void shutdown("SIGTERM"));
  process.on("SIGINT",  () => void shutdown("SIGINT"));
  ```
  A background worker / Cloud Run Job needs the same shape: trap `SIGTERM`, stop pulling new work, finish or checkpoint the current item, exit 0. Don't `process.exit()` abruptly or skip the `pool.end()`.
- **Don't block the event loop.** Node is single-threaded per process; a synchronous CPU-bound call (`JSON.parse` on a huge payload, a sync `crypto`/`zlib` call, `fs.readFileSync`, a tight loop) stalls **every** concurrent request on that instance — the exact trap as a blocking call inside an `async def`. Use the async (`fs.promises`, streaming) APIs, and offload genuinely heavy work to a `worker_thread` or a separate Cloud Run Job off the request path (`scalability-and-system-design.md`).
- **The rest carries over verbatim** from `python-web-apis.md` — read it as the canonical version and apply the same shape in Node: 12-factor config validated at startup into a frozen object (fail-fast on a missing `DATABASE_URL`); an unauthenticated `GET /health` that doesn't touch the DB; auth as one middleware that verifies the bearer token and opens an RLS-scoped transaction (never trust a client-supplied tenant id); generic auth errors with the specific reason logged; structured JSON logging with no secrets/PII; disable any public schema/playground in prod; allowlist CORS; rate-limit per principal; cap request body size.

---

## Supply chain — see `package-managers.md`, don't re-derive here

The npm supply-chain posture is **fully owned by `package-managers.md`** and is not repeated: commit `package-lock.json` and install with `npm ci` (never `npm install`) in CI; `npm audit` + `npm audit signatures` as gates; treat `postinstall`/lifecycle scripts as the dominant attack vector (`--ignore-scripts` for untrusted one-offs); pin `engines`; no literal `_authToken` in a committed `.npmrc`. Read that reference for the full gate set. The only thing to add at the TS layer: **`@types/*` packages are dependencies too** — they run no code but a malicious or wrong type definition can mis-describe an API and mask a real bug, so they're in scope for the same pin-and-review discipline.

---

## Framework / state / bundler security — the boundary (read, don't go deep)

Front-end framework choice (React/Svelte/Vue/SolidJS…), client state management, and bundler config are a **rabbit hole this reference deliberately does not enter** — they churn fast and are project-specific. The durable, framework-agnostic security facts, with pointers:

- **Rendering untrusted/model-generated content is an XSS sink regardless of framework.** Every framework has an escape hatch — React `dangerouslySetInnerHTML`, Svelte `{@html …}`, Vue `v-html`, `innerHTML` in vanilla — and each bypasses the framework's auto-escaping. Sanitize before using one (markdown render ≠ sanitization). This and CSP, token storage, and the rest of the browser attack surface live in **`frontend-web-security.md`** — that's the reference for client-side security, not this file.
- **The bundle is public — no secrets in it.** Any value that reaches the client bundle (including a build-time env var inlined by the bundler, e.g. a `VITE_`/`NEXT_PUBLIC_` prefix) is shipped to every user. Server-only secrets never cross into client code. (`frontend-web-security.md`.)
- **A bundler/toolchain config and its plugins are a supply-chain surface** like any other dependency — pinned and reviewed via `package-managers.md`; a build plugin runs arbitrary code at build time.
- **Authorization and tenant scope are always server-side** — a client framework's router/guards are UX, never a security control (`python-web-apis.md`, `threat-modeling-and-api-design.md`).

Beyond these, defer to the project's chosen stack docs and a focused review — don't let this reference accrete framework-version specifics that rot.

---

## QA & quality gates (what "done" requires)

- **Type-check gate.** `tsc --noEmit` green under the strict `tsconfig` above — required in CI and run locally, the `mypy --strict` equivalent.
- **Lint + format gate.** ESLint (`typescript-eslint`, with `no-explicit-any`, `no-floating-promises`, switch-exhaustiveness as errors) + Prettier — the `ruff` equivalent.
- **Tests.** Jest (per SKILL.md *Tests*) or Vitest; test the boundary schemas (valid parses, malformed input rejects before the handler runs) and the async error paths — the Node analog of `python-web-apis.md`'s validation-reject and fail-closed cases. Cross-tenant denial is still the un-skippable test (`databases.md`).
- **Supply-chain + secret gates.** Per `package-managers.md` (`npm ci`, `npm audit`/`audit signatures`) and the SKILL.md secret-scan gate.

## Sources

- TypeScript compiler-flag names and strict-family membership verified against the official tsconfig reference: https://www.typescriptlang.org/tsconfig/ (confirmed `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noPropertyAccessFromIndexSignature`, `isolatedModules` are **not** enabled by `strict: true` and must be set separately; `strictNullChecks`/`noImplicitAny`/`useUnknownInCatchVariables` **are** in the strict family).
