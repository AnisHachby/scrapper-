#!/usr/bin/env python3
"""
Test script for migrated services.
"""
import sys
import subprocess
import time
import httpx

print("=" * 60)
print("TESTING MIGRATED SERVICES")
print("=" * 60)

# Test 1: Import adapters
print("\n[1/5] Testing adapter imports...")
try:
    sys.path.insert(0, 'src')
    from adapters.model_adapter import get_model_adapter
    from adapters.dashboard_adapter import get_dashboard_adapter
    from adapters.pipeline_adapter import get_pipeline_adapter
    print("[OK] All adapters imported successfully")
except Exception as e:
    print(f"[X] Adapter import failed: {e}")
    sys.exit(1)

# Test 2: Import services
print("\n[2/5] Testing service imports...")
try:
    sys.path.insert(0, 'services')
    from api_service.main import app as api_app
    from ml_service.main import app as ml_app
    print("[OK] All services imported successfully")
except Exception as e:
    print(f"[X] Service import failed: {e}")
    sys.exit(1)

# Test 3: Start ML service
print("\n[3/5] Starting ML service...")
try:
    ml_process = subprocess.Popen(
        ["py", "-m", "uvicorn", "services.ml_service.main:app", "--host", "0.0.0.0", "--port", "8001"],
        cwd="C:\\Work\\Ayoub-choubouki-webscrapper\\project-pfe-repo"
    )
    time.sleep(3)  # Wait for startup
    
    # Test health
    response = httpx.get("http://localhost:8001/health", timeout=5)
    if response.status_code == 200:
        print(f"[OK] ML service running: {response.json()}")
    else:
        print(f"[X] ML service returned {response.status_code}")
    
    ml_process.terminate()
except Exception as e:
    print(f"[X] ML service test failed: {e}")

# Test 4: Start API service
print("\n[4/5] Starting API service...")
try:
    api_process = subprocess.Popen(
        ["py", "-m", "uvicorn", "services.api_service.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd="C:\\Work\\Ayoub-choubouki-webscrapper\\project-pfe-repo"
    )
    time.sleep(3)
    
    response = httpx.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        print(f"[OK] API service running: {response.json()}")
    else:
        print(f"[X] API service returned {response.status_code}")
    
    api_process.terminate()
except Exception as e:
    print(f"[X] API service test failed: {e}")

# Test 5: Test adapters in local mode
print("\n[5/5] Testing adapters in local mode...")
try:
    model_adapter = get_model_adapter(use_service=False)
    dashboard_adapter = get_dashboard_adapter(use_service=False)
    pipeline_adapter = get_pipeline_adapter(use_service=False)
    print("[OK] All adapters work in local mode")
except Exception as e:
    print(f"[X] Adapter test failed: {e}")

print("\n" + "=" * 60)
print("TESTING COMPLETE")
print("=" * 60)
print("\nNext steps:")
print("1. Start services manually:")
print("   - ML: uvicorn services.ml_service.main:app --port 8001")
print("   - API: uvicorn services.api_service.main:app --port 8000")
print("2. Switch adapters to service mode (USE_SERVICE = True)")
print("3. Run: py src/model.py")
