## PII / Sensitive Data Tagging

Purpose: Consistent lightweight classification so tooling can exclude or redact sensitive fields in exports / backups.

### Tag Markers
Add markers inside comments (case-insensitive):

```
[PII]          -> Personally identifiable information
[SENSITIVE]    -> Business-sensitive but not direct PII
[RESTRICTED]   -> Access restricted (combine with others)
```

Multiple markers allowed: `[PII][EMAIL][GDPR]`.

### Applying Tags
Column level (preferred):
```sql
COMMENT ON COLUMN users.email IS 'User email for contact [PII][EMAIL]';
COMMENT ON COLUMN users.created_at IS 'Row creation timestamp';
```

Table level (applies to all columns lacking explicit tags):
```sql
COMMENT ON TABLE audit_log IS 'Security audit events [SENSITIVE]';
```

### Function Redaction
If a function body references any PII-tagged column name and export runs WITHOUT `--include-pii`, body is replaced with:
```
-- REDACTED (references PII columns)
```

### Policies
RLS policies are always exported for review; they rarely leak raw data values. If a policy references PII columns the policy text still appears.

### Export Tooling
Run sanitized export:
```
python scripts/schema_export_sanitized.py --out schema_sanitized.json
```
Full (includes PII):
```
python scripts/schema_export_sanitized.py --include-pii --out schema_full.json
```

### Future Enhancements
- Dedicated classification table (e.g. `data_classification(table, column, level)`).
- Encrypted column set (PG crypto) plus masking views.
- Policy to reject INSERT/UPDATE missing classification comment.

Keep markers factual and minimal.
