# Docker & Kubernetes Standards

Companion reference for the senior-engineering-partner skill.


Before reaching for Kubernetes at all: **for almost every workload of this shape, Cloud Run is the correct target, not GKE.** An example app, its web frontend, and a Supabase-backed SaaS API are all single-container, stateless, scale-to-zero HTTP services. Cloud Run runs the *same* OCI image you'd push to a cluster, with no nodes to patch, no control-plane to secure, no `NetworkPolicy`/RBAC/Pod-Security surface to get wrong, and a far smaller attack surface. Reach for GKE only when you genuinely need multi-container pods, in-cluster service mesh, DaemonSets, or workloads Cloud Run's request model can't host (long-lived stateful processes, non-HTTP protocols). Default answer to "should this be on Kubernetes?" is **no — Cloud Run.** Everything in the Docker section below applies either way; everything in the Kubernetes section applies only once you've justified the cluster. Images for both live in **Google Artifact Registry**; pull secrets at runtime from **GCP Secret Manager** (build-time secrets from **1Password** via BuildKit mounts — see below).

---

## Docker

### Discipline / best practices

- **Pin the base image by digest, never `:latest` or even a floating tag.** `FROM python:3.13-slim` re-resolves to a different image every rebuild — builds stop being reproducible and a compromised upstream tag lands silently. Pin the digest so the bytes are frozen and the build is identical regardless of which machine or CI runner produced it:
  ```dockerfile
  FROM python:3.13-slim@sha256:<digest>
  ```
  Get the digest with `docker buildx imagetools inspect python:3.13-slim`. Bump it deliberately (Dependabot/Renovate can PR digest bumps), never implicitly.
