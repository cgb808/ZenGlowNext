"""Schema Drift Check

Purpose:
  Lightweight comparison of two Postgres database schemas (public schema) to detect
  drift between a *reference* (e.g. Supabase / cloud) and a *local* dev instance.

Environment Variables (pick one pair):
  1. DATABASE_URL (local) + SUPABASE_DB_URL (remote)
  2. PRIMARY_DATABASE_URL + SECONDARY_DATABASE_URL (override explicit pair)

Output:
  - Lists tables only in A or B
  - Lists columns added / removed / changed type per table
  - Exit code 0 always (non-fatal) unless --fatal-on-drift flag set

Usage (examples):
  python scripts/schema_drift_check.py
  python scripts/schema_drift_check.py --fatal-on-drift
  DATABASE_URL=postgresql://... SUPABASE_DB_URL=postgresql://... python scripts/schema_drift_check.py

Notes:
  - Requires psycopg2 (already present if pg access used elsewhere) or psycopg2-binary.
  - Does not compare indexes / constraints (extend easily, see TODO section).
  - Safe to run in CI to produce advisory log.
"""
from __future__ import annotations

import os
import sys
import argparse
import json
from dataclasses import dataclass
from typing import Dict, Tuple, List, Any

try:  # type: ignore
    import psycopg2  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"[schema-drift] psycopg2 not available: {e}", file=sys.stderr)
    sys.exit(2)


@dataclass
class ColumnDef:
    table: str
    name: str
    data_type: str
    is_nullable: str
    default: str | None

    def sig(self) -> Tuple[str, str, str]:  # signature for change detection
        return (self.data_type, self.is_nullable, self.default or "<none>")


def load_columns(dsn: str) -> Dict[str, Dict[str, ColumnDef]]:
    out: Dict[str, Dict[str, ColumnDef]] = {}
    q = """
    SELECT table_name, column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema='public'
    ORDER BY table_name, ordinal_position;
    """
    with psycopg2.connect(dsn) as conn:  # type: ignore[arg-type]
        with conn.cursor() as cur:
            cur.execute(q)
            for table, col, dt, nullable, default in cur.fetchall():  # type: ignore
                out.setdefault(table, {})[col] = ColumnDef(table, col, dt, nullable, default)
    return out


def compare_structured(a: Dict[str, Dict[str, ColumnDef]], b: Dict[str, Dict[str, ColumnDef]]) -> Dict[str, Any]:
    """Return structured diff including per-column attribute changes."""
    result: Dict[str, Any] = {
        "tables_only_in_a": [],
        "tables_only_in_b": [],
        "tables": {},  # table -> {removed, added, changed: [{column, primary, secondary}]}
    }
    set_a = set(a.keys())
    set_b = set(b.keys())
    for t in sorted(set_a - set_b):
        result["tables_only_in_a"].append(t)
    for t in sorted(set_b - set_a):
        result["tables_only_in_b"].append(t)
    for t in sorted(set_a & set_b):
        cols_a = a[t]
        cols_b = b[t]
        ca = set(cols_a.keys())
        cb = set(cols_b.keys())
        removed = sorted(ca - cb)
        added = sorted(cb - ca)
        changed: List[Dict[str, Any]] = []
        for c in sorted(ca & cb):
            if cols_a[c].sig() != cols_b[c].sig():
                changed.append(
                    {
                        "column": c,
                        "primary": {
                            "data_type": cols_a[c].data_type,
                            "nullable": cols_a[c].is_nullable,
                            "default": cols_a[c].default,
                        },
                        "secondary": {
                            "data_type": cols_b[c].data_type,
                            "nullable": cols_b[c].is_nullable,
                            "default": cols_b[c].default,
                        },
                    }
                )
        if removed or added or changed:
            result["tables"][t] = {"removed": removed, "added": added, "changed": changed}
    return result


