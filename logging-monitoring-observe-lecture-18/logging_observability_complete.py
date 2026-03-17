"""
Complete Logging, Monitoring & Observability - FastAPI
Demonstrates all concepts from Lecture 18:

1. Log levels (DEBUG, INFO, WARN, ERROR, FATAL)
2. Structured vs unstructured logging
3. Development vs production configuration
4. Request correlation (request_id)
5. Logging middleware
6. Never log sensitive data
7. OpenTelemetry tracing
8. Prometheus metrics
9. The three pillars (Logs, Metrics, Traces)
10. Complete debugging workflow

Run with:
  # Development (unstructured logs)
  ENVIRONMENT=development fastapi dev logging_observability_complete.py
  
  # Production (structured JSON logs)
  ENVIRONMENT=production fastapi dev logging_observability_complete.py

Visit:
  http://localhost:8000/docs
  http://localhost:8000/metrics (Prometheus)

Install:
  pip install "fastapi[standard]" sqlalchemy python-json-logger \
              prometheus-fastapi-instrumentator opentelemetry-api \
              opentelemetry-sdk opentelemetry-instrumentation-fastapi
"""

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import logging
import json
import time
import os
import uuid
from datetime import datetime
from typing import Optional
from contextvars import ContextVar

# ============================================================================
# ENVIRONMENT DETECTION
# ============================================================================

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
IS_DEVELOPMENT = ENVIRONMENT == "development"

# ============================================================================
# LOGGING CONFIGURATION (DYNAMIC BASED ON ENVIRONMENT)
# ============================================================================

if IS_PRODUCTION:
    """
    PRODUCTION: Structured JSON Logging
    
    - Format: JSON (machine-parseable)
    - Level: INFO (reduce noise)
    - Output: stdout (collected by log aggregator)
    - Tools: ELK stack / Loki can parse and search
    """
    import pythonjsonlogger.jsonlogger
    
    logHandler = logging.StreamHandler()
    formatter = pythonjsonlogger.jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    logHandler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logHandler]
    )
    
    print("📋 PRODUCTION MODE: Structured JSON logging enabled")
    
