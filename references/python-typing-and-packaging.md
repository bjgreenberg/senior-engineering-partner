# Python Typing & Single-File→Package Layout

Companion reference for the senior-engineering-partner skill. The **rules** live in SKILL.md (*Type Annotations and TypedDicts*, *Single-File vs. Package Architecture*); this file holds the worked examples and the target layout, kept out of the always-loaded core for token economy. Read it when adding TypedDicts or planning a single-file→package migration.

---

## TypedDict — the pattern

Every Python function has complete type annotations. For functions that return dictionaries, use `TypedDict` instead of `dict[str, Any]` — `dict[str, Any]` is a type black hole that defeats IDE autocompletion and static analysis.

**Rules:**
- Define all TypedDicts near the top of the file (before functions) or in a dedicated `types.py` module.
- Use `total=False` when most fields are optional (callers should guard with `.get()`). Use `total=True` (the default) when all fields are always present.
- TypedDicts are `dict` subtypes — adding them to existing code is always safe and never changes runtime behavior.
- For functions with complex nested returns, define sub-TypedDicts (e.g. `PdfMetadata`, `EmlAuthInfo`) rather than nesting `dict[str, Any]`.
- Define a `Union` alias (e.g. `AnyArtifact`) when multiple TypedDict types appear in the same list.

**Example pattern:**
```python
from typing import TypedDict

class PdfMetadata(TypedDict, total=False):
    author: str
    creator: str
    creation_date: str
    modification_date: str

class PdfArtifact(TypedDict, total=False):
    file: str
    type: str  # always "pdf"
    metadata: PdfMetadata
    pages: list[dict[str, Any]]
    errors: list[str]

def extract_pdf(path: Path) -> PdfArtifact:
    ...
```

---

## The type-check gate covers the whole tree — never a hand-kept file list

The rule is in SKILL.md (*Type Annotations and TypedDicts*): every gate — `mypy`, `ruff`, `bandit`, the test runner — is pointed at the repo root or the package, with exclusions, never at named files. A legacy ratchet scopes a rung to the diff *computed* against the merge base (`testing.md`, the gate-promotion ladder), with the whole-tree run as its scheduled sweep; a list someone typed is never the scope. The origin: a `typecheck.sh` that ran `mypy --strict` on one named module reported `Success: no issues found in 1 source file` and CI stayed green for months. The modules that file imported were checked (mypy follows imports); the tests, the helper scripts and every module it did not import were not, and the count only ever counted the named file. The rule missed it because the paragraph said "over the package", endorsed gating the touched modules, and said nothing about tests, scripts or the count.

**Configuration (`pyproject.toml`), the shape that satisfies the rule** (verified with mypy 2.4, ruff 0.17, bandit 1.9):

```toml
[tool.mypy]
files = ["."]                         # the root; not a directory list, which is the hand-kept list one level up
strict = true                         # source runs strict
exclude = ["^build/", "^\\.venv/"]    # exclusions are explicit and few
explicit_package_bases = true         # tests/test_a.py is tests.test_a even without tests/__init__.py
mypy_path = ["src"]

[[ tool.mypy.overrides ]]             # whitespace around the key is valid TOML
module = "tests.*"
disallow_untyped_defs = false         # relax ONLY what a test fixture needs; everything else stays strict

[tool.bandit]
exclude_dirs = [".venv", "build"]     # read only when bandit is run with -c pyproject.toml
[tool.bandit.assert_used]
skips = ["*/tests/*"]                 # B101: assert is the test idiom; the narrow skip, not an excluded tests/

[tool.pytest.ini_options]
testpaths = ["tests"]                 # discovery, not a list of test modules
```

- **Source is strict; tests and scripts are checked, not omitted.** Tests and `scripts/` run under the same `files`, with a per-module override that relaxes only the setting a justified case needs (`disallow_untyped_defs` for test functions, say). An override that turns off `strict` wholesale, or an `exclude` that drops `tests/` or `scripts/`, is the hand-kept list by another name. The override matches the module name mypy computes, not the path: without `explicit_package_bases`, `tests/test_a.py` is `tests.test_a` only when `tests/__init__.py` exists — otherwise the module is `test_a`, `module = "tests.*"` matches nothing, and strict applies in full (verified: the test file fails `no-untyped-def` until either the `__init__.py` or `explicit_package_bases` is added).
- **The gate script passes no paths but the root.** `scripts/check.sh` is `mypy` (config supplies the tree), `ruff check . && ruff format --check .` (ruff's defaults already exclude `.venv/` and `build/`), `bandit -r -c pyproject.toml .` (without `-c`, bandit ignores `[tool.bandit]` and scans `.venv/`), `pytest`. CI runs the same script with the same flags — a `-ll` in CI and none locally is two different gates. A file argument on any of these lines is a finding in review.
- **Verify the gate by its reported count, not its exit code.** `mypy` prints the count on both outcomes — `Success: no issues found in N source files` and `Found 1 error in 1 file (checked N source files)`; compare N with `git ls-files '*.py' | wc -l` (minus the excluded dirs) and explain any gap. The same check for the others: `ruff check --show-files .` lists what ruff saw, `bandit -v` prints `Files in scope (N)` and `Files excluded (N)`, `pytest --collect-only -q` lists what was collected. A green exit over one file is the failure this section exists to catch — the check with no input passes.
- **Ratchet by computed scope or by override, not by list.** For a large untyped legacy module, keep the whole tree in `files` and put the module under a per-module override that disables the specific error codes it fails (`disable_error_code = ["no-untyped-def", ...]`), with a dated comment and an owner; widen by deleting overrides, never by adding paths. Never `ignore_errors = true`: an ignored module still counts toward `N source files` while nothing in it is checked, so the count check reads green over a hole. The legacy carve-out is visible in config and shrinks; a path list grows silently stale.

---

## Single-file → package: the target layout

Apply the *Single-File vs. Package Architecture* decision framework in SKILL.md first — most single-file scripts should **stay** single-file (portability, bootstrap logic, solo contributor, under ~5–6k lines). Convert only when a trigger fires (file > ~6k lines, I/O-bound functions need mocking, a second contributor, public distribution, CI/CD). Always do the intermediate steps first (TypedDicts → tests for pure-logic helpers → `requirements.txt` → `MODULARIZATION.md`).

When a full migration is warranted, this is the target layout:

```
package_name/
├── __init__.py         ← version, top-level exports
├── cli.py              ← argparse + main() only (thin)
├── config.py           ← module-level constants, env/path resolution
├── types.py            ← all TypedDicts
├── extractors/         ← file type extractors (one per type or family)
├── enrichment/         ← external data lookups (WHOIS, DNS, APIs)
├── analysis/           ← cross-artifact or cross-record detection logic
├── reporting/          ← report formatting, bundle assembly
└── output/             ← external outputs (Google Docs, Slack, etc.)

script.py               ← thin shim at repo root:
                           from package_name.cli import main
                           if __name__ == "__main__": main()
```

The thin shim preserves the existing `./script.py` invocation — users never notice the change. `MODULARIZATION.md` (written during the intermediate steps) is the implementation spec for this migration.
