# FIN Phase 9 — Local Operations & Run Guide

## 1. Prerequisites

- Python 3.10+ (tested on Python 3.11 Windows)
- Working directory: `c:\Users\ozhad\Desktop\HackMatrix\PCCOE-HackMatrix\AI`

---

## 2. Starting the Microservice

From the `Intelligence/` directory, launch the Uvicorn ASGI server:

```powershell
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

Output:
```
INFO:     Started server process [21796]
INFO:     Waiting for application startup.
INFO:     Initializing FIN AI Microservice (version 1.0.0)...
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 3. Interactive API Documentation

Once the server is running, navigate in your browser to:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## 4. Quick CLI Verification Queries (PowerShell / cURL)

### Health Check (Public)
```powershell
curl http://localhost:8000/health/live
```
Response:
```json
{"status":"ok","service":"fin-ai"}
```

### Readiness Check (Protected)
```powershell
curl http://localhost:8000/health/ready `
  -H "X-AI-Service-Key: fin_internal_dev_key"
```

### Deterministic Eligibility Check (Protected)
```powershell
curl -X POST http://localhost:8000/v1/eligibility/check `
  -H "Content-Type: application/json" `
  -H "X-AI-Service-Key: fin_internal_dev_key" `
  -d '{"applicant_facts": {"owns_cultivable_land": true, "is_institutional_landholder": false, "is_taxpayer": false, "monthly_pension_amount": 0}, "scheme_ids": ["pm-kisan"]}'
```

### Grounded Citizen Chat (Protected)
```powershell
curl -X POST http://localhost:8000/v1/chat `
  -H "Content-Type: application/json" `
  -H "X-AI-Service-Key: fin_internal_dev_key" `
  -d '{"query": "What are the benefits under PM Kisan?", "conversation_id": "test_conv_01"}'
```

---

## 5. Graceful Shutdown

Press `Ctrl + C` in the running PowerShell terminal to initiate graceful shutdown. All pending requests will complete before process exit.
