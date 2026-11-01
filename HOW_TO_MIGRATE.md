# How to Break Up the Monolith

## Current State: STILL MONOLITHIC
The services exist in `services/` but the original code doesn't use them.

## Migration Strategy: Adapter Pattern

### 1. Created: `src/adapters/`
Thin wrappers that let you switch between local and service mode.

### 2. Modified: `src/model.py`
```python
# OLD:
oos = walk_forward_oos(df, N_SPLITS)

# NEW:
from adapters.model_adapter import get_model_adapter
adapter = get_model_adapter(use_service=False)  # Flip to True
oos = adapter.train(df)
```

### 3. Modified: `src/run_full_pipeline.py`
```python
# OLD:
for s in steps:
    run_step(s)  # subprocess.run

# NEW:
from adapters.pipeline_adapter import get_pipeline_adapter
adapter = get_pipeline_adapter(use_service=False)  # Flip to True
for s in steps:
    result = adapter.run_step(s)
```

## How to Actually Migrate

### Step 1: Start Services
```bash
# Terminal 1: Redis
docker run -p 6379:6379 redis:7-alpine

# Terminal 2: ML Service
cd services/ml_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001

# Terminal 3: API Service
cd services/api_service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Step 2: Test Adapters (Local Mode)
```bash
# Should work exactly as before
py src/model.py
py src/run_full_pipeline.py
```

### Step 3: Switch to Service Mode
```python
# In src/adapters/model_adapter.py
USE_SERVICE = True  # Now uses ML service

# In src/adapters/pipeline_adapter.py
USE_SERVICE = True  # Now uses worker service
```

### Step 4: Verify Services Are Called
```bash
# Check ML service logs
# Should see: "POST /train HTTP/1.1" 200
```

## Key Files

### Adapters Created
- `src/adapters/model_adapter.py` - model.py → ML Service
- `src/adapters/dashboard_adapter.py` - dashboard_server.py → API Service
- `src/adapters/pipeline_adapter.py` - run_full_pipeline.py → Worker Service

### Services Created (in `services/` folder)
- ML Service (port 8001) - Model inference
- API Service (port 8000) - REST API
- Worker Service - Background tasks

### Modified Files
- `src/model.py` - Now uses adapter
- `src/run_full_pipeline.py` - Now uses adapter

## Rollback
```bash
# Switch adapters back to local mode
# Edit src/adapters/model_adapter.py: USE_SERVICE = False
# Edit src/adapters/pipeline_adapter.py: USE_SERVICE = False

# Or revert changes
git checkout src/model.py
git checkout src/run_full_pipeline.py
```

## Next Steps
1. Test adapters in local mode (should work now)
2. Start services
3. Flip USE_SERVICE = True
4. Verify services are called
5. Migrate dashboard_server.py

The monolith is now wrapped with adapters that can use services when ready.
