# 🚨 Parental Predictor - Operations Runbook

## 🚀 Quick Start

### Essential Commands

```bash
# Deploy production stack
docker stack deploy -c prod/zendexer_Swarm_Prod.compose zendexer-prod

# Check service health
curl http://localhost:8002/health

# View real-time logs
docker service logs -f zendexer-prod_smollm-predictor

# Scale service
docker service scale zendexer-prod_smollm-predictor=3
```

## 🔍 Health Checks

### Service Status

```bash
# Check service status
docker service ps zendexer-prod_smollm-predictor

# Expected output:
# ID      NAME                        IMAGE                     NODE    DESIRED STATE   CURRENT STATE
# abc123  zendexer-prod_smollm-predictor.1  zendexer/phi2-predictor:latest  node1   Running         Running 2 hours ago
```

### API Health Verification

```bash
# Primary health endpoint
curl -f http://localhost:8002/health
# Expected: {"status":"healthy","model":"phi-2","mode":"parental_prediction"}

# Detailed health check
curl http://localhost:8002/health/detailed
# Expected: Full system status including model load, memory usage, cache status
```

### Resource Monitoring

```bash
# Container resource usage
docker stats $(docker ps -q --filter "name=zendexer-prod_smollm-predictor")

# Service resource limits
docker service inspect zendexer-prod_smollm-predictor --format='{{.Spec.TaskTemplate.Resources}}'
```

## 🚨 Incident Response

### High Priority Incidents

#### Service Down

```bash
# Immediate Response (< 2 minutes)
1. Check service status:
   docker service ps zendexer-prod_smollm-predictor

2. Check recent logs:
   docker service logs --tail 100 zendexer-prod_smollm-predictor

3. Restart if needed:
   docker service update --force zendexer-prod_smollm-predictor

4. Verify restoration:
   curl http://localhost:8002/health
```

#### High Latency (>1 second predictions)

```bash
# Investigation Steps
1. Check resource usage:
   docker stats $(docker ps -q --filter "name=zendexer-prod_smollm-predictor")

2. Check cache hit rate:
   curl http://localhost:8002/metrics | grep cache_hit_rate

3. Scale if needed:
   docker service scale zendexer-prod_smollm-predictor=4

4. Monitor improvement:
   curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8002/predict/test
```

#### Memory Issues (>90% usage)

```bash
# Immediate Actions
1. Check memory usage per container:
   docker exec -it <container_id> cat /proc/meminfo

2. Clear model cache if safe:
   curl -X POST http://localhost:8002/admin/clear-cache

3. Restart containers gradually:
   docker service update --update-parallelism 1 --update-delay 60s zendexer-prod_smollm-predictor

4. Monitor memory after restart:
   watch docker stats
```

### Medium Priority Incidents

#### Prediction Accuracy Degradation

```bash
# Investigation
1. Check model confidence scores:
   curl http://localhost:8002/metrics | grep confidence

2. Review recent prediction logs:
   docker service logs zendexer-prod_smollm-predictor | grep "confidence"

3. Compare with baseline metrics:
   # Review historical performance data

4. Consider model reload:
   curl -X POST http://localhost:8002/admin/reload-model
```

#### High Error Rate (>2%)

```bash
# Troubleshooting
1. Identify error types:
   docker service logs zendexer-prod_smollm-predictor | grep ERROR

2. Check input validation:
   curl http://localhost:8002/validate/input -d '{"test":"data"}'

3. Verify dependencies:
   curl http://phi2-assistant:8001/health
   curl http://mistral-interface:8080/health

4. Check network connectivity:
   docker exec -it <container_id> ping redis
```

## 📊 Performance Tuning

### Optimization Checklist

#### CPU Optimization

```bash
# Check CPU usage patterns
docker exec -it <container_id> top -p $(pgrep python)

# Adjust if needed
docker service update --limit-cpu 3 zendexer-prod_smollm-predictor

# Monitor impact
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

#### Memory Optimization

```bash
# Model memory usage
docker exec -it <container_id> python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"

# Adjust batch size
curl -X POST http://localhost:8002/admin/config -d '{"batch_size": 8}'

# Restart with new limits
docker service update --limit-memory 4g zendexer-prod_smollm-predictor
```

#### Cache Optimization

```bash
# Check cache statistics
curl http://localhost:8002/metrics | grep cache

# Adjust cache size
curl -X POST http://localhost:8002/admin/config -d '{"cache_size": 2000}'

# Clear and rebuild cache
curl -X POST http://localhost:8002/admin/rebuild-cache
```

### Load Testing

```bash
# Basic load test
for i in {1..100}; do
  curl -s http://localhost:8002/predict/test > /dev/null &
done
wait

# Advanced load testing with ab
ab -n 1000 -c 10 http://localhost:8002/predict/test

# Monitor during load test
watch -n 1 'docker stats --no-stream'
```

## 🔧 Configuration Management

### Environment Variables Update

```bash
# Update environment variable
docker service update --env-add NEW_VAR=value zendexer-prod_smollm-predictor

# Remove environment variable
docker service update --env-rm OLD_VAR zendexer-prod_smollm-predictor