else:
    """
    DEVELOPMENT: Unstructured Console Logging
    
    - Format: Plain text (human-readable, colorized)
    - Level: DEBUG (see everything)
    - Output: console
    - Tools: Your eyes 👀
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("🔧 DEVELOPMENT MODE: Unstructured console logging enabled")

logger = logging.getLogger(__name__)

# ============================================================================
# REQUEST CONTEXT (CORRELATION ID)
# ============================================================================

# Thread-safe context variable for request_id
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

def get_request_id() -> str:
    """Get current request ID from context"""
    return request_id_context.get()

# ============================================================================
# OPENTELEMETRY TRACING SETUP
# ============================================================================

# Set up tracer provider
trace.set_tracer_provider(TracerProvider())

# Add console exporter (for demo - in prod use OTLP exporter)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

# Get tracer
tracer = trace.get_tracer(__name__)

# ============================================================================
# DATABASE SETUP
# ============================================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///./observability_demo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TodoModel(Base):
    """Todo database model"""
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    user_id = Column(Integer)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    user_id: int = Field(..., gt=0)

class TodoResponse(BaseModel):
    id: int
    title: str
    description: str
    user_id: int
    
    class Config:
        from_attributes = True

# ============================================================================
# LOGGING MIDDLEWARE (REQUEST/RESPONSE LOGGING)
# ============================================================================

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    OBSERVABILITY MIDDLEWARE
    
    Responsibilities:
    1. Generate unique request_id (correlation)
    2. Start trace/transaction
    3. Log request received
    4. Measure request duration
    5. Log response sent
    6. Store metadata in context
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request_id_context.set(request_id)
        
        # Start timing
        start_time = time.time()
        
        # Log request received
        logger.info(
            "Request received",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response sent
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Add request_id to response headers (for client debugging)
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": round(duration_ms, 2),
                    "timestamp": datetime.utcnow().isoformat()
                },
                exc_info=True
            )
            
            raise

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Logging, Monitoring & Observability Complete API",
    description="Production-grade observability patterns",
    version="1.0.0"
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Initialize Prometheus instrumentator
# Exposes metrics at /metrics endpoint
Instrumentator().instrument(app).expose(app)

logger.info("✅ Prometheus metrics enabled at /metrics")

# ============================================================================
# OPENTELEMETRY AUTO-INSTRUMENTATION
# ============================================================================

# Auto-instrument FastAPI (traces all requests)
FastAPIInstrumentor.instrument_app(app)

logger.info("✅ OpenTelemetry auto-instrumentation enabled")

# ============================================================================
# LOG LEVELS DEMONSTRATION
# ============================================================================

@app.get("/demo/log-levels")
def demonstrate_log_levels():
    """
    LOG LEVELS DEMONSTRATION
    
    5 severity levels:
    - DEBUG: Detailed troubleshooting (dev only)
    - INFO: Successful operations
    - WARN: Non-critical issues
    - ERROR: Significant failures
    - CRITICAL/FATAL: Catastrophic bugs
    """
    request_id = get_request_id()
    
    # DEBUG: Detailed troubleshooting (only in dev)
    logger.debug(
        "Debug level log (very detailed)",
        extra={"request_id": request_id, "details": "function args, variables"}
    )
    
    # INFO: Normal operations
    logger.info(
        "Info level log (successful operation)",
        extra={"request_id": request_id, "operation": "log_levels_demo"}
    )
    
    # WARNING: Non-critical issues
    logger.warning(
        "Warning level log (non-critical issue)",
        extra={"request_id": request_id, "issue": "User typed wrong password"}
    )
    
    # ERROR: Significant failures
    logger.error(
        "Error level log (significant failure)",
        extra={"request_id": request_id, "error": "Database query failed"}
    )
    
    # CRITICAL: Catastrophic (rarely used)
    # logger.critical("Critical level log (app shutting down)")
    
    return {
        "message": "Log levels demonstrated",
        "request_id": request_id,
        "environment": ENVIRONMENT,
        "levels": {
            "DEBUG": "Detailed troubleshooting (dev only)",
            "INFO": "Successful operations",
            "WARNING": "Non-critical issues",
            "ERROR": "Significant failures",
            "CRITICAL": "Catastrophic bugs"
        },
        "note": "Check server logs to see output"
    }

# ============================================================================
# SECURE LOGGING (NEVER LOG SENSITIVE DATA)
# ============================================================================

@app.post("/demo/secure-logging")
def demonstrate_secure_logging(password: str, credit_card: str, api_key: str):
    """
    SECURE LOGGING DEMONSTRATION
    
    NEVER LOG:
    - Passwords
    - API keys
    - Credit card numbers
    - SSNs
    - Session tokens
    - Any PII
    
    If you must reference them, use masked versions.
    """
    request_id = get_request_id()
    
    # ❌ WRONG: Never log sensitive data
    # logger.info(f"Password: {password}")
    # logger.info(f"Credit card: {credit_card}")
    
    # ✅ CORRECT: Log event without sensitive data
    logger.info(
        "User authentication attempt",
        extra={
            "request_id": request_id,
            "user_id": 123,  # OK to log
            "auth_method": "password",  # OK to log
            # "password": password,  # NEVER!
        }
    )
    
    # ✅ CORRECT: Masked sensitive data (if must reference)
    logger.info(
        "Payment processed",
        extra={
            "request_id": request_id,
            "user_id": 123,
            "card_last4": credit_card[-4:],  # Only last 4 digits
            "api_key_prefix": api_key[:10] + "...",  # Only prefix
        }
    )
    
    return {
        "message": "Secure logging demonstrated",
        "request_id": request_id,
        "warning": "Never log passwords, keys, cards in real code!",
        "best_practices": {
            "never_log": ["passwords", "api_keys", "credit_cards", "ssns"],
            "ok_to_log": ["user_ids", "request_ids", "timestamps", "event_types"],
            "masked_ok": ["card_last4", "api_key_prefix"]
        }
    }

# ============================================================================
# STRUCTURED LOGGING WITH METADATA
# ============================================================================

@app.post("/todos", response_model=TodoResponse, status_code=201)
def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
    """
    CREATE TODO - With Complete Instrumentation
    
    Demonstrates:
    1. Structured logging with rich metadata
    2. Request correlation (request_id)
    3. OpenTelemetry tracing
    4. Business metric logging
    """
    request_id = get_request_id()
    
    # Start custom span (trace)
    with tracer.start_as_current_span("create_todo") as span:
        # Add attributes to span
        span.set_attribute("user_id", todo.user_id)
        span.set_attribute("todo_title", todo.title)
        span.set_attribute("request_id", request_id)
        
        # Log: Operation started
        logger.info(
            "Creating todo",
            extra={
                "request_id": request_id,
                "user_id": todo.user_id,
                "todo_title": todo.title,
                "operation": "create_todo",
                "step": "started"
            }
        )
        
        # Database operation
        start_db = time.time()
        db_todo = TodoModel(**todo.dict())
        db.add(db_todo)
        db.commit()
        db.refresh(db_todo)
        db_duration = (time.time() - start_db) * 1000
        
        # Add DB metrics to span
        span.set_attribute("db_duration_ms", db_duration)
        span.set_attribute("todo_id", db_todo.id)
        
        # Log: Database operation completed
        logger.info(
            "Todo created in database",
            extra={
                "request_id": request_id,
                "user_id": todo.user_id,
                "todo_id": db_todo.id,
                "db_duration_ms": round(db_duration, 2),
                "operation": "create_todo",
                "step": "db_completed"
            }
        )
        
        # Log: Operation completed (success metric)
        logger.info(
            "Todo created successfully",
            extra={
                "request_id": request_id,
                "user_id": todo.user_id,
                "todo_id": db_todo.id,
                "todo_title": todo.title,
                "operation": "create_todo",
                "step": "completed",
                "status": "success"
            }
        )
        
        return db_todo

@app.get("/todos/{todo_id}", response_model=TodoResponse)
def get_todo(todo_id: int, db: Session = Depends(get_db)):
    """
    GET TODO - With Error Logging
    
    Demonstrates logging for both success and error cases
    """
    request_id = get_request_id()
    
    with tracer.start_as_current_span("get_todo") as span:
        span.set_attribute("todo_id", todo_id)
        span.set_attribute("request_id", request_id)
        
        logger.debug(
            "Fetching todo from database",
            extra={
                "request_id": request_id,
                "todo_id": todo_id,
                "operation": "get_todo"
            }
        )
        
        todo = db.query(TodoModel).filter(TodoModel.id == todo_id).first()
        
        if not todo:
            # Log: Not found (warning level, not error - user's fault)
            logger.warning(
                "Todo not found",
                extra={
                    "request_id": request_id,
                    "todo_id": todo_id,
                    "operation": "get_todo",
                    "status": "not_found"
                }
            )
            
            span.set_attribute("status", "not_found")
            
            raise HTTPException(status_code=404, detail="Todo not found")
        
        logger.info(
            "Todo fetched successfully",
            extra={
                "request_id": request_id,
                "todo_id": todo_id,
                "user_id": todo.user_id,
                "operation": "get_todo",
                "status": "success"
            }
        )
        
        span.set_attribute("status", "success")
        span.set_attribute("user_id", todo.user_id)
        
        return todo

# ============================================================================
# ERROR LOGGING
# ============================================================================

@app.get("/demo/error")
def demonstrate_error_logging():
    """
    ERROR LOGGING DEMONSTRATION
    
    Shows how errors are automatically logged by middleware
    and can include custom context
    """
    request_id = get_request_id()
    
    try:
        # Simulate error
        raise ValueError("Simulated error for demonstration")
        
    except ValueError as e:
        # Log error with context
        logger.error(
            "Demonstration error occurred",
            extra={
                "request_id": request_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "endpoint": "/demo/error",
                "user_id": 123  # Would come from auth
            },
            exc_info=True  # Include stack trace
        )
        
        # Re-raise or handle
        raise HTTPException(
            status_code=500,
            detail="Demonstration error (check logs for details)"
        )

# ============================================================================
# METRICS ENDPOINT (PROMETHEUS)
# ============================================================================

# Prometheus metrics automatically exposed at /metrics by Instrumentator
# Includes:
# - http_requests_total
# - http_request_duration_seconds
# - http_requests_in_progress
# - And more...

@app.get("/demo/metrics-info")
def metrics_info():
    """
    Information about Prometheus metrics
    """
    return {
        "message": "Prometheus metrics available",
        "endpoint": "/metrics",
        "metrics_available": [
            "http_requests_total (counter)",
            "http_request_duration_seconds (histogram)",
            "http_requests_in_progress (gauge)",
            "http_request_size_bytes (histogram)",
            "http_response_size_bytes (histogram)"
        ],
        "usage": "curl http://localhost:8000/metrics",
        "tools": [
            "Prometheus (scraper)",
            "Grafana (visualization)"
        ]
    }

# ============================================================================
# THE THREE PILLARS DEMONSTRATION
# ============================================================================

@app.get("/demo/three-pillars")
def demonstrate_three_pillars():
    """
    THE THREE PILLARS OF OBSERVABILITY
    
    1. LOGS: What happened
    2. METRICS: How many/how fast
    3. TRACES: Where in the flow
    """
    request_id = get_request_id()
    
    with tracer.start_as_current_span("three_pillars_demo") as span:
        # PILLAR 1: LOGS
        logger.info(
            "Demonstrating three pillars",
            extra={
                "request_id": request_id,
                "pillar": "logs",
                "answer": "WHAT happened"
            }
        )
        
        # PILLAR 2: METRICS (tracked automatically by Prometheus)
        # Metrics answer: HOW MANY requests, HOW FAST
        
        # PILLAR 3: TRACES (this span)
        span.set_attribute("pillar", "traces")
        span.set_attribute("answer", "WHERE in the flow")
        
        return {
            "three_pillars": {
                "1_logs": {
                    "purpose": "Tell you WHAT happened",
                    "example": "User created todo item",
                    "format": "JSON in production",
                    "tools": "ELK stack, Loki"
                },
                "2_metrics": {
                    "purpose": "Provide NUMBERS (trends, patterns)",
                    "example": "Error rate: 85%, Response time: 500ms",
                    "format": "Time series data",
                    "tools": "Prometheus, Grafana",
                    "endpoint": "/metrics"
                },
                "3_traces": {
                    "purpose": "Track ENTIRE request lifecycle",
                    "example": "Handler → Service → DB (2500ms slow!)",
                    "format": "Distributed traces",
                    "tools": "Jaeger, Tempo",
                    "current_span": str(span.get_span_context())
                }
            },
            "request_id": request_id,
            "note": "Check logs, /metrics, and span output"
        }

# ============================================================================
# DEBUGGING WORKFLOW SIMULATION
# ============================================================================

@app.get("/demo/debugging-workflow")
def debugging_workflow():
    """
    COMPLETE DEBUGGING WORKFLOW
    
    Simulates the workflow:
    1. Alert (something's wrong)
    2. Metrics (how bad is it)
    3. Logs (what's the error)
    4. Traces (where did it fail)
    """
    return {
        "debugging_workflow": {
            "step_1_alert": {
                "trigger": "Slack notification: API error rate > 80%",
                "action": "Check monitoring dashboard"
            },
            "step_2_metrics": {
                "dashboard": "Grafana",
                "findings": [
                    "Error rate: 85% (spiked from 1%)",
                    "p95 latency: 5000ms (was 200ms)",
                    "DB connections: 50/50 (pool exhausted!)"
                ],
                "action": "Search logs for errors"
            },
            "step_3_logs": {
                "query": "level=ERROR AND timestamp > last_5_min",
                "findings": [
                    "ConnectionTimeout: Database pool exhausted",
                    "1,250 errors with request_id pattern req-abc-*"
                ],
                "action": "View trace for specific request"
            },
            "step_4_traces": {
                "request": "req-abc-123",
                "trace_breakdown": [
                    "Handler: 5ms ✅",
                    "Service: 10ms ✅",
                    "Database Query: 2500ms ❌ BOTTLENECK!",
                    "Response: 5ms ✅"
                ],
                "diagnosis": "Database connection pool exhausted",
                "solution": "Increase pool size OR optimize slow query"
            }
        },
        "time_to_resolution": {
            "with_observability": "5 minutes",
            "without_observability": "Hours of guessing"
        }
    }

# ============================================================================
# ROOT
# ============================================================================

@app.get("/")
def root():
    return {
        "message": "Logging, Monitoring & Observability Complete API",
        "documentation": "/docs",
        "environment": ENVIRONMENT,
        "logging": {
            "format": "JSON (structured)" if IS_PRODUCTION else "Console (unstructured)",
            "level": "INFO" if IS_PRODUCTION else "DEBUG"
        },
        "endpoints": {
            "log_levels": "GET /demo/log-levels",
            "secure_logging": "POST /demo/secure-logging",
            "create_todo": "POST /todos",
            "get_todo": "GET /todos/{id}",
            "error_demo": "GET /demo/error",
            "metrics": "GET /metrics (Prometheus)",
            "three_pillars": "GET /demo/three-pillars",
            "debugging_workflow": "GET /demo/debugging-workflow"
        },
        "observability_features": {
            "structured_logging": IS_PRODUCTION,
            "request_correlation": True,
            "opentelemetry_tracing": True,
            "prometheus_metrics": True,
            "secure_logging": True
        },
        "key_concepts": {
            "logs": "WHAT happened (detailed events)",
            "metrics": "HOW MANY/FAST (numbers, trends)",
            "traces": "WHERE in flow (request lifecycle)"
        }
    }

# ============================================================================
# TEST COMMANDS
# ============================================================================
"""
SETUP:
  pip install "fastapi[standard]" sqlalchemy python-json-logger \
              prometheus-fastapi-instrumentator opentelemetry-api \
              opentelemetry-sdk opentelemetry-instrumentation-fastapi

RUN:
  # Development mode (console logs, DEBUG level)
  ENVIRONMENT=development fastapi dev logging_observability_complete.py
  
  # Production mode (JSON logs, INFO level)
  ENVIRONMENT=production fastapi dev logging_observability_complete.py

TESTS:

1. View log levels:
   curl http://localhost:8000/demo/log-levels
   
   # Watch server logs - see all 5 levels

2. Test structured logging (create todo):
   curl -X POST http://localhost:8000/todos \
     -H "Content-Type: application/json" \
     -d '{"title":"Buy milk","description":"From the store","user_id":123}'
   
   # Check logs - see rich metadata (request_id, user_id, duration, etc.)

3. View Prometheus metrics:
   curl http://localhost:8000/metrics
   
   # See metrics like:
   # - http_requests_total
   # - http_request_duration_seconds

4. Test error logging:
   curl http://localhost:8000/demo/error
   
   # Check logs - see error with stack trace

5. Compare dev vs prod logging:
   # Terminal 1: Dev mode
   ENVIRONMENT=development fastapi dev logging_observability_complete.py
   curl http://localhost:8000/todos
   # Logs: Human-readable console format
   
   # Terminal 2: Prod mode
   ENVIRONMENT=production fastapi dev logging_observability_complete.py
   curl http://localhost:8000/todos
   # Logs: JSON format (machine-parseable)

6. View three pillars:
   curl http://localhost:8000/demo/three-pillars

7. Understand debugging workflow:
   curl http://localhost:8000/demo/debugging-workflow

KEY INSIGHTS:

The Spectrum:
  Logging → Monitoring → Observability
  (Recording) (Tracking) (Understanding)

Log Levels:
  DEBUG: Detailed (dev only)
  INFO: Success events
  WARN: Non-critical issues
  ERROR: Significant failures
  CRITICAL: Catastrophic bugs

Development vs Production:
  Dev: Console logs, DEBUG level, human-readable
  Prod: JSON logs, INFO level, machine-parseable

Never Log:
  ❌ Passwords
  ❌ API keys
  ❌ Credit card numbers
  ❌ SSNs
  ❌ Session tokens

Always Log:
  ✅ User IDs
  ✅ Request IDs
  ✅ Timestamps
  ✅ Event types
  ✅ Durations
  ✅ Status codes

The Three Pillars:
  1. Logs: WHAT happened (detailed events)
  2. Metrics: HOW MANY/FAST (numbers, trends)
  3. Traces: WHERE (request lifecycle)

Debugging Workflow:
  Alert → Metrics (dashboard) → Logs (search) → Traces (root cause)
  
  With observability: 5 minutes to fix
  Without: Hours of guessing

Tools:
  Open-source: Prometheus + Loki + Jaeger + Grafana
  Proprietary: Datadog, New Relic (simpler, paid)

Request Correlation:
  request_id links logs, metrics, traces for same request
  Essential for distributed systems
"""
