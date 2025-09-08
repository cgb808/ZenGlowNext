"""Postgres persistence implementation for Family context.

Activated externally (e.g., via sync script) — API still uses in-memory store
until wiring logic adds dependency injection. Provides initial durability layer.
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

try:  # optional dependency
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore


class PgFamilyRepo:
    def __init__(self, dsn: str) -> None:
        if not psycopg2:  # pragma: no cover
            raise RuntimeError("psycopg2 not installed")
        self.dsn = dsn

    def _conn(self):  # context manager usage expected
        return psycopg2.connect(self.dsn)  # type: ignore[arg-type]

    def _conn_with_user(self, app_user: str):
        """Return connection with session variable set for RLS evaluation.

        Uses a transaction-scoped SET LOCAL so policies referencing
        current_setting('app.current_user', true) can enforce per-request
        filtering / masking. Caller should perform all statements within
        same connection context.
        """
        conn = psycopg2.connect(self.dsn)  # type: ignore[arg-type]
        with conn.cursor() as cur:
            try:
                cur.execute("SET LOCAL app.current_user = %s", (app_user,))
            except Exception:
                # Fail soft (RLS policies that rely on variable will treat as null)
                pass
        return conn

    # People -----------------------------------------------------------
    def upsert_person(self, p: Dict[str, Any], app_user: Optional[str] = None) -> None:
        sql = """
            INSERT INTO family_people (id,name,age,grade_band,last_name,birthdate,household_id,meta)
            VALUES (%(id)s,%(name)s,%(age)s,%(grade_band)s,%(last_name)s,%(birthdate)s,%(household_id)s, %(meta)s::jsonb)
            ON CONFLICT (id) DO UPDATE SET
                name=EXCLUDED.name,
                age=EXCLUDED.age,
                grade_band=EXCLUDED.grade_band,
                last_name=EXCLUDED.last_name,
                birthdate=EXCLUDED.birthdate,
                household_id=EXCLUDED.household_id,
                meta=EXCLUDED.meta,
                updated_ts=now();
        """
        record = {**p, "meta": json.dumps(p.get("meta", {}))}
        conn_ctx = self._conn_with_user(app_user) if app_user else self._conn()
        with conn_ctx as c, c.cursor() as cur:
            cur.execute(sql, record)

    def list_people(self, app_user: Optional[str] = None) -> List[Dict[str, Any]]:
        conn_ctx = self._conn_with_user(app_user) if app_user else self._conn()
        with conn_ctx as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:  # type: ignore
            cur.execute("SELECT * FROM family_people ORDER BY id")
            return list(cur.fetchall())

    # Relationships ----------------------------------------------------
    def add_guardian(self, guardian_id: str, child_id: str, legal: bool = True, app_user: Optional[str] = None) -> None:
        sql = """
            INSERT INTO family_relationships (guardian_id, child_id, kind, legal)
            VALUES (%s,%s,'guardian',%s) ON CONFLICT DO NOTHING;
        """
    conn_ctx = self._conn_with_user(app_user) if app_user else self._conn()
    with conn_ctx as c, c.cursor() as cur:
            cur.execute(sql, (guardian_id, child_id, legal))

    # Artifacts --------------------------------------------------------
    def add_artifact(self, art: Dict[str, Any], app_user: Optional[str] = None) -> None:
        sql = """
            INSERT INTO family_artifacts (id, entity_id, kind, title, tags, content_ref, meta, created_ts)
            VALUES (%(id)s,%(entity_id)s,%(kind)s,%(title)s,%(tags)s,%(content_ref)s,%(meta)s::jsonb, to_timestamp(%(created_ts)s/1000.0))
            ON CONFLICT (id) DO NOTHING;
        """
        rec = {**art, "tags": art.get("tags", []), "meta": json.dumps(art.get("meta", {}))}
        conn_ctx = self._conn_with_user(app_user) if app_user else self._conn()
        with conn_ctx as c, c.cursor() as cur:
            cur.execute(sql, rec)

    def list_artifacts(self, limit: int = 100, app_user: Optional[str] = None) -> List[Dict[str, Any]]:
        conn_ctx = self._conn_with_user(app_user) if app_user else self._conn()
        with conn_ctx as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:  # type: ignore
            cur.execute("SELECT * FROM family_artifacts ORDER BY created_ts DESC LIMIT %s", (limit,))
            return list(cur.fetchall())

    # Health metrics ---------------------------------------------------
    def add_health_metric(self, entity_id: str, metric: str, value: Any, unit: Optional[str], app_user: Optional[str] = None) -> None:
        if isinstance(value, (int, float)):
            vnum, vtext = float(value), None
        else:
            vnum, vtext = None, str(value)
        sql = """
            INSERT INTO family_health_metrics (entity_id, metric, value_text, value_num, unit)
            VALUES (%s,%s,%s,%s,%s);
        """
        conn_ctx = self._conn_with_user(app_user) if app_user else self._conn()
        with conn_ctx as c, c.cursor() as cur:
            cur.execute(sql, (entity_id, metric, vtext, vnum, unit))

    def latest_health_metric(self, entity_id: str, metric: str, app_user: Optional[str] = None) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT * FROM family_health_metrics
            WHERE entity_id=%s AND metric=%s
            ORDER BY ts DESC LIMIT 1;
        """
    conn_ctx = self._conn_with_user(app_user) if app_user else self._conn()
    with conn_ctx as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:  # type: ignore
            cur.execute(sql, (entity_id, metric))
            row = cur.fetchone()
            return dict(row) if row else None


def ensure_schema(dsn: str, schema_path: str) -> None:
    if not psycopg2:  # pragma: no cover
        raise RuntimeError("psycopg2 not installed")
    sql = open(schema_path, 'r', encoding='utf-8').read()
    with psycopg2.connect(dsn) as conn:  # type: ignore[arg-type]
        with conn.cursor() as cur:
            cur.execute(sql)
