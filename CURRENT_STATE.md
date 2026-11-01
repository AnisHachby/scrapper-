# Current State: Monolith → Microservices Migration

## Status: IN PROGRESS - Adapters Created, Ready for Testing

---

## What's Done

### 1. Services Created (`services/` folder)
All microservices are coded and ready:
- ✅ `services/shared/` - Common library (schemas, circuit_breaker, quota_manager, etc.)
- ✅ `services/ml_service/` - Model inference server (port 8001)
- ✅ `services/api_service/` - REST API server (port 8000)
- ✅ `services/worker_service/` - Background tasks
- ✅ `services/frontend/` - Nginx config
- ✅ `services/docker-compose.yml` - Full stack orchestration

### 2. Adapters Created (`src/adapters/` folder)
Thin wrappers that let monolith use services:
- ✅ `src/adapters/model_adapter.py` - Wraps model.py
- ✅ `src/adapters/dashboard_adapter.py` - Wraps dashboard_server.py
- ✅ `src/adapters/pipeline_adapter.py` - Wraps run_full_pipeline.py

### 3. Monolith Modified
Actual changes to original files:
- ✅ `src/model.py` - Now uses adapter (line 121-124)
- ✅ `src/run_full_pipeline.py` - Now uses adapter (line 25-41)
- ✅ `src/dashboard_server.py` - Now imports from migrated_dashboard

### 4. Migrated Files Created
- ✅ `src/migrated_dashboard.py` - Clean dashboard using adapters
- ✅ `src/migrated_model.py` - Clean model using adapters
- ✅ `src/migrated_pipeline.py` - Clean pipeline using adapters

---

## How to Test Right Now

### Test 1: Local Mode (No Services Needed)
```bash
# Should work exactly as before
cd C:\Work\Ayoub-choubouki-webscrapper\project-pfe-repo

# Test model
py src/model.py

# Test pipeline
py src/run_full_pipeline.py

# Test dashboard
uvicorn src.dashboard_server:app --port 8000
# Then visit: http://localhost:8000
```

### Test 2: Service Mode (Requires Services Running)
```bash
# Terminal 1: Start Redis
docker run -p 6379:6379 redis:7-alpine

# Terminal 2: Start ML Service
cd services/ml_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001

# Terminal 3: Start API Service
cd services/api_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 4: Switch to service mode and test
# Edit src/adapters/model_adapter.py: USE_SERVICE = True
py src/model.py
```

---

## File Structure

```
project-pfe-repo/
├── src/
│   ├── adapters/                      # NEW: Adapter layer
│   │   ├── model_adapter.py          # model.py → ML Service
│   │   ├── dashboard_adapter.py      # dashboard_server.py → API Service
│   │   └── pipeline_adapter.py       # pipeline → Worker Service
│   │
│   ├── model.py                       # MODIFIED: Uses adapter
│   ├── dashboard_server.py            # MODIFIED: Imports migrated
│   ├── run_full_pipeline.py           # MODIFIED: Uses adapter
│   │
│   ├── migrated_dashboard.py          # NEW: Clean dashboard
│   ├── migrated_model.py              # NEW: Clean model
│   └── migrated_pipeline.py           # NEW: Clean pipeline
│
├── services/
│   ├── shared/                        # Common library
│   ├── ml_service/                    # Port 8001
│   ├── api_service/                   # Port 8000
│   ├── worker_service/                # Background tasks
│   ├── frontend/                      # Nginx
│   └── docker-compose.yml             # Full stack
│
├── HOW_TO_MIGRATE.md                  # Migration guide
└── CURRENT_STATE.md                   # This file
```

---

## The Migration Pattern

### Before (Monolith):
```python
# src/model.py
def main():
    df = pd.read_parquet(...)
    oos = walk_forward_oos(df, N_SPLITS)  # Direct call
    # ... 60 more lines
```

### After (With Adapter):
```python
# src/model.py
def main():
    df = pd.read_parquet(...)
    from adapters.model_adapter import get_model_adapter
    adapter = get_model_adapter(use_service=False)  # or True
    oos = adapter.train(df)  # Can use local OR service
    # ... rest of code unchanged
```

### How to Switch to Service:
```python
# In src/adapters/model_adapter.py
USE_SERVICE = False  # Change to True

# That's it! Now model.py calls ML service instead of local processing.
```

---

## What's Still Monolithic

These files are NOT yet migrated (but can be used as-is):
- `src/features.py` - Standalone feature engineering
- `src/labels.py` - Standalone labeling
- `src/backtest.py` - Standalone backtesting
- `src/fetch_bulletins.py` - Scraping
- All other src/*.py files

They work as standalone scripts and don't need migration unless you want them as services.

---

## Next Steps

1. **Test local mode** - Run `py src/model.py` to verify adapters work
2. **Start services** - Run ML and API services
3. **Switch to service mode** - Change `USE_SERVICE = True`
4. **Test service mode** - Verify services are called
5. **Deploy** - Use `docker-compose up --build`

---

## Key Benefit

**Zero-risk migration:** The adapters let you switch between local and service mode with one boolean flip. You can test each migration step independently and rollback instantly if something breaks.

```python
# Rollback: Just change False → True
adapter = get_model_adapter(use_service=False)  # Back to local
```

---

*Status: Adapters created, monolith wrapped, ready for testing*
*Date: 2026-04-08*
