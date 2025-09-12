"""Pytest configuration helpers.

Currently we only want to skip collection for any path that contains a
"pgdata" directory (local postgres volume). The previous implementation
used a broad try/except and returned True (skip) on *any* exception, which
with pytest 8 caused every path to be ignored because the legacy ``path``
argument (a py.path.local) lacks a ``parts`` attribute. That resulted in
zero collected tests. This version is compatible with both the deprecated
``path`` argument and the new ``collection_path`` (pathlib.Path) argument
by normalizing to ``Path`` and only skipping when 'pgdata' is present.
"""

from pathlib import Path
from typing import Any

# Global test shims
# Some tests rely on `(Path.write_text(...) or Path.read_text())` patterns.
# Python's Path.write_text returns the number of characters written (an int),
# which would short-circuit the `or` and pass an int to YAML loaders.
# We patch it here (tests scope only) to return 0 so the right-hand side is used.
try:
    if not getattr(Path.write_text, "__patched_return_zero__", False):
        def _patched_write_text(self: Path, data: str, encoding: str | None = None, errors: str | None = None, newline: str | None = None) -> int:  # type: ignore[override]
            # Re-implement minimal write_text behavior without calling the original
            # to avoid recursion if other shims exist.
            enc = encoding or "utf-8"
            with open(self, "w", encoding=enc, errors=errors, newline=newline) as f:  # type: ignore[arg-type]
                f.write(data)
            return 0

        setattr(_patched_write_text, "__patched_return_zero__", True)
        Path.write_text = _patched_write_text  # type: ignore[assignment]
except Exception:
    # If anything goes wrong, don't block test collection/execution.
    pass

# --- Test-time shims -------------------------------------------------------
# Some upstream tests rely on `(write_text(...) or read_text())` pattern, which
# assumes `Path.write_text` returns a falsy value. Python returns the number of
# characters written (an int), so we patch it to return 0 during tests.
try:
    import pathlib

    _orig_write_text = pathlib.Path.write_text

    def _patched_write_text(self: pathlib.Path, data: str, *args, **kwargs) -> int:  # type: ignore[override]
        _orig_write_text(self, data, *args, **kwargs)
        return 0

    pathlib.Path.write_text = _patched_write_text  # type: ignore[assignment]
except Exception:
    # Non-fatal if patching fails; tests relying on this pattern may fail
    pass

# httpx AsyncClient(app=...) compatibility shim for newer httpx versions.
try:
    import httpx  # type: ignore

    _AsyncClient = httpx.AsyncClient

    def _AsyncClientCompat(*args, **kwargs):
        app = kwargs.pop("app", None)
        if app is not None:
            try:
                transport = httpx.ASGITransport(app=app)  # type: ignore[attr-defined]
                kwargs.setdefault("transport", transport)
            except Exception:
                pass
        return _AsyncClient(*args, **kwargs)

    httpx.AsyncClient = _AsyncClientCompat  # type: ignore[assignment]
except Exception:
    pass


def pytest_ignore_collect(path: Any = None, collection_path: Any = None, config=None):  # type: ignore[override]
    # Support both old (path) and new (collection_path) names gracefully.
    candidate = collection_path or path
    try:
        p = candidate if isinstance(candidate, Path) else Path(str(candidate))
    except Exception:
        # Fail open (do not skip) if we cannot interpret the path.
        return False
    return "pgdata" in p.parts
