# Lecture 18: Logging, Monitoring & Observability - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Logging, Monitoring & Observability - Understanding Your System  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Core Philosophy from Your Lecture

> **"Logging, monitoring, and observability represent a spectrum of practices essential for managing modern distributed backends."**

### **The Three Concepts**

```
LOGGING ────→ MONITORING ────→ OBSERVABILITY
(Recording)   (Tracking)      (Understanding)

"What happened?"  "Something's wrong!"  "Why it's wrong & how to fix it"
```

**Not rigid rules, but a spectrum.**  
No company has 100% perfect observability — implement what makes practical sense for your resources.

---

## 📝 1. LOGGING - Recording Events

### **Definition**

> **"A journal or diary that the backend maintains to track what happened, when it happened, and why."**

**Purpose:** Record all important, suspicious, and security-related events throughout the application lifecycle.

---

### **Log Levels (Severity)**

| Level | When to Use | Example | Environment |
|-------|------------|---------|-------------|
| **DEBUG** | Detailed troubleshooting | "Function called with args: {x, y, z}" | Dev only |
| **INFO** | Successful operations | "User created todo item" | Dev + Prod |
| **WARN** | Non-critical issues (not app's fault) | "User typed incorrect password" | Dev + Prod |
| **ERROR** | Significant failures | "Database query failed" | Dev + Prod |
| **FATAL** | Catastrophic bugs | "Cannot connect to DB, shutting down" | Prod |

**Rule:** 
- **Dev:** DEBUG enabled (see everything)
- **Prod:** INFO and above (reduce noise)

---

### **Structured vs Unstructured Logs**

#### **Unstructured (Development)**

**Format:** Plain text, human-readable, colorized

```python
# Console output (development)
2024-01-29 10:30:15 - INFO - User alice created todo item "Buy milk"
2024-01-29 10:30:16 - ERROR - Database connection failed
```

**Pros:** Easy for humans to read  
**Cons:** Hard for tools to parse

---

#### **Structured (Production)**

**Format:** JSON, machine-parseable

```json
{
  "timestamp": "2024-01-29T10:30:15Z",
  "level": "INFO",
  "message": "User created todo item",
  "user_id": 123,
  "todo_id": 456,
  "todo_title": "Buy milk",
  "request_id": "req-abc-123",
  "latency_ms": 45,
  "function": "create_todo"
}
```

**Pros:** ELK stack / Loki can parse and search  
**Cons:** Harder for humans to read directly

**Why JSON in production:**
- Log management tools need structured data
- Enable searching: "Show all errors for user_id=123"
- Enable aggregation: "Count errors per endpoint"
- Enable correlation: "Find all logs for request_id=req-abc-123"

---

### **Essential Metadata in Logs**

```python
logger.info("User created todo", extra={
    "user_id": user.id,              # Who
    "todo_id": todo.id,              # What
    "request_id": request_id,        # Which request (correlation)
    "latency_ms": latency,           # Performance
    "function": "create_todo",       # Where
    "endpoint": "/api/todos",        # API route
    "ip_address": client_ip,         # Network info
    "user_agent": user_agent         # Client info
})
```

**Critical:** Never log passwords, API keys, credit cards, or PII!

---

## 📊 2. MONITORING - Tracking State

### **Definition**

> **"Tracking the real-time state and health of your system."**

**Purpose:** Measure system resources and application metrics to detect problems.

---

### **What to Monitor**

#### **System Metrics (Infrastructure)**
```
- CPU usage (%)
- Memory consumption (MB)
- Disk I/O (reads/writes per second)
- Network traffic (bytes in/out)
- Open database connections
- Request rate (req/s)
```

#### **Application Metrics (Business)**
```
- API response time (p50, p95, p99)
- Error rate (%)
- Successful transactions per minute
- Cache hit rate (%)
- Queue length (background tasks)
- Active users
```

---

### **Monitoring Limitation**

**Monitoring tells you THAT a problem exists, but NOT what's wrong or how to fix it.**

```
Alert: "Error rate > 80%!" ⚠️
    ↓
Question: "But why? Which endpoint? What error?"
    ↓
Need: Logs + Traces (observability)
```

**Typical delay:** 10-15 seconds (to avoid overwhelming system with telemetry)

---

## 🔍 3. OBSERVABILITY - Understanding the System

### **Definition**

> **"A system is observable if you can determine its internal state purely by looking at its external outputs."**

**Purpose:** Tell you exactly WHAT is wrong and HOW to fix it.

---

### **The Three Pillars of Observability**

```
┌─────────────────────────────────────────────┐
│         OBSERVABILITY PILLARS               │
├─────────────────────────────────────────────┤
│                                             │
│  1. LOGS                                    │
│     → Tell you WHAT happened                │
│     → Detailed event records                │
│                                             │
│  2. METRICS                                 │
│     → Provide NUMBERS (trends, patterns)    │
│     → Error rates, latency, throughput      │
│                                             │
│  3. TRACES                                  │
│     → Track ENTIRE request lifecycle        │
│     → See every component touched           │
│                                             │
└─────────────────────────────────────────────┘
```

---

### **Pillar 1: Logs**

**What:** Detailed event records

```json
{
  "timestamp": "2024-01-29T10:30:15Z",
  "level": "ERROR",
  "message": "Database connection timeout",
  "error_type": "ConnectionTimeout",
  "query": "SELECT * FROM users WHERE id = ?",
  "request_id": "req-abc-123"
}
```

**Answer:** WHAT happened? "Database connection timeout"

---

### **Pillar 2: Metrics**

**What:** Concrete numbers revealing patterns

```
Error rate: 85% (spiked from 1%)
Response time p95: 5000ms (increased from 200ms)
Database connections: 50/50 (pool exhausted!)
Failed requests: 1,250 in last 5 minutes
```

**Answer:** HOW BAD is it? "85% error rate, pool exhausted"

---

### **Pillar 3: Traces**

**What:** Track entire request lifecycle

```
Request: POST /api/todos
    ↓ 5ms    Handler (validate request)
    ↓ 10ms   Service Layer (business logic)
    ↓ 2500ms Database Query (SLOW! ⚠️)
    ↓ 5ms    Return response
Total: 2520ms

Bottleneck identified: Database query took 2500ms!
```

**Answer:** WHERE did it fail? "Database query was slow"

---

## 🔧 The Complete Debugging Workflow

**Scenario:** Production API suddenly slow

```
STEP 1: ALERT
  Slack notification: "API error rate > 80%"
  
STEP 2: METRICS (Dashboard)
  Open Grafana
  See: Error rate spiked to 85%
  See: p95 latency jumped to 5000ms
  See: Database connection pool at 50/50 (maxed!)
  
STEP 3: LOGS (Search)
  Filter logs by time range + error level
  Find: "ConnectionTimeout: Database pool exhausted"
  Find: 1,250 errors for request_id pattern "req-abc-*"
  
STEP 4: TRACES (Root Cause)
  Click on one error log
  View its trace:
    Handler → 5ms ✅
    Service → 10ms ✅
    Database Query → 2500ms ❌ (BOTTLENECK!)
  
DIAGNOSIS: Database connection pool exhausted
SOLUTION: Increase pool size OR optimize slow query
```

**With observability:** 5 minutes to root cause  
**Without observability:** Hours of guessing

---

## 🛠️ Implementation: Code-Level Instrumentation

### **What is Instrumentation?**

> **"Actively measuring different attributes of your functions as they execute."**

**Before tools can display dashboards, the application code must generate the data.**

---

### **The Standard: OpenTelemetry**

**What:** Open standard for instrumentation

**Provides:**
- SDKs for all major languages (Python, Node.js, Go, Java)
- APIs for logging, metrics, traces
- Best practices and conventions

**Why:** Vendor-neutral, works with any observability tool

---

### **Instrumentation Architecture**

```
HTTP Request
    ↓
[OBSERVABILITY MIDDLEWARE]
    ├─ Start Transaction (trace)
    ├─ Capture: IP, User-Agent, Timestamp
    └─ Store in Request Context
    ↓
[HANDLER]
    ├─ Extract transaction from context
    └─ Add metadata: endpoint, method
    ↓
[SERVICE LAYER]
    ├─ Extract transaction from context
    └─ Add metadata: user_id, tenant_id
    ↓
[REPOSITORY]
    ├─ Extract transaction from context
    └─ Add metadata: query, duration
    ↓
[DATABASE]
    └─ Record: query time, rows affected
    ↓
Return Response
    └─ End Transaction (complete trace)
```

---

### **Dynamic Configuration (Dev vs Prod)**

```python
import os

# Environment-based logging
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "development":
    # Unstructured, colorized, DEBUG level
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
else:
    # Structured JSON, INFO level
    import json_logging
    json_logging.init_fastapi(enable_json=True)
    logging.basicConfig(level=logging.INFO)
```

---

## 🔗 The Tooling Ecosystem

### **Two Routes**

```
OPEN-SOURCE ROUTE          vs.    PROPRIETARY ROUTE
(Complex, Free)                   (Simple, Paid)

Prometheus (metrics)              Datadog (all-in-one)
Loki (logs)                       New Relic (all-in-one)
Jaeger (traces)                   
Grafana (dashboard)               

Pros:                             Pros:
- Free                            - Simple setup
- Full control                    - Auto-managed
- Customizable                    - Support included

Cons:                             Cons:
- Complex setup                   - Expensive
- Requires DevOps expertise       - Vendor lock-in
- Must maintain infrastructure    - Less customization
```

---

### **Open-Source Stack (ELK + Prometheus)**

```
┌──────────────────────────────────────────┐
│    OPEN-SOURCE OBSERVABILITY STACK       │
├──────────────────────────────────────────┤
│                                          │
│  LOGS:                                   │
│    Promtail (collector)                  │
│      ↓                                   │
│    Loki (storage/search)                 │
│      ↓                                   │
│    Grafana (visualization)               │
│                                          │
│  METRICS:                                │
│    Prometheus (collector/storage)        │
│      ↓                                   │
│    Grafana (visualization)               │
│                                          │
│  TRACES:                                 │
│    Jaeger (collector/storage)            │
│      ↓                                   │
│    Grafana (visualization)               │
│                                          │
└──────────────────────────────────────────┘
```

**Alternative for Logs:** ELK Stack
- **E**lasticsearch (storage)
- **L**ogstash (parsing)
- **K**ibana (visualization)

---

### **Proprietary Solutions**

**Datadog:**
- Unified platform
- Logs + Metrics + Traces + APM
- Auto-instrumentation
- Built-in alerts

**New Relic:**
- Application Performance Monitoring (APM)
- Real-time dashboards
- AI-powered insights
- Distributed tracing

**Advantages:**
- Single vendor, single UI
- Automatic setup
- Managed infrastructure
- Support team

**Cost:** $$$$ (worth it if lacking DevOps resources)

---

## 🔗 FastAPI Documentation Mapping

| Your Lecture Concept | FastAPI/Python Feature | Documentation | Notes |
|---------------------|----------------------|---------------|-------|
| **Logging** | `logging` module | [Python Logging](https://docs.python.org/3/library/logging.html) | Standard library |
| **Structured Logging** | `python-json-logger` | [JSON Logging](https://github.com/madzak/python-json-logger) | Production format |
| **Log Levels** | `logging.DEBUG/INFO/WARN/ERROR` | [Log Levels](https://docs.python.org/3/library/logging.html#levels) | Severity hierarchy |
| **Request Context** | `contextvars` | [Context Variables](https://docs.python.org/3/library/contextvars.html) | Thread-safe context |
| **Middleware Logging** | Custom middleware | [FastAPI Middleware](https://fastapi.tiangolo.com/tutorial/middleware/) | Log all requests |
| **OpenTelemetry** | `opentelemetry-api` | [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/) | Industry standard |
| **Tracing** | `opentelemetry-instrumentation-fastapi` | [FastAPI Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html) | Auto-instrumentation |
| **Metrics** | `prometheus-fastapi-instrumentator` | [Prometheus FastAPI](https://github.com/trallnag/prometheus-fastapi-instrumentator) | Prometheus metrics |
| **Health Checks** | Custom endpoint | [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/) | Monitor dependencies |

### **Key FastAPI Logging Patterns**

**Pattern 1: Basic Logging**
```python
import logging

logger = logging.getLogger(__name__)

@app.post("/todos")
def create_todo(todo: TodoCreate):
    logger.info(f"Creating todo: {todo.title}")
    # ... business logic
    logger.info(f"Todo created successfully: {todo.id}")
```

**Pattern 2: Structured Logging (Production)**
```python
import logging
import json_logging

# Initialize JSON logging
json_logging.init_fastapi(enable_json=True)
json_logging.init_request_instrument(app)

logger = logging.getLogger(__name__)

@app.post("/todos")
def create_todo(todo: TodoCreate):
    logger.info("Todo created", extra={
        "user_id": current_user.id,
        "todo_id": new_todo.id,
        "todo_title": todo.title
    })
```
Output (JSON):
```json
{
  "timestamp": "2024-01-29T10:30:15Z",
  "level": "INFO",
  "message": "Todo created",
  "user_id": 123,
  "todo_id": 456,
  "todo_title": "Buy milk"
}
```

**Pattern 3: Request Logging Middleware**
```python
import time
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        logger.info("Request completed", extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration * 1000
        })
        
        return response

app.add_middleware(LoggingMiddleware)
```

**Pattern 4: OpenTelemetry Tracing**
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracer
tracer = trace.get_tracer(__name__)

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

@app.post("/todos")
def create_todo(todo: TodoCreate):
    # Manual span for custom tracking
    with tracer.start_as_current_span("create_todo") as span:
        span.set_attribute("user_id", current_user.id)
        span.set_attribute("todo_title", todo.title)
        
        # Business logic
        new_todo = create_todo_in_db(todo)
        
        span.set_attribute("todo_id", new_todo.id)
        return new_todo
```

**Pattern 5: Prometheus Metrics**
```python
from prometheus_fastapi_instrumentator import Instrumentator

# Initialize Prometheus
Instrumentator().instrument(app).expose(app)

# Access metrics at /metrics endpoint
# Example metrics:
# - http_requests_total
# - http_request_duration_seconds
# - http_requests_in_progress
```

---

## 🎓 Mastery Checklist

- [ ] Understand the spectrum: Logging → Monitoring → Observability?
- [ ] Explain the 5 log levels (DEBUG, INFO, WARN, ERROR, FATAL)?
- [ ] Differentiate structured vs unstructured logs?
- [ ] Implement structured JSON logging in production?
- [ ] Never log sensitive data (passwords, keys, PII)?
- [ ] Understand the three pillars (Logs, Metrics, Traces)?
- [ ] Explain the debugging workflow (Alert → Metrics → Logs → Traces)?
- [ ] Instrument code with OpenTelemetry?
- [ ] Set up logging middleware in FastAPI?
- [ ] Implement request correlation (request_id)?
- [ ] Choose between open-source vs proprietary tools?
- [ ] Understand dynamic configuration (dev vs prod)?

---

## 📍 Observability in the Architecture

```
HTTP Request
    ↓
[Observability Middleware]
    ├─ Generate request_id
    ├─ Start trace (transaction)
    ├─ Log: Request received
    └─ Store context
    ↓
[Handler]
    ├─ Extract context
    ├─ Add span: "handler"
    └─ Log: Endpoint called
    ↓
[Service Layer]
    ├─ Extract context
    ├─ Add span: "business_logic"
    └─ Log: Service invoked
    ↓
[Repository]
    ├─ Extract context
    ├─ Add span: "database_query"
    └─ Log: Query executed
    ↓
[Database]
    └─ Record: query_time, rows
    ↓
Return Response
    ├─ End trace
    ├─ Log: Request completed
    └─ Metrics: duration, status_code
```

**Result:** Complete visibility into every request!

---

**Last Updated**: 2026-01-29  
**Status**: ✅ Mapping Complete  
**Practice File**: logging_observability_complete.py (next)
