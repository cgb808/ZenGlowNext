## Docker Swarm Deployment (Baseline)

This sets up a minimal Swarm stack: Postgres (pgvector) + replicated indexer service.

### Files
- `deploy/docker-stack.yml` – Swarm stack definition.
- `deploy/secrets/pg_password.txt` – Postgres password (not committed; create locally).

### 1. Initialize Swarm (once)
```
docker swarm init
```
If you have multiple nodes, join workers using the token displayed.

### 2. Prepare Secrets
```
mkdir -p deploy/secrets
echo 'your-super-strong-and-secret-password' > deploy/secrets/pg_password.txt
```
Keep this out of version control (folder already contains `.gitkeep`).

### 3. Build & Push (or build on each node)
Option A (registry):
```
docker build -t your-registry/zenglow-indexer:latest .
docker push your-registry/zenglow-indexer:latest
```
Update `image:` in stack file accordingly.

Option B (no registry, single node):
```
docker build -t zenglow/indexer:latest .
```

### 4. Deploy Stack
```
docker stack deploy -c deploy/docker-stack.yml zenglow
```

### 5. Check Status
```
docker stack services zenglow
docker service ls
docker service ps zenglow_indexer
```

### 6. Logs
```
docker service logs -f zenglow_indexer
```

### 7. Scale Indexer
```
docker service scale zenglow_indexer=3
```

### 8. Rolling Update
After pushing a new image tag:
```
docker service update --image your-registry/zenglow-indexer:latest zenglow_indexer
```

### Environment & Secrets
`POSTGRES_PASSWORD_FILE` is used; inside the container the app should read the file (or we substitute env). Update `DATABASE_URL` at runtime via template substitution or modify entrypoint to read the file and export the variable.

### Health & Ordering
Swarm does not honor `depends_on` health sequencing. The indexer should tolerate initial DB connection failures (retry loop or startup delay). If needed, add a simple wait-for-db wrapper script.

### Persistence
`pgdata` volume is local to each node hosting the `db` task. Run the database on a manager or label a dedicated storage node.

### Hardening TODO (future):
1. External secrets manager (Vault / AWS SM) instead of file secret.
2. RLS + masking for PII tables before promoting to multi-tenant production.
3. Traefik / Nginx ingress with TLS termination.
4. Metrics & logging aggregation (Prometheus, Loki).
5. Automated backup job (pg_dump + retention).

### Removal
```
docker stack rm zenglow
```

Wait for tasks to drain, then optionally `docker swarm leave --force` on worker nodes.

---
Baseline only; expand with ingress + observability before production traffic.