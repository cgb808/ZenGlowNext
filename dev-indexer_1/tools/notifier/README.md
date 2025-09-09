# Go Notifier (Templated HTTP)

Tiny CLI that renders an HTTP request from a Go text/template into JSON, then executes it.

- Binary: `go build -o notifier ./tools/notifier`
- Template: JSON with fields { method, url, headers, body }
- Helpers in templates: `env`, `now`, `join`

## Usage

```bash
# Build
cd tools/notifier && go build -o ../../bin/notifier .

# Gate opened
GATE_URL=https://example.com/hooks/ingest \
GATE_TOKEN=secret \
../../bin/notifier \
  -template templates/gate_open.json.tmpl \
  -data '{"batch_tag":"spool_20250909_101010","count":42,"bytes":123456,"spool":"/data/spool/processing"}' -v

# Gate done
GATE_URL=https://example.com/hooks/ingest \
GATE_TOKEN=secret \
../../bin/notifier \
  -template templates/gate_done.json.tmpl \
  -data '{"batch_tag":"spool_20250909_101010","status":"success","processed":42}' -v
```

Exit code is non-zero if `-require-2xx` is true and HTTP status is not 2xx.
