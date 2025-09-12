"""Session state manager for voice fragment accumulation.

Early-phase in-memory implementation. Future: optional Redis backend.

API:
    get_session(session_id) -> dict (creates if missing)
    append_fragment(session_id, fragment: str, is_final: bool) -> dict session snapshot

Session Structure:
{
  'session_id': str,
  'accum_text': str,           # sliding window text
  'fragments': list[str],      # recent fragments (bounded)
  'is_final': bool,            # last received fragment marked final
  'created_ts': float,
  'last_updated': float,
  'turns': int                 # count of finalized utterances
}

Config:
    MAX_CHARS (env VOICE_SESSION_MAX_CHARS, default 2000)
    MAX_FRAGMENTS (env VOICE_SESSION_MAX_FRAGMENTS, default 50)

Cleanup placeholder: expose sweep(expire_seconds) for future cron.
"""
from __future__ import annotations

import os
import time
import threading
from typing import Dict, List

_lock = threading.Lock()
_sessions: Dict[str, dict] = {}

MAX_CHARS = int(os.getenv("VOICE_SESSION_MAX_CHARS", "2000"))
MAX_FRAGMENTS = int(os.getenv("VOICE_SESSION_MAX_FRAGMENTS", "50"))


def get_session(session_id: str) -> dict:
    now = time.time()
    with _lock:
        sess = _sessions.get(session_id)
        if not sess:
            sess = {
                'session_id': session_id,
                'accum_text': '',
                'fragments': [],
                'is_final': False,
                'created_ts': now,
                'last_updated': now,
                'turns': 0,
            }
            _sessions[session_id] = sess
        return sess


def append_fragment(session_id: str, fragment: str, is_final: bool) -> dict:
    fragment = fragment or ''
    sess = get_session(session_id)
    with _lock:
        # Append fragment and update accum_text with sliding window trim
        if fragment:
            sess['fragments'].append(fragment)
            if len(sess['fragments']) > MAX_FRAGMENTS:
                sess['fragments'] = sess['fragments'][-MAX_FRAGMENTS:]
            sess['accum_text'] = (sess['accum_text'] + ' ' + fragment).strip()
            if len(sess['accum_text']) > MAX_CHARS:
                # Keep last MAX_CHARS (approx sliding window)
                sess['accum_text'] = sess['accum_text'][-MAX_CHARS:]
        if is_final:
            sess['is_final'] = True
            sess['turns'] += 1
        sess['last_updated'] = time.time()
        return dict(sess)  # shallow copy snapshot


def sweep(expire_seconds: int = 900) -> int:
    """Remove sessions idle longer than expire_seconds. Returns count removed."""
    cutoff = time.time() - expire_seconds
    removed: List[str] = []
    with _lock:
        for sid, sess in list(_sessions.items()):
            if sess['last_updated'] < cutoff:
                removed.append(sid)
                _sessions.pop(sid, None)
    return len(removed)

__all__ = [
    'get_session', 'append_fragment', 'sweep'
]
