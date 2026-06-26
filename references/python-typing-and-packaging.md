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
