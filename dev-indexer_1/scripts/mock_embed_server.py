#!/usr/bin/env python3
"""
Minimal mock embed HTTP server using only Python stdlib.
Endpoint: POST /model/embed { "texts": ["...", "..."] }
Response: { "embeddings": [[...DIM...], ...] }

Env:
  EMBED_DIM   (default 384)
  EMBED_HOST  (default 127.0.0.1)
  EMBED_PORT  (default 8000)
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json, os, random

DIM = int(os.getenv("EMBED_DIM", "384"))
HOST = os.getenv("EMBED_HOST", "127.0.0.1")
PORT = int(os.getenv("EMBED_PORT", "8000"))


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 (stdlib signature)
        if self.path != "/model/embed":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            data = {}
        texts = data.get("texts") or []
        embs = []
        for t in texts:
            random.seed(len(t))
            embs.append([random.random() for _ in range(DIM)])
        out = json.dumps({"embeddings": embs}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


if __name__ == "__main__":
    httpd = HTTPServer((HOST, PORT), Handler)
    print(f"[mock-embed] serving on http://{HOST}:{PORT}")
    httpd.serve_forever()