- **Multi-stage build — build deps never ship.** Compile/install in a `builder` stage, copy only the artifact (the venv, the wheel, the binary) into a clean final stage. A `pip install`'s build toolchain, `.git`, and caches must not survive into the runtime image. Smaller image = smaller CVE surface for trivy to flag.
- **Run as a non-root `USER`.** A container with no `USER` line runs as root (UID 0); a container escape is then root on the node. Create an unprivileged user in the image and switch to it:
  ```dockerfile
  RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
  USER 10001
  ```
  Use the numeric UID in `USER` (not just the name) so Kubernetes `runAsNonRoot` can verify it — `runAsNonRoot` cannot prove a *named* user is non-zero (the name→UID mapping lives only inside the image's `/etc/passwd`) and the pod fails to start with `container has runAsNonRoot and image has non-numeric user, cannot verify user is non-root`.
- **Minimal / distroless base.** Prefer `gcr.io/distroless/python3` or `-slim` over a full `python` image. Distroless has no shell, no package manager, no `curl` — which also means no `RUN` after the `FROM` and nothing for an attacker to pivot through. Trade-off: you can't `docker exec ... sh` to debug; use the `:debug` distroless variant (it ships a busybox shell) locally only.
- **`.dockerignore` is mandatory and excludes secrets + cruft.** Without it, `COPY . .` bakes `.git/` (full history, including any secret ever committed), `.env`, `node_modules/`, and local junk into a layer — readable forever by anyone who pulls the image, even if a later layer deletes them. Minimum:
  ```
  .git
  .gitignore
  .env
  .env.*
  *.pem
  *.key
  node_modules
  __pycache__
  .venv
  .pytest_cache
  .DS_Store
  ```
- **NEVER bake secrets into a layer or a build arg.** `ARG API_KEY` + `--build-arg` is **not** secret — it's recorded in image metadata and visible via `docker history`. Same for `COPY .env`, `ENV TOKEN=...`, or a `RUN` that echoes a credential. Two correct paths:
  - **Build-time secret needed** (e.g. pulling a private package): BuildKit secret mount — never persisted in any layer:
    ```dockerfile
    # syntax=docker/dockerfile:1
    RUN --mount=type=secret,id=op_token \
        TOKEN="$(cat /run/secrets/op_token)" pip install ...
    ```
    feed it from 1Password at build time: `op read "op://vault/item/token" | docker buildx build --secret id=op_token,src=/dev/stdin .`
  - **Runtime secret** (the normal case): inject at container start from **GCP Secret Manager** — never in the image. On Cloud Run, mount the secret as an env var or file with `--set-secrets` (e.g. `--set-secrets=API_KEY=my-secret:latest`). This is the runtime mirror of the 1Password-at-build-time rule above.
- **`HEALTHCHECK` so orchestrators know "running" ≠ "healthy".** Without one a hung-but-not-crashed process keeps serving traffic. (Note: Cloud Run and Kubernetes ignore the Dockerfile `HEALTHCHECK` and use their own probes — keep the Dockerfile one for `docker run`/Compose and container-structure-test parity, but the authoritative liveness check on the cluster is the pod probe below.)
- **OCI provenance labels** so a pulled image is traceable back to a commit:
  ```dockerfile
  LABEL org.opencontainers.image.source="https://github.com/<org>/<repo>" \
        org.opencontainers.image.revision="<git-sha>" \
        org.opencontainers.image.licenses="UNLICENSED"
  ```
  Populate `revision` from the CI commit SHA. This is what lets you answer "which commit produced the image currently serving prod?" months later.
- **Harden at *runtime*, not just in the Dockerfile** — read-only root filesystem and dropped capabilities are a runtime flag (`docker run --read-only --cap-drop ALL`) or a Kubernetes `securityContext` (below). A read-only rootfs means a foothold can't drop a binary or rewrite your app; give it an explicit `tmpfs`/`emptyDir` for the few paths that must be writable.

### QA & quality gates (CI gates)

- **`hadolint Dockerfile` — lint every Dockerfile, zero warnings is the bar.** Catches unpinned `apt-get` (`DL3008`), missing `--no-install-recommends`, `ADD` where `COPY` belongs, root `USER`, shell-form `CMD` pitfalls. Treat it like ShellCheck (which it also runs on `RUN` lines): a clean run is the standard, and it fails the PR.
- **`dockle` for CIS Docker Benchmark + image hygiene** — flags `:latest`, missing `HEALTHCHECK`, credential files left in the image, world-writable files, running as root. Fail CI on `FATAL`.
- **`container-structure-test` for image *contract* tests** — assert the image actually contains what it must: the entrypoint exists, the non-root user is in effect, a required binary is present/absent, an expected env var is set. This is the unit test for the image itself; commit the YAML alongside the Dockerfile.
- **Smoke-run the built image in CI.** Building green proves nothing about *running*. After build, `docker run -d` the image, hit its health endpoint, assert HTTP 200, tear down. An image that builds but crashes on boot (missing runtime dep, bad entrypoint) must fail the pipeline, not production.
- **Build with BuildKit and a pinned `# syntax=docker/dockerfile:1` directive** for reproducible, cache-mountable, secret-mountable builds.

### Test cases (what to test and how)

- **Structure-test the security posture, not just functionality:** assert `USER` is non-root (`metadataTest.user` is the numeric UID, not `root`/`0`), the expected `LABEL`s exist, no `.env`/`.git`/`*.pem` paths exist in the filesystem, and no unexpected shell is present in a distroless image.
- **Test the container boots and serves** with the same `--read-only --cap-drop ALL --user 10001` flags CI/prod will use — a container that only works *with* write access or extra capabilities has a latent prod failure. Catch it in the smoke test, not after deploy.
- **Test the non-root user can actually write where it needs to** (logs, temp). The classic regression: add `USER 10001`, and the app that wrote to a root-owned path now throws `Permission denied` at runtime. Assert the writable path is owned by/writable for the runtime UID.
- **For the Python app inside the container**, the real logic tests are the pytest suite (see `testing-single-file.md`); the container tests cover only the packaging/runtime contract — keep them distinct so a logic failure and a packaging failure point at different files.
- **`docker compose run <svc>` can recreate a `depends_on` service — wiping out-of-band state, and only in CI.** A common ephemeral-gate shape is `compose up -d db` → bootstrap the db out of band (create a role, pre-create an extension, seed) → `compose run --rm migrator` (or `tests`). But `compose run` re-evaluates `depends_on` and may **recreate** the dependency container — observed on the GitHub-runner compose, **not** on local Docker Desktop/OrbStack, a textbook works-on-my-machine CI-only failure — discarding everything the bootstrap added, so the dependent step hits a fresh container (e.g. `password authentication failed` for a role that no longer exists). When you own the dependency's lifecycle (you brought it up and seeded it), pass **`--no-deps`** — `compose run --rm --no-deps <svc>` — so `run` touches only the one-off container, never the db you set up. A harness that connects as the **built-in env-provided superuser** is immune (that role survives a recreation), which is exactly why a pre-existing gate using it never surfaced the bug.

### Security testing (scanners + specific checks)

- **`trivy image <ref>` (or `grype`) scans the *built* image and FAILS CI on HIGH/CRITICAL.** This is the make-or-break gate — bandit and `npm audit` (already mandated in SKILL.md's Automated QA) cover *your* dependencies; trivy covers the entire image including OS packages in the base layer that you don't directly control. Standard gate:
  ```bash
  trivy image --severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed <image-ref>
  ```
  `--ignore-unfixed` keeps the build from blocking on CVEs with no upstream patch yet (track those, don't gate on them); drop it for a periodic full audit. Pin trivy's vulnerability-DB version in CI so a scan is reproducible.
- **`trivy` also catches baked secrets and misconfigs** — it has a secret scanner (flags an API key/private key that made it into a layer) and a config scanner for the Dockerfile itself. Run it; a leaked credential in a layer is a `git`-history-class disaster that ships to anyone with pull access.
- **`dockle` for the CIS/runtime-hardening checks** trivy's vuln scan doesn't cover (root user, missing `HEALTHCHECK`, sensitive files, suid binaries).
- **Scan on a schedule, not only on build.** An image that was clean at build time accrues CVEs as new ones are disclosed against its frozen base digest. A weekly trivy re-scan of what's *deployed* is the dead-man's-switch for "we shipped clean and rotted in place" — mirror the monitoring discipline in SKILL.md (alert on NEW criticals, summarize don't itemize, deliver durably).
- **Verify image provenance for anything deployed.** Prefer signed images (cosign / Sigstore) and, on GKE, Binary Authorization so only attested images from your Artifact Registry pipeline run. At minimum, deploy by **digest**, never by mutable tag — `image: ...@sha256:...` — so "what's running" can't drift from "what you scanned."
- **Generate and attach an SBOM for every built image** (the supply-chain *output* — SKILL.md *Supply-chain integrity*). Run **`syft`** (→ SPDX) or `trivy image --format cyclonedx` to produce a component/version/license manifest, attach it as an attestation (`actions/attest-sbom`, or `cosign attest`), and feed it to `osv-scanner`/`grype` so vuln scanning reads a manifest of record rather than re-deriving it. SBOM (*what's in it*) + provenance (*how it was built*) together are what a consumer verifies; pair this with the build-provenance attestation in `github-actions.md`.

---

## Kubernetes

Only once a cluster is actually justified (see the Cloud-Run-first note at top). All image rules above still apply.

### Discipline / best practices

- **Resource `requests` AND `limits` on every container.** No `requests` → the scheduler can't bin-pack and a noisy pod starves its neighbors; no memory `limit` → a leak consumes the node and triggers cascading evictions; no CPU handling and the pod gets throttled unpredictably. Set both for CPU and memory on every container, always.
- **`securityContext` locked down on every workload** — this is the cluster-side of the Docker hardening above, and it's non-negotiable:
  ```yaml
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop: ["ALL"]
    seccompProfile:
      type: RuntimeDefault
  ```
  `runAsNonRoot: true` is why the image needs a *numeric* `USER` (above). `readOnlyRootFilesystem: true` needs an explicit `emptyDir` volume for any writable path. `drop: ["ALL"]` then add back only the rare capability genuinely required.
- **Enforce the *restricted* Pod Security Standard at the namespace** so a non-compliant pod is rejected at admission, not discovered later:
  ```yaml
  metadata:
    labels:
      pod-security.kubernetes.io/enforce: restricted
      pod-security.kubernetes.io/enforce-version: latest
  ```
  Without this, the `securityContext` above is a convention an author can simply omit; with it, the API server refuses the pod.
- **Never `:latest` (or any mutable tag) for the image — pin by digest.** A `:latest` pod re-pulls a different image on every reschedule, so two replicas can silently run different code and a rollback is impossible. Use `image: <registry>/<repo>@sha256:<digest>`.
- **Readiness, liveness, AND startup probes — they are not interchangeable.** Liveness restarts a wedged container; readiness gates whether it receives traffic (a pod that's up but not warm must not get requests); startup protects a slow-booting app from being liveness-killed before it's ready. Omitting readiness is the classic cause of 503s during a rollout (traffic routed to a not-yet-ready pod).
- **Default-deny `NetworkPolicy` per namespace, then allow explicitly.** Kubernetes default is *all pods can talk to all pods* — flat, open east-west traffic. Apply a deny-all ingress/egress policy and then open only the required flows. Without this, a single compromised pod can reach everything in the cluster. (Note: `NetworkPolicy` is enforced only if the CNI supports it — GKE Dataplane V2 / Cilium does; confirm enforcement is actually on, or the policy is a no-op.)
- **RBAC least-privilege — never bind a workload to `cluster-admin`.** A pod's ServiceAccount should have a `Role` scoped to exactly the namespaced verbs/resources it needs (often: nothing). `cluster-admin` on a workload SA means a container compromise is a *cluster* compromise. This is the Principle of Least Privilege from SKILL.md applied to RBAC — same rule, same stakes.
- **Secrets via External Secrets Operator or the Secret Manager CSI driver — NOT plaintext base64 `Secret`s.** A native Kubernetes `Secret` is base64 (encoding, not encryption), stored in etcd, and trivially readable by anyone with `get secret` RBAC. Pull from **GCP Secret Manager** at runtime via ESO or the CSI driver so the credential never lives in a manifest, in Git, or in etcd in recoverable form. This mirrors the Docker runtime-injection rule and the 1Password/Secret-Manager discipline above.
- **Namespace isolation** as the unit of tenancy/blast-radius — separate namespaces per app/environment, each with its own PSS label, default-deny `NetworkPolicy`, RBAC, and resource quota. For the multi-tenant SaaS, namespace isolation is *infrastructure* segmentation; tenant-row isolation is still Supabase **RLS** at the data layer — they are complementary, not substitutes.

### QA & quality gates (CI gates)

- **`kubeconform` (successor to the unmaintained `kubeval`) for schema validation** — catches a typoed field, wrong `apiVersion`, or malformed manifest before it ever reaches the cluster. Fast, offline, runs on every manifest in the PR.
- **`kube-score` and/or `polaris` for best-practice scoring** — flags missing `requests`/`limits`, missing probes, missing `securityContext`, running as root, mutable image tags. Set a score threshold that fails the PR.
- **`kubesec` for security scoring** of a manifest — assigns a risk score and points at the specific `securityContext`/capability/host-namespace weaknesses to fix.
- **`trivy` scans manifests (misconfig) AND images** — one tool for "is this YAML insecure?" (`trivy config`) and "is this image vulnerable?" (`trivy image`). Gate both.
- **`kubectl apply --dry-run=server` before any real apply** — `--dry-run=client` only checks local schema; `--dry-run=server` runs it through admission controllers (including the PSS enforcement above) so you find out the pod is rejected *before* you change cluster state, not after.
- **GitOps (Argo CD or Flux) over hand-run `kubectl apply` to prod.** A `kubectl apply` from a laptop is an unrecorded, unreviewed, unrepeatable mutation of production — the cluster-equivalent of editing a rendered config *target* instead of its *source*. The Git repo is the single source of truth; the controller reconciles the cluster to it; every change is a reviewed, CI-gated, signed PR (same PR-flow + branch-protection standard as every other `<org>/*` repo in SKILL.md). Drift is detected and reverted automatically.

### Test cases (what to test and how)

- **Assert every container has `requests` + `limits` and all three probes** — fail the manifest test if any is absent; these are the omissions that cause prod incidents, not edge cases.
- **Assert the `securityContext` block is present and correct** on every pod spec: `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]`, `seccompProfile.type: RuntimeDefault`. A policy-as-code test (Conftest/OPA Rego, or `kube-score` with a threshold) makes this a hard gate rather than a review-by-eyeball.
- **Test that the namespace carries the `restricted` PSS label and a default-deny `NetworkPolicy`** — these are easy to forget on a *new* namespace, which is exactly when the gap is widest.
- **`--dry-run=server` against a real (or kind/minikube) cluster in CI** as the integration test — proves admission controllers accept the manifest, which pure schema validation can't.
- **Negative tests for RBAC**: assert the workload's ServiceAccount *cannot* do what it shouldn't (`kubectl auth can-i --as=system:serviceaccount:<ns>:<sa> get secrets -n <ns>` → must be `no`). Testing only the allow path lets an over-broad `Role` pass unnoticed.

### Security testing (scanners + specific checks)

- **`trivy config` / `trivy k8s` for manifest misconfiguration** — the cluster analog of the image scan: privileged pods, host-namespace sharing (`hostPID`/`hostNetwork`/`hostPath`), missing `securityContext`, `automountServiceAccountToken` left on where unused.
- **`kubesec` + `polaris` for the security/best-practice score**, gated to a minimum.
- **Specific high-severity checks to fail on, every time:** any container running as root or `runAsNonRoot: false`; `privileged: true`; `allowPrivilegeEscalation: true`; `hostNetwork`/`hostPID`/`hostIPC: true`; `hostPath` volume mounts; mutable image tag instead of digest; a plaintext `Secret` (these belong in Secret Manager via ESO/CSI); any ServiceAccount bound to `cluster-admin`; a namespace with no default-deny `NetworkPolicy`.
- **Scan running cluster state, not just manifests** — `trivy k8s` (or kube-bench for the CIS Kubernetes Benchmark on the nodes) finds drift and node-level misconfig that manifest scanning can't see. On GKE, lean on GKE's built-in security posture / workload-vulnerability scanning rather than self-hosting that whole stack.
- **Provenance/admission**: prefer GKE Binary Authorization so only signed, attested images from your Artifact Registry pipeline can be admitted — closes the gap between "we scanned a clean image in CI" and "only that image can run."

> Note on tool specifics: scanner CLIs (trivy, hadolint, dockle, kube-score, kubeconform, kubesec, polaris) and managed offerings (GKE security posture, Binary Authorization, Artifact Registry scanning) move quickly. The *gates and the failure conditions* above are durable; **verify exact flags, severity names, current subcommands, and the precise Cloud Run `--set-secrets` / Secret Manager / Artifact Registry wiring against each tool's and GCP's current docs** before wiring a new pipeline — don't assume a flag from memory.
