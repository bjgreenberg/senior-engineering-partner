# Frontend / Web-App Security

Companion reference for the senior-engineering-partner skill.


SKILL.md mandates **responsive design** (layout); this is the **client-side security** layer it doesn't cover. `threat-modeling-and-api-design.md` and `python-web-apis.md` defend the API; this defends the **browser** — the half of the attack surface that runs on untrusted machines. Worked example: the the example SaaS SPA (`frontend/index.html` today — a no-build page pulling `marked.js` from a CDN and rendering model-generated report markdown; re-platforming to SvelteKit + a Firebase Auth client per the plan). Rendering attacker-influenced report content in a privileged session is exactly where a client-side bug becomes a breach. Cross-ref `python-web-apis.md` (the server sets the headers/CORS), `threat-modeling-and-api-design.md` (the API contract), `secure-data-processing.md` (model output is untrusted — §2), `data-protection.md` (no PII in client storage/logs), `compliance.md` (OWASP A03 Injection / A07 Auth).

The governing rule: **the client is untrusted and so is everything it renders — every security decision is enforced server-side; the frontend's job is to not *add* a vulnerability.** *Verify exact CSP directive names, header syntax, and framework escaping APIs against current docs — they are version-specific; the principles are durable.*

---

## 1. Token & session handling (the #1 frontend mistake)
- **Never store a bearer/session token in `localStorage` or `sessionStorage`.** Both are readable by any JavaScript on the page — one XSS and the token is exfiltrated. Use either an **httpOnly + Secure + `SameSite` cookie** (the browser holds it; JS can't read it) or keep a short-lived token **in memory only** (a JS variable / framework store), re-acquired on reload. For a Firebase Auth client, let the SDK manage token lifecycle and **send the ID token per-request** (Authorization header) rather than persisting it yourself.
- **Scope and expire.** Short token lifetimes + silent refresh; on logout, clear in-memory state and invalidate the server session/cookie.
- **The token proves identity; it never carries authorization the client can edit.** Tenant scoping and roles are derived server-side from the verified token (`python-web-apis.md`), never read from a client-held claim the user could tamper.

---

## 2. Content Security Policy (the highest-leverage control)
- **Ship a strict CSP header** — it's the backstop that turns an XSS bug from "account takeover" into "blocked." Lock `script-src` to your origin + explicit hashes/nonces; **no `unsafe-inline`, no `unsafe-eval`**; set `object-src 'none'`, `base-uri 'none'`, and `frame-ancestors 'none'` (clickjacking). Use a per-response **nonce** for any inline script you genuinely need.
- **A CDN `<script>` is a CSP and supply-chain hole.** The current `marked.js`-from-CDN pattern means `script-src` must allow that origin and trust it forever. Prefer vendoring the dependency (served from your origin) so CSP can stay tight; if a CDN is unavoidable, pin it with **Subresource Integrity** (`integrity=` hash) so a compromised CDN can't swap the file (§6).
- Roll out in `Content-Security-Policy-Report-Only` first, watch the violation reports, then enforce. *Verify directive names/values against the current CSP spec before shipping.*

---

## 3. XSS & output encoding (untrusted content rendered in a trusted session)
- **Let the framework auto-escape; never defeat it.** React/Svelte/Vue escape by default — `dangerouslySetInnerHTML`, Svelte `{@html ...}`, `v-html`, and `innerHTML =` are the explicit opt-outs and each is an XSS vector. Treat any use as a reviewed exception.
- **Model output and document content are untrusted (`secure-data-processing.md` §2).** The report markdown the SPA renders is influenced by attacker-supplied evidence — a markdown→HTML render (`marked.js`) can emit `<script>`/`onerror`/`javascript:` payloads. **Sanitize the rendered HTML** (e.g. a vetted sanitizer like DOMPurify) *after* markdown conversion, with a strict allowlist, before insertion. Markdown rendering is not sanitization.
- **Encode per context** — HTML body, attribute, URL, and JS contexts each need different encoding; the framework handles body/attribute, but a URL built from user input (`href`/`src`) must be validated against an allowlist (no `javascript:`).

---

## 4. CSRF (only if you use cookie auth)
- **Token-in-header auth is largely CSRF-immune** (the attacker's site can't read your token to set the header). **Cookie auth is not** — add `SameSite=Lax` or `Strict` on the session cookie (the baseline defense) **plus** a CSRF token (synchronizer or double-submit) for state-changing requests. Decide your auth model first; the CSRF posture follows from it.
- Never perform a state change on a `GET`.

---

## 5. Security headers (set server-side — `python-web-apis.md`)
Beyond CSP: **HSTS** (`Strict-Transport-Security`, force HTTPS), **`X-Content-Type-Options: nosniff`**, **`Referrer-Policy`** (e.g. `strict-origin-when-cross-origin` — don't leak full URLs/paths), **`Permissions-Policy`** (disable camera/mic/geo you don't use), and frame-blocking via CSP `frame-ancestors` (modern) or `X-Frame-Options` (legacy). CORS stays an **allowlist**, never `*` with credentials (`python-web-apis.md`). *Verify header names/values against current docs.*

---

## 6. Dependency & supply-chain (the frontend ships third-party code to users)
- **Pin and lock** (`package-managers.md`): committed lockfile, exact versions, `npm ci` in CI; a frontend dependency runs in your users' privileged sessions, so a malicious update is a direct compromise.
- **SRI for anything off-origin** (`integrity=` + `crossorigin`) so a CDN swap is rejected by the browser.
- **A build step is a security feature** — it lets you vendor deps, apply CSP nonces, and drop the runtime CDN trust the current no-build page depends on. This is a concrete security reason to favor the planned SvelteKit move.

---

## 7. Never trust the client
- **Every authorization and tenant-scoping decision is server-side** (`python-web-apis.md` token→GUC→RLS). Client-side route guards and hidden buttons are **UX, not security** — assume the user can call any endpoint directly with a crafted request.
- **No secrets in client code or the bundle** — API keys, service credentials, and admin flags belong on the server; anything shipped to the browser is public.
- **No PII or evidence cached in the browser beyond the session** (`data-protection.md`) — and nothing sensitive in client-side logs/telemetry.

---

## QA, testing & checklist
- **Automated header/CSP check** in CI: assert the deployed app returns the expected CSP, HSTS, `nosniff`, and CORS-allowlist headers (a header regression is silent otherwise).
- **XSS regression corpus**: render a report containing classic payloads (`<img onerror>`, `javascript:` links, `<script>`) and assert the sanitizer strips them (ties to the `secure-data-processing.md` injection corpus).
- **Dependency audit** (`npm audit`/`audit signatures`, SRI present) as a gate (`github-actions.md`).
- Pre-merge checklist:
  - [ ] No token in `localStorage`/`sessionStorage`; cookie auth has `SameSite` + CSRF, or token-in-header in memory.
  - [ ] Strict CSP shipped (no `unsafe-inline`/`unsafe-eval`); off-origin scripts vendored or SRI-pinned.
  - [ ] Rendered model/markdown output sanitized; no unreviewed `{@html}`/`dangerouslySetInnerHTML`.
  - [ ] Security headers present and CI-asserted; CORS is an allowlist.
  - [ ] No secrets/PII in the bundle or client storage; authz is server-enforced.

### Cross-references
- Server-side headers, CORS, generic auth errors, the auth `Depends()` pipeline — `references/python-web-apis.md`.
- The API attack surface and STRIDE trust boundaries (client→API) — `references/threat-modeling-and-api-design.md`.
- Model output / document content is untrusted; the injection corpus — `references/secure-data-processing.md` §2.
- Frontend dependency pinning + supply-chain — `references/package-managers.md`; CI header/audit gates — `references/github-actions.md`.
- No client-side PII; data-handling — `references/data-protection.md`. OWASP mapping — `references/compliance.md`. Responsive-design layout standard — `SKILL.md`.