# Apply configuration file changes
docker service update --config-add prod-config.yml zendexer-prod_smollm-predictor
```

### Model Updates

```bash
# Update model image
docker service update --image zendexer/phi2-predictor:v1.2.0 zendexer-prod_smollm-predictor

# Rolling update with zero downtime
docker service update --update-parallelism 1 --update-delay 30s --image zendexer/phi2-predictor:latest zendexer-prod_smollm-predictor

# Rollback if needed
docker service rollback zendexer-prod_smollm-predictor
```

## 📈 Monitoring & Alerts

### Key Metrics to Monitor

#### Application Metrics

```bash
# Prediction metrics
curl http://localhost:8002/metrics | grep -E "(prediction_|confidence_|latency_)"

# Family metrics
curl http://localhost:8002/metrics | grep -E "(family_|child_|parent_)"

# System metrics
curl http://localhost:8002/metrics | grep -E "(memory_|cpu_|cache_)"
```

#### Infrastructure Metrics

```bash
# Container health
docker service ps zendexer-prod_smollm-predictor --format "table {{.Name}}\t{{.CurrentState}}\t{{.Error}}"

# Network connectivity
docker exec -it <container_id> nc -zv redis 6379
docker exec -it <container_id> nc -zv phi2-assistant 8001
```

### Alert Thresholds

```yaml
Critical (Immediate Response):
  - Service down > 30 seconds
  - Error rate > 5%
  - Prediction latency > 1 second
  - Memory usage > 95%
  - No successful predictions > 2 minutes

Warning (Response within 15 minutes):
  - Error rate > 2%
  - Prediction latency > 500ms
  - Memory usage > 85%
  - Cache hit rate < 70%
  - CPU usage > 80%

Info (Response within 1 hour):
  - Memory usage > 70%
  - Cache hit rate < 85%
  - CPU usage > 60%
  - Unusual traffic patterns
```

## 🔐 Security Operations

### Security Health Checks

```bash
# Certificate validation
openssl s_client -connect localhost:8002 -servername localhost

# Access control verification
curl -H "Authorization: Bearer invalid_token" http://localhost:8002/predict/test
# Expected: 401 Unauthorized

# Audit log verification
docker exec -it <container_id> tail -f /app/audit_logs/access.log
```

### Security Incident Response

```bash
# Suspicious Activity Detection
1. Check access logs:
   docker exec -it <container_id> grep "SUSPICIOUS" /app/audit_logs/access.log

2. Review failed authentication attempts:
   docker exec -it <container_id> grep "401\|403" /app/logs/access.log

3. Verify SSL/TLS status:
   curl -I https://localhost:8002/health

4. Check for unauthorized model access:
   docker exec -it <container_id> grep "model_access" /app/audit_logs/model.log
```

## 🔄 Backup & Recovery

### Backup Procedures

```bash
# Model state backup
docker exec -it <container_id> tar -czf /app/backups/model_$(date +%Y%m%d).tar.gz /app/model_cache

# Configuration backup
docker config ls | grep zendexer-prod
docker config inspect zendexer-prod-config > config_backup_$(date +%Y%m%d).json

# Family data backup (if applicable)
docker exec -it <container_id> pg_dump family_data > family_backup_$(date +%Y%m%d).sql
```

### Recovery Procedures

```bash
# Service recovery from backup
1. Stop current service:
   docker service scale zendexer-prod_smollm-predictor=0

2. Restore model state:
   docker exec -it <container_id> tar -xzf /app/backups/model_20250811.tar.gz

3. Restart service:
   docker service scale zendexer-prod_smollm-predictor=2

4. Verify recovery:
   curl http://localhost:8002/health
```

## 📋 Maintenance Procedures

### Routine Maintenance (Weekly)

```bash
# Log rotation
docker exec -it <container_id> logrotate /etc/logrotate.d/zendexer

# Cache cleanup
curl -X POST http://localhost:8002/admin/cache/cleanup

# Model performance check
curl http://localhost:8002/admin/model/benchmark

# Security update check
docker exec -it <container_id> apt list --upgradable
```

### Planned Maintenance (Monthly)

```bash
# Full system backup
./scripts/backup_full_system.sh

# Performance optimization
curl -X POST http://localhost:8002/admin/optimize

# Security scan
docker exec -it <container_id> clamscan -r /app

# Update dependencies
docker service update --image zendexer/phi2-predictor:latest zendexer-prod_smollm-predictor
```

## 📞 Escalation Procedures

### Level 1: Automated Recovery

- Service restart attempts
- Cache clearing
- Basic diagnostics

### Level 2: Operations Team

- **Contact**: ops-team@zenglow.ai
- **Response Time**: 15 minutes
- **Scope**: Infrastructure issues, scaling, configuration

### Level 3: Development Team

- **Contact**: dev-team@zenglow.ai
- **Response Time**: 1 hour
- **Scope**: Model issues, application bugs, performance optimization

### Level 4: Architecture Team

- **Contact**: arch-team@zenglow.ai
- **Response Time**: 4 hours
- **Scope**: Design issues, major infrastructure changes

---

**🚨 Emergency Contact**: +1-800-ZENGLOW (24/7 critical issues)
**📚 Documentation**: https://docs.zenglow.ai/parental-predictor
**🎫 Ticket System**: https://tickets.zenglow.ai
