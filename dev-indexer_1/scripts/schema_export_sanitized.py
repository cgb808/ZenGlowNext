"""Sanitized Schema Export

Exports tables, non-PII columns, RLS policies, and PostgreSQL functions while
redacting or excluding objects tagged as PII / sensitive.

Tagging Strategy (initial lightweight):
  - Column or table comments containing token markers (case-insensitive):
        [PII], [SENSITIVE], [RESTRICTED]
    classify columns as sensitive. Additional free-form tags allowed inside
    square brackets e.g. [PII][GDPR][EMAIL].
  - Table-level comment with [PII] applies to all columns unless a column
    comment explicitly omits PII markers.

Function Redaction:
  - If function body (pg_get_functiondef) contains the name of any PII column
    (simple substring match) it is replaced with a placeholder unless
    --include-pii provided.

RLS Policies:
  - Always exported (policy text does not expose data values). If a policy
    references a redacted column name, it remains; downstream reviewers can
    still audit logic.

Output: JSON to stdout or --out file. Structure:
{
  "generated_at": iso8601,
  "db": {"primary": dsn_masked_host},
  "tables": { "table_name": {"columns": [...], "rls_policies": [...], "table_tags": [...] } },
  "functions": [ { name, args, returns, definition|redacted, redacted: bool } ],
  "summary": {"tables": N, "columns": M, "pii_columns_skipped": K}
}

Env / Args:
  DATABASE_URL or SUPABASE_DB_URL (DSN)
  --include-pii : do not redact or exclude PII (full export)
  --out path.json : write file
  --fatal-on-error : non-zero exit on error (default soft)

Limitations / TODO:
  - No index / constraint export yet.
  - PII detection via comments only; add classification table later if needed.
  - Function body reference detection is naive substring (improve via parse).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Set, Iterable

try:  # type: ignore
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"[schema-export] psycopg2 not installed: {e}", file=sys.stderr)
    sys.exit(2)

PII_MARKERS = {"pii", "sensitive", "restricted"}
TAG_PATTERN = re.compile(r"\[([^\]]+)\]")
ENV_VAR_PATTERN = re.compile(r"Deno\.env\.get\(['\"]([A-Z0-9_]+)['\"]\)")


def extract_tags(comment: str | None) -> List[str]:
    if not comment:
        return []
    return [t.strip() for t in TAG_PATTERN.findall(comment)]


def has_pii(tags: List[str]) -> bool:
    return any(t.lower() in PII_MARKERS for t in tags)


def mask_dsn(dsn: str | None) -> str | None:
    if not dsn:
        return None
    # crude: remove credentials portion user:pass@
    return re.sub(r"//([^:@/]+)(:[^@/]+)?@", "//***:***@", dsn)


def load_schema(conn, include_pii: bool) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # Table & column comments
    cur.execute(
        """
        SELECT c.relname AS table_name,
               obj_description(c.oid) AS table_comment,
               a.attname AS column_name,
               col_description(c.oid, a.attnum) AS column_comment,
               pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
               NOT a.attnotnull AS is_nullable,
               pg_get_expr(ad.adbin, ad.adrelid) AS column_default
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname='public'
        JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
        LEFT JOIN pg_attrdef ad ON ad.adrelid = c.oid AND ad.adnum = a.attnum
        WHERE c.relkind='r'
        ORDER BY c.relname, a.attnum;
        """
    )
    rows = cur.fetchall() or []
    tables: Dict[str, Any] = {}
    table_tags_cache: Dict[str, List[str]] = {}
    pii_columns: Set[str] = set()
    for r in rows:
        t = r["table_name"]
        tbl = tables.setdefault(t, {"columns": [], "rls_policies": [], "table_tags": []})
        if not tbl["table_tags"]:
            ttags = extract_tags(r["table_comment"])
            tbl["table_tags"] = ttags
            table_tags_cache[t] = ttags
        col_tags = extract_tags(r["column_comment"])
        # Inherit table PII if table comment has marker and column lacks explicit tags.
        effective_tags = col_tags or table_tags_cache[t]
        col_is_pii = has_pii(effective_tags)
        if col_is_pii and not include_pii:
            pii_columns.add(f"{t}.{r['column_name']}")
            continue
        tbl["columns"].append(
            {
                "name": r["column_name"],
                "data_type": r["data_type"],
                "nullable": r["is_nullable"],
                "default": r["column_default"],
                "tags": effective_tags,
            }
        )

    # Policies
    cur.execute(
        """
        SELECT polname, schemaname, tablename, cmd, roles, qual, with_check, permissive
        FROM pg_policies
        WHERE schemaname='public'
        ORDER BY tablename, polname;
        """
    )
    for p in cur.fetchall() or []:
        t = p["tablename"]
        if t in tables:
            tables[t]["rls_policies"].append(
                {
                    "policy": p["polname"],
                    "command": p["cmd"],
                    "roles": p["roles"],
                    "qual": p["qual"],
                    "with_check": p["with_check"],
                    "permissive": p["permissive"],
                }
            )

    # Functions
    cur.execute(
        """
        SELECT p.oid,
               proname,
               pg_get_function_identity_arguments(p.oid) AS args,
               pg_get_functiondef(p.oid) AS definition,
               pg_catalog.format_type(p.prorettype, NULL) AS returns
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace AND n.nspname='public'
        WHERE p.prokind='f'
        ORDER BY proname;
        """
    )
    functions = []
    pii_column_names = {c.split(".")[1] for c in pii_columns}
    for f in cur.fetchall() or []:
        body = f["definition"] or ""
        redacted = False
        if not include_pii and any(col in body for col in pii_column_names):
            body = "-- REDACTED (references PII columns)"  # minimal placeholder
            redacted = True
        functions.append(
            {
                "name": f["proname"],
                "args": f["args"],
                "returns": f["returns"],
                "definition": body,
                "redacted": redacted,
            }
        )

    return {
        "tables": tables,
        "functions": functions,
        "pii_columns_skipped": len(pii_columns),
    }


def collect_edge_functions(root: str | Path) -> List[Dict[str, Any]]:
    root_path = Path(root)
    if not root_path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for child in sorted(p for p in root_path.iterdir() if p.is_dir()):
        # simple heuristic: look for index.(ts|js)
        entry: Path | None = None
        for candidate in (child / "index.ts", child / "index.js"):
            if candidate.exists():
                entry = candidate
                break
        if not entry:
            continue
        try:
            text = entry.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        # Extract leading comment block lines starting with // until blank line
        header_lines: List[str] = []
        for line in text.splitlines()[:25]:  # only scan first 25
            ls = line.strip()
            if ls.startswith("//"):
                header_lines.append(ls[2:].strip())
            elif header_lines and not ls:
                break
            elif header_lines and not ls.startswith("//"):
                break
        env_vars = sorted(set(ENV_VAR_PATTERN.findall(text)))
        out.append(
            {
                "name": child.name,
                "entry": str(entry.relative_to(root_path.parent)),
                "sha256_16": sha,
                "header": header_lines[:6],  # cap
                "env_vars": env_vars,
                "lines": len(text.splitlines()),
            }
        )
    return out


def generate_sanitized_payload(
    dsn: str,
    include_pii: bool = False,
    edge_functions_dir: str | Path = "supabase/functions",
) -> Dict[str, Any]:
    """Generate sanitized schema + edge function metadata for a single database DSN."""
    import psycopg2  # local import to keep top-level import minimal for callers

    with psycopg2.connect(dsn) as conn:  # type: ignore[arg-type]
        schema_data = load_schema(conn, include_pii=include_pii)
    edge_funcs = collect_edge_functions(edge_functions_dir)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": {"primary": mask_dsn(dsn)},
        **schema_data,
        "edge_functions": edge_funcs,
        "summary": {
            "tables": len(schema_data["tables"]),
            "columns": sum(len(t["columns"]) for t in schema_data["tables"].values()),
            "pii_columns_skipped": schema_data["pii_columns_skipped"],
            "edge_functions": len(edge_funcs),
        },
    }
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Export sanitized schema metadata")
    ap.add_argument("--include-pii", action="store_true", help="Include PII-tagged columns and full function bodies")
    ap.add_argument("--out", help="Write JSON to file instead of stdout")
    ap.add_argument("--fatal-on-error", action="store_true")
    ap.add_argument(
        "--edge-functions-dir",
        default="supabase/functions",
        help="Directory containing Supabase Edge Functions (default supabase/functions)",
    )
    args = ap.parse_args()

    dsn = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or os.getenv("SUPABASE_DIRECT_URL")
    if not dsn:
        print("[schema-export] No DATABASE_URL / SUPABASE_DB_URL set", file=sys.stderr)
        return 2
    try:
        payload = generate_sanitized_payload(
            dsn,
            include_pii=args.include_pii,
            edge_functions_dir=args.edge_functions_dir,
        )
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            print(f"[schema-export] Wrote {args.out}")
        else:
            print(json.dumps(payload, indent=2))
        return 0
    except Exception as e:  # pragma: no cover
        print(f"[schema-export] ERROR: {e}", file=sys.stderr)
        return 1 if args.fatal_on_error else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
