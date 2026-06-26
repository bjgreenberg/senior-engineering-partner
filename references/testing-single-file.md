# Testing strategy for single-file scripts with module-level side effects

Companion reference for the senior-engineering-partner skill (AUTOMATED QA & TESTING).


When a Python script has a `sys.exit()` or other side effect at module level (e.g., a fast-path help block that exits if no flags are present), it cannot be imported directly by pytest. Use this pattern:

**`tests/conftest.py`:**
```python
import sys
import importlib.util
from pathlib import Path

# Patch sys.argv BEFORE importing so any module-level sys.exit is bypassed.
_original_argv = sys.argv[:]
sys.argv = ["script.py", "--flag", "/tmp/sentinel"]  # use a real flag the script accepts

_SCRIPT_PATH = Path(__file__).parent.parent / "script.py"
_spec = importlib.util.spec_from_file_location("module_name", _SCRIPT_PATH)
module = importlib.util.module_from_spec(_spec)
sys.modules["module_name"] = module
_spec.loader.exec_module(module)

sys.argv = _original_argv  # restore after import so tests see clean argv
```

**Test files then import normally:**
```python
import module_name  # resolved from sys.modules set by conftest
```

## What is testable without I/O in a single-file script
- All pure-logic helpers (string manipulation, regex, datetime parsing, etc.)
- All regex patterns — even locally-scoped ones can be replicated in the test file
- Whitelist/filter functions
- Format/render functions that accept in-memory data

## What requires fixtures or mocks
- Extractor functions (file I/O) → use `tmp_path` pytest fixture with minimal synthetic files
- Enrichment functions (network I/O) → mock with `unittest.mock.patch` or `responses` library
- `main()` → integration test territory; defer until package modularization

