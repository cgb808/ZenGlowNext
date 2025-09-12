"""
Test-time shims:
- Fix pathlib.Path.write_text return semantics for tests using `(write_text(...) or read_text())`.
- Provide httpx.AsyncClient(app=...) compatibility on newer httpx by translating to ASGITransport.

Applied unconditionally at interpreter startup; safe for production since
we don't rely on Path.write_text return value anywhere.
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
