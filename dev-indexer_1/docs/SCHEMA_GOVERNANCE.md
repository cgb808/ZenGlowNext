## Schema Governance & Drift Management

Scope: Processes and tooling for managing Postgres (Supabase) schema evolution while protecting PII and ensuring reproducibility.

### Components
| Tool / Doc | Purpose | Path |
|------------|---------|------|
| Drift Check Script | Compares PRIMARY vs SECONDARY schemas (public) | `scripts/schema_drift_check.py` |
| Sanitized Export Script | Exports tables, non‑PII columns, RLS policies, SQL & Edge Functions metadata | `scripts/schema_export_sanitized.py` |
| PII Tagging Guide | Tag vocabulary for column/table comments | `docs/PII_TAGGING.md` |

### PII Tagging (Lite Classification)
Use comment markers `[PII]`, `[SENSITIVE]`, `[RESTRICTED]`. Column markers override table markers. See `docs/PII_TAGGING.md`.

### Daily / CI Workflow
1. (Local) Validate drift prior to applying new migrations:
   ```bash
  python scripts/schema_drift_check.py --emit-sanitized artifacts/schema/snapshot_local.json --json-out -
   ```
2. Apply migration(s) locally; re-run drift check to confirm expected delta only.
3. Commit migration SQL + updated snapshot (if repo policy enables storing).
4. CI: run drift check against cloud (`DATABASE_URL` + `SUPABASE_DB_URL`) with `--fatal-on-drift` to block unapproved changes introduced out-of-band.

### Sanitized Export
Produces JSON containing:
```jsonc
{
  "tables": { "table": { "columns": [...], "rls_policies": [...], "table_tags": [] } },
  "functions": [ { "name": "fn", "redacted": false } ],
  "edge_functions": [ { "name": "text_embed", "env_vars": ["OPENAI_API_KEY"] } ],
  "summary": { "tables": 12, "columns": 143, "pii_columns_skipped": 7, "edge_functions": 4 }
}
```
Usage examples:
```bash
python scripts/schema_export_sanitized.py --out schema_sanitized.json
python scripts/schema_export_sanitized.py --include-pii --out schema_full.json   # restricted use
```

### Edge Functions Metadata
The export gathers for each directory under `supabase/functions/`:
* `name`, `entry` (index.ts/js path)
* First comment header lines (max 6)
* Detected `Deno.env.get()` environment variable names
* Short SHA256 (first 16 hex) for integrity tracking

This allows delta review without embedding full source in governance artifacts.

### Recommended Retention
| Artifact | Retain | Reason |
|----------|--------|--------|
| Latest sanitized snapshot | Yes (VCS) | High-level audit evidence |
| Historical snapshots | Optional (S3/obj) | For forensic / rollback |
| Full (PII) snapshot | Avoid in VCS | Reduce breach blast radius |

### Guardrails
| Risk | Mitigation |
|------|-----------|
| Unlabeled PII column added | Pre-merge review; future: lint to enforce tag comment | 
| Out-of-band prod change | CI drift check with `--fatal-on-drift` |
| Function leaks PII logic in export | Redaction triggers if body references PII column names |
| Oversharing env needs in Edge Functions | Only name list captured; no values exported |

### Future Enhancements
* Index & constraint diffing (extend drift script with `pg_indexes`, `pg_constraint`).
* Column-level classification table (`data_classification`) to supplement comments.
* Migration manifest with semantic versioning & applied hash list.
* Git pre-commit hook: reject new columns in migrations lacking classification marker in adjacent `COMMENT ON`.
* Optional SQLite ephemeral projection for local debug (fast warm start).

### Pre-Commit Hook (PII Guard)

Script: `scripts/precommit_pii_guard.sh`

Heuristic: scans staged `supabase/migrations/*.sql` for new/added columns whose names match common PII patterns
(`email`, `phone`, `address`, `ip`, `name`, `dob`, etc.). If any such column lacks a `COMMENT ON COLUMN` (or table-level
`COMMENT ON TABLE`) containing one of `[PII]`, `[SENSITIVE]`, `[RESTRICTED]`, or `[NONPII]`, the commit is blocked.

Install (one-time):
```bash
chmod +x scripts/precommit_pii_guard.sh
ln -sf ../../scripts/precommit_pii_guard.sh .git/hooks/pre-commit
```

Bypass (not recommended):
```bash
ALLOW_UNTAGGED_PII=1 git commit -m "temp bypass"
```

Rationale: Enforces deliberate classification at introduction time; prevents silent drift of sensitive fields.

### Quick Commands (Copy/Paste)
```bash
# Compare local vs cloud, fail build if drift and emit JSON diff file
python scripts/schema_drift_check.py --fatal-on-drift --json-out drift_report.json

# Create sanitized audit snapshot
python scripts/schema_export_sanitized.py --out artifacts/schema/sanitized.json

# Create full snapshot (secured location only)
python scripts/schema_export_sanitized.py --include-pii --out /secure/tmp/schema_full.json
```

Maintain minimal, reviewable diff noise: avoid committing regenerated sanitized snapshots unless schema actually changed.
