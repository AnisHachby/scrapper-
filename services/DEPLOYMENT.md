# Deployment Guide

## Prerequisites
- Docker & Docker Compose installed
- 8GB RAM minimum
- 20GB disk space
- Data files in `project-pfe-repo/data/` (raw and processed)

## Quick Start

### 1. Build and Start All Services
```bash
cd C:\Work\Ayoub-choubouki-webscrapper\project-pfe-repo
docker-compose up --build
```

### 2. Verify Services Are Running
```bash
# Check health
curl http://localhost/health

# Check API
curl http://localhost:8000/health

# Check ML service
curl http://localhost:8001/health

# Check metrics
curl http://localhost:8002/metrics
```

### 3. Access Points
| Service | URL | Purpose |
|---------|-----|---------|
| Frontend Dashboard | http://localhost | Main UI |
| API Service | http://localhost:8000 | REST API |
| ML Service | http://localhost:8001 | Model inference |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Metrics | http://localhost:8002/metrics | Prometheus |
| Traefik Dashboard | http://localhost:8080 | Gateway monitoring |

## Testing the API

### Get a Signal Prediction
```bash
curl "http://localhost:8000/api/v1/signal/MA0000011489?date=2025-06-15&confidence_threshold=0.70"
```

### Batch Predictions
```bash
curl -X POST http://localhost:8000/api/v1/signal/batch \
  -H "Content-Type: application/json" \
  -d '{"isins": ["MA0000011489", "MA0000012345"], "date": "2025-06-15"}'
```

### Check Quota Status
```bash
curl http://localhost:8000/api/v1/quota/status
```

### Get Market Watch
```bash
curl http://localhost:8000/api/v1/market-watch
```

## Scaling

### Scale Individual Services
```bash
# Scale API service to 5 replicas
docker-compose up --scale api-service=5

# Scale workers to 10 replicas
docker-compose up --scale worker=10

# Scale ML service (usually keep at 1 for CPU-intensive tasks)
docker-compose up --scale ml-service=2
```

### Resource Limits
Edit `docker-compose.yml` to adjust CPU/memory limits per service.

## Monitoring

### Prometheus Metrics
Metrics are exposed at http://localhost:8002/metrics

Key metrics:
- `bvc_signals_total{signal_type="ACHAT"}` - Total signals generated
- `bvc_abstentions_total{reason="low_confidence"}` - Abstention reasons
- `bvc_quota_rejections_total{user_id="..."}` - Quota exhaustion
- `bvc_api_latency_seconds{endpoint="/predict"}` - API latency
- `bvc_circuit_breaker_state{service="ml_service"}` - Circuit state

### Grafana Dashboard
Create a new dashboard with these metrics to monitor:
- Signal generation rate
- Abstention rate by reason
- Quota exhaustion trends
- API latency percentiles
- Circuit breaker state changes

## Troubleshooting

### Model Not Loading
```bash
# Check if model file exists
ls -la project-pfe-repo/data/processed/model.joblib

# Check ML service logs
docker-compose logs ml-service

# Restart ML service
docker-compose restart ml-service
```

### Circuit Breaker Open
If ML service is overloaded or failing:
```bash
# Check ML service health
curl http://localhost:8001/health

# Check circuit breaker metrics
curl http://localhost:8002/metrics | grep circuit_breaker

# Restart if needed
docker-compose restart ml-service
```

### Quota Issues
If quotas are too restrictive:
```python
# In services/shared/quota_manager.py
daily_quota = QuotaManager(daily_quota=50)  # Increase to 50/day
ip_quota = QuotaManager(daily_quota=200)     # Increase to 200/day
```

## Production Checklist

- [ ] Set `allow_origins` in CORS to specific domains
- [ ] Add authentication (JWT/OAuth)
- [ ] Enable TLS/HTTPS
- [ ] Configure Redis persistence
- [ ] Set up log aggregation (ELK/Loki)
- [ ] Configure alerts in Grafana
- [ ] Backup model files
- [ ] Load test with expected traffic
- [ ] Document runbooks for common issues
- [ ] Set up CI/CD pipeline

## Rollback Procedure

If a new model version causes issues:
```bash
# Access model registry
docker-compose exec ml-service python -c "
from services.ml_service.model_registry import ModelRegistry
registry = ModelRegistry(Path('/models'))
registry.rollback('v2.0.0')  # Rollback to previous version
"

# Restart ML service
docker-compose restart ml-service
```

## Support

For issues or questions:
1. Check logs: `docker-compose logs <service-name>`
2. Check health endpoints
3. Review metrics at http://localhost:8002/metrics
4. Check Traefik dashboard at http://localhost:8080