def compare(a: Dict[str, Dict[str, ColumnDef]], b: Dict[str, Dict[str, ColumnDef]]) -> Dict[str, List[str]]:
    structured = compare_structured(a, b)
    diff: Dict[str, List[str]] = {"tables_only_in_a": structured["tables_only_in_a"], "tables_only_in_b": structured["tables_only_in_b"], "column_drift": []}
    for t, info in structured["tables"].items():
        parts = []
        if info["removed"]:
            parts.append(f"-removed:{info['removed']}")
        if info["added"]:
            parts.append(f"+added:{info['added']}")
        if info["changed"]:
            parts.append("±changed:" + str([c["column"] for c in info["changed"]]))
        diff["column_drift"].append(f"{t}: {' '.join(parts)}")
    diff["_structured"] = structured  # attach for callers needing details
    return diff


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two Postgres schemas (public)")
    parser.add_argument("--fatal-on-drift", action="store_true", help="Exit 1 if any drift detected")
    parser.add_argument(
        "--emit-sanitized",
        metavar="PATH",
        help="Also write a sanitized schema+edge-functions snapshot JSON for PRIMARY DB to PATH (excludes PII)",
    )
    parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write machine-readable JSON diff to PATH (or use '-' for stdout)",
    )
    args = parser.parse_args()

    # DSN resolution order
    primary = os.getenv("PRIMARY_DATABASE_URL") or os.getenv("DATABASE_URL")
    secondary = os.getenv("SECONDARY_DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not primary or not secondary:
        print("[schema-drift] Both primary & secondary DSNs required (see README in script header)", file=sys.stderr)
        return 2
    print(f"[schema-drift] Primary:   {primary}")
    print(f"[schema-drift] Secondary: {secondary}")
    try:
        a = load_columns(primary)
        b = load_columns(secondary)
    except Exception as e:  # pragma: no cover
        print(f"[schema-drift] ERROR: {e}", file=sys.stderr)
        return 2

    # Optional sanitized snapshot (PRIMARY only) for archival / review
    if args.emit_sanitized:
        try:
            from scripts.schema_export_sanitized import generate_sanitized_payload  # type: ignore

            payload = generate_sanitized_payload(primary, include_pii=False)
            with open(args.emit_sanitized, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            print(f"[schema-drift] Wrote sanitized snapshot -> {args.emit_sanitized}")
        except Exception as e:  # pragma: no cover
            print(f"[schema-drift] WARN: failed to emit sanitized snapshot: {e}", file=sys.stderr)
    diff = compare(a, b)
    structured = diff.pop("_structured")  # underlying structured data
    drift = False
    if diff["tables_only_in_a"]:
        drift = True
        print("\nTables only in PRIMARY:")
        for t in diff["tables_only_in_a"]:
            print(f"  {t}")
    if diff["tables_only_in_b"]:
        drift = True
        print("\nTables only in SECONDARY:")
        for t in diff["tables_only_in_b"]:
            print(f"  {t}")
    if diff["column_drift"]:
        drift = True
        print("\nColumn-level differences:")
        for line in diff["column_drift"]:
            print(f"  {line}")
    # JSON output (always provide even if no drift so downstream pipeline stable)
    if args.json_out:
        def mask(dsn: str) -> str:
            return dsn if "@" not in dsn else re_mask(dsn)

        def re_mask(dsn: str) -> str:
            # replace credentials between // and @
            import re as _re
            return _re.sub(r"//([^:@/]+)(:[^@/]+)?@", "//***:***@", dsn)

        json_payload = {
            "summary": {
                "drift": drift,
                "tables_only_in_primary": len(structured["tables_only_in_a"]),
                "tables_only_in_secondary": len(structured["tables_only_in_b"]),
                "tables_with_column_drift": len(structured["tables"]),
            },
            "primary_dsn_masked": mask(primary),
            "secondary_dsn_masked": mask(secondary),
            "tables_only_in_primary": structured["tables_only_in_a"],
            "tables_only_in_secondary": structured["tables_only_in_b"],
            "column_drift": structured["tables"],
        }
        if args.emit_sanitized and os.path.exists(args.emit_sanitized):
            json_payload["sanitized_snapshot_path"] = args.emit_sanitized
        encoded = json.dumps(json_payload, indent=2)
        if args.json_out == "-":
            print("\n[json-drift]\n" + encoded)
        else:
            with open(args.json_out, "w", encoding="utf-8") as jf:
                jf.write(encoded + "\n")
            print(f"[schema-drift] Wrote JSON diff -> {args.json_out}")

    if not drift:
        print("\n[schema-drift] No drift detected (public schema).")
        return 0
    print("\n[schema-drift] Drift detected.")
    return 1 if args.fatal_on_drift else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

# TODO (extend if needed):
#  - Compare indexes: query pg_indexes
#  - Compare constraints: pg_constraint join
#  - Include migration version comparison table
#  - JSON / machine readable output (--json)