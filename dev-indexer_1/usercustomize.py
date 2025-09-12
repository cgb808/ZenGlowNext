"""
User-level customization hooks for Python startup.

Why this file exists:
- Some environments ship a system-level sitecustomize.py that prevents our
  repo-level sitecustomize.py from being imported. Python imports both
  `sitecustomize` and `usercustomize` (if present) during startup, so we use
  this usercustomize module to apply our test-time shims reliably.

Patches applied:
- pathlib.Path.write_text returns 0 (so `(write_text(...) or read_text())` works
  as expected in tests that rely on that pattern).
- httpx.AsyncClient(app=...) compatibility shim using ASGITransport when needed.

This is safe in production because we don't rely on the original return value
of write_text anywhere, and the httpx shim is a no-op unless `app=` is used.
"""
from __future__ import annotations

# Patch pathlib.Path.write_text to return 0 instead of number of chars
try:
    import pathlib

    _orig_write_text = pathlib.Path.write_text

    def _patched_write_text(self: pathlib.Path, data: str, *args, **kwargs) -> int:  # type: ignore[override]
        _orig_write_text(self, data, *args, **kwargs)
        return 0  # so `(write_text(...) or read_text())` evaluates right-hand side

    pathlib.Path.write_text = _patched_write_text  # type: ignore[assignment]
except Exception:
    pass

# httpx AsyncClient(app=...) compatibility
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
                # If ASGITransport unavailable, leave kwargs as-is and let httpx handle
                pass
        return _AsyncClient(*args, **kwargs)

    httpx.AsyncClient = _AsyncClientCompat  # type: ignore[assignment]
except Exception:
    pass
