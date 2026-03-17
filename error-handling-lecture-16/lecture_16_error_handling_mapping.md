# Lecture 16: Error Handling & Fault-Tolerant Systems - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Error Handling & Building Fault-Tolerant Systems  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Core Philosophy from Your Lecture

> **"Errors are not problems to solve — they are an inevitable part of building applications."**

### **The Fault-Tolerant Mindset**

Accept that:
- Databases **will** fail
- External APIs **will** time out
- Users **will** send bad data
- Networks **will** partition

**Prepare strategies to detect and gracefully handle these scenarios.**

---

## 🎯 The 5 Types of Backend Errors

### **1. Logic Errors** ⚠️ MOST DANGEROUS

**What:** Code runs without crashing but produces **incorrect business results**

**Why Dangerous:** 
- No error message
- No crash
- Silent corruption of business logic
- Often discovered by users or accountants

**Examples:**
```python
# ❌ LOGIC ERROR: Discount applied twice
def calculate_total(price, discount_code):
    discounted = price * 0.9  # 10% off
    if discount_code == "SAVE10":
        discounted = discounted * 0.9  # Another 10% off!
    return discounted  # User gets 19% off instead of 10%!

# ❌ LOGIC ERROR: Wrong comparison
def is_adult(age):
    return age > 18  # Should be >= 18 (18-year-olds rejected!)

# ❌ LOGIC ERROR: Edge case not handled
def divide_reward(total_points, num_users):
    return total_points / num_users  # Crashes if num_users = 0!
```

**Prevention:**
- Thorough testing (unit tests, integration tests)
- Code reviews
- Business logic validation
- Edge case analysis

---

### **2. Database Errors**

**Types:**

**a) Connection Errors**
```python
# Pool exhausted (too many connections)
# Network partition (DB unreachable)
# Timeout (query too slow)
```

**b) Constraint Violations**
```python
# Unique constraint: Email already exists
# Foreign key: Order references non-existent customer
# NOT NULL: Required field missing
# Check constraint: Age < 0
```

**c) Query Errors**
```python
# SQL syntax error (typo in query)
# Deadlock (two transactions waiting on each other)
# Table doesn't exist
```

**FastAPI Handling:**
```python
from sqlalchemy.exc import IntegrityError, OperationalError

try:
    db.add(user)
    db.commit()
except IntegrityError as e:
    # Unique constraint violation
    if "unique constraint" in str(e).lower():
        raise HTTPException(status_code=400, detail="Email already exists")
    raise
except OperationalError:
    # Database connection issue
    raise HTTPException(status_code=503, detail="Database temporarily unavailable")
```

---

### **3. External Service Errors**

**Modern apps depend on third parties:**
- Payment processors (Stripe)
- Email providers (SendGrid)
- Auth providers (Auth0)
- SMS services (Twilio)
- Cloud storage (S3)

**Common Failures:**

**a) Network Issues**
```python
# Connection timeout
# DNS resolution failure
# SSL certificate error
```

**b) Service Outages**
```python
# 500 Internal Server Error from API
# 503 Service Unavailable
# Complete downtime
```

**c) Rate Limiting**
```python
# 429 Too Many Requests
# Daily quota exceeded
# Burst limit hit
```

**Strategy: Retry with Exponential Backoff**
```python
import time

def call_external_api_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            return response.json()
        except requests.Timeout:
            if attempt == max_retries - 1:
                raise HTTPException(503, "External service timeout")
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait_time)
```

---

### **4. Input Validation Errors** ✅ EASIEST TO HANDLE

**What:** User sends bad data

**When:** 
- Missing required fields
- Wrong data type
- Out of range values
- Invalid format

**Where to catch:** At the **entry point** (handler/controller)

**FastAPI Automatic Validation:**
```python
from pydantic import BaseModel, Field, field_validator

class UserCreate(BaseModel):
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    age: int = Field(..., ge=0, le=150)
    password: str = Field(..., min_length=8)
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v):
        if not v.endswith(('@gmail.com', '@company.com')):
            raise ValueError('Email must be from allowed domains')
        return v

# FastAPI automatically returns 422 Unprocessable Entity with details!
```

**Return Code:** `400 Bad Request` or `422 Unprocessable Entity`

---

### **5. Configuration Errors**

**What:** Missing or invalid environment variables

**Examples:**
- Missing `DATABASE_URL`
- Missing `API_KEY`
- Invalid `JWT_SECRET`
- Wrong `REDIS_HOST`

**❌ BAD: Fail at runtime (when user hits endpoint)**
```python
@app.get("/send-email")
def send_email():
    api_key = os.getenv("SENDGRID_API_KEY")  # None!
    # Crashes when user tries to send email
```

**✅ GOOD: Fail at startup**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    sendgrid_api_key: str
    jwt_secret: str
    
    class Config:
        env_file = ".env"

# Load settings at startup - app won't start if missing
settings = Settings()

# Or manual check
@app.on_event("startup")
def validate_config():
    required = ["DATABASE_URL", "SENDGRID_API_KEY", "JWT_SECRET"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing}")
```

**Benefit:** Fail fast, fail loudly, fail at startup (not in production!)

---

## 🔍 Prevention & Proactive Detection

### **1. Advanced Health Checks**

**❌ BAD: Simple health check**
```python
@app.get("/health")
def health():
    return {"status": "ok"}  # Always returns 200!
```

**✅ GOOD: Deep health check**
```python
@app.get("/health")
def health(db: Session = Depends(get_db)):
    checks = {}
    
    # 1. Database connectivity
    try:
        db.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
    
    # 2. Redis connectivity
    try:
        redis_client.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
    
    # 3. External API reachability
    try:
        response = requests.get("https://api.stripe.com/healthcheck", timeout=2)
        checks["stripe"] = "healthy" if response.ok else "degraded"
    except Exception as e:
        checks["stripe"] = f"unhealthy: {str(e)}"
    
    # Overall status
    all_healthy = all("healthy" in status for status in checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }
```

---

### **2. Observability**

**Monitor three categories:**

**a) Error Rates**
```python
# Track 4xx and 5xx response counts
# Alert if error rate > 1%
# Alert if 500 errors spike suddenly
```

**b) Performance Metrics**
```python
# Response time (p50, p95, p99)
# Database query duration
# External API latency
# Alert if p95 > 500ms
```

**c) Business Metrics**
```python
# Successful transactions per minute
# Failed payment rate
# User signup rate
# Alert if drop > 20%
```

**Tools:**
- Prometheus + Grafana (metrics)
- Sentry (error tracking)
- Datadog (APM)
- ELK Stack (logs)

---

## 🛡️ Response & Recovery Strategies

### **1. Recoverable Errors: Retry Logic**

**When to retry:**
- Network timeouts
- Rate limiting (429)
- Temporary service unavailable (503)
- Transient database errors

**Exponential Backoff:**
```python
def retry_with_exponential_backoff(
    func,
    max_retries=3,
    base_delay=1
):
    for attempt in range(max_retries):
        try:
            return func()
        except (RequestTimeout, RateLimitError) as e:
            if attempt == max_retries - 1:
                raise  # Final attempt failed
            
            # Exponential backoff: 1s, 2s, 4s, 8s...
            delay = base_delay * (2 ** attempt)
            
            # Add jitter to prevent thundering herd
            jitter = random.uniform(0, delay * 0.1)
            time.sleep(delay + jitter)
```

**⚠️ Warning: Don't retry on:**
- 4xx errors (client fault, won't fix on retry)
- 500 errors from overloaded service (makes it worse!)
- Non-idempotent operations (e.g., charging credit card twice)

---

### **2. Non-Recoverable Errors: Graceful Degradation**

**When service is totally down:**

**Strategy 1: Use cached data**
```python
@app.get("/product/{id}")
def get_product(id: int):
    try:
        # Try live database
        product = fetch_from_database(id)
    except DatabaseError:
        # Fallback to cache
        product = fetch_from_cache(id)
        if not product:
            raise HTTPException(503, "Service temporarily unavailable")
    
    return product
```

**Strategy 2: Disable non-essential features**
```python
@app.get("/dashboard")
def dashboard():
    try:
        analytics = fetch_analytics()  # External service
    except ServiceError:
        analytics = {"message": "Analytics temporarily unavailable"}
    
    # Main dashboard still works, just without analytics
    return {
        "user": get_user(),
        "notifications": get_notifications(),
        "analytics": analytics  # May be error message
    }
```

**Strategy 3: Circuit Breaker**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"  # Try again
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func()
            if self.state == "half-open":
                self.state = "closed"  # Service recovered
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"  # Stop trying for timeout period
            raise
```

---

## 🌐 Global Error Handling Middleware

### **The Final Safety Net**

**Philosophy:**
- Catch errors in low-level code (repository, service)
- Add context
- Bubble up to global middleware
- Centralized formatting and logging

**FastAPI Implementation:**

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
import logging

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    GLOBAL ERROR HANDLER
    
    Catches all unhandled exceptions
    - Logs details internally
    - Returns safe message to client
    - Maps error types to HTTP status codes
    """
    
    # 1. Log full error internally (with context)
    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host,
            "error_type": type(exc).__name__
        },
        exc_info=True
    )
    
    # 2. Map to appropriate HTTP status
    if isinstance(exc, IntegrityError):
        # Database constraint violation
        if "unique constraint" in str(exc).lower():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Resource already exists"}
            )
        elif "foreign key" in str(exc).lower():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Referenced resource does not exist"}
            )
    
    elif isinstance(exc, OperationalError):
        # Database connection issue
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Service temporarily unavailable"}
        )
    
    elif isinstance(exc, ValueError):
        # Business logic validation
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}
        )
    
    # 3. Default: 500 with GENERIC message (no leak!)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"}
    )
```

**Benefits:**
- ✅ No error forgotten
- ✅ Consistent error format
- ✅ Centralized logging
- ✅ Security (no leaks)
- ✅ Less code duplication

---

## 🔒 Security Considerations

### **1. Sanitize Error Messages**

**❌ NEVER leak internal details:**
```python
# BAD: Exposes database structure
return {"error": "Column 'users.email' violates unique constraint"}

# BAD: Exposes file paths
return {"error": "/var/app/src/handlers/user.py line 42: IndexError"}

# BAD: Exposes SQL query
return {"error": "SELECT * FROM users WHERE id=5 FAILED"}
```

**✅ ALWAYS use generic messages:**
```python
# GOOD: Generic for client, detailed in logs
return {"error": "Something went wrong"}

# GOOD: Helpful but safe
return {"error": "Email already in use"}

# GOOD: Business-friendly
return {"error": "Unable to process request"}
```

---

### **2. Prevent Enumeration Attacks**

**❌ BAD: Reveals if email exists**
```python
@app.post("/login")
def login(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return {"error": "Email not found"}  # REVEALS EMAIL EXISTS!
    
    if not verify_password(password, user.password_hash):
        return {"error": "Incorrect password"}
```

**✅ GOOD: Ambiguous message**
```python
@app.post("/login")
def login(email: str, password: str):
    user = get_user_by_email(email)
    if not user or not verify_password(password, user.password_hash):
        return {"error": "Invalid email or password"}  # SAME MESSAGE!
    
    return {"token": create_token(user)}
```

---

### **3. Secure Logging**

**❌ NEVER log:**
```python
# BAD: Logs password
logger.info(f"User {user_id} logged in with password {password}")

# BAD: Logs API key
logger.info(f"Calling Stripe with key {stripe_api_key}")

# BAD: Logs credit card
logger.info(f"Processing payment for card {card_number}")
```

**✅ ALWAYS log safely:**
```python
# GOOD: Logs user ID only
logger.info(f"User {user_id} logged in successfully")

# GOOD: Masks sensitive data
logger.info(f"Calling Stripe with key {stripe_api_key[:10]}...")

# GOOD: Logs last 4 digits only
logger.info(f"Processing payment for card ending in {card_number[-4:]}")

# GOOD: Uses correlation ID
logger.info(f"Request {request_id} failed", extra={
    "user_id": user_id,
    "endpoint": "/api/payment",
    "error_type": "PaymentFailed"
})
```

---

## 📊 Error Handling Best Practices Summary

| Practice | Why | Example |
|----------|-----|---------|
| **Fail fast at startup** | Don't discover missing config in production | Validate env vars on app start |
| **Deep health checks** | Detect issues before users do | Test DB, Redis, external APIs |
| **Global error handler** | Consistent error handling | FastAPI exception_handler |
| **Retry with backoff** | Recover from transient failures | Network timeouts, rate limits |
| **Circuit breaker** | Prevent cascading failures | Stop calling dead service |
| **Graceful degradation** | Keep app running with reduced features | Use cached data, disable analytics |
| **Sanitize errors** | Security (no internal leak) | Generic 500 messages |
| **Ambiguous auth errors** | Prevent enumeration | "Invalid email or password" |
| **Secure logging** | Protect sensitive data | Never log passwords/keys |
| **Monitor everything** | Early detection | Error rates, latency, business metrics |

---

## 🔗 FastAPI Documentation Mapping

| Your Lecture Concept | FastAPI Feature | FastAPI Docs | Notes |
|---------------------|-----------------|--------------|-------|
| **Global Error Handler** | `@app.exception_handler()` | [Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/) | Catch all unhandled exceptions |
| **HTTPException** | `HTTPException` | [HTTPException](https://fastapi.tiangolo.com/tutorial/handling-errors/#use-httpexception) | Raise HTTP errors with status codes |
| **Custom Exception Handler** | Custom exception classes | [Custom Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers) | Handle specific error types |
| **Request Validation Errors** | `RequestValidationError` | [Override Request Validation Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/#override-request-validation-exceptions) | Customize Pydantic validation errors |
| **Startup Events** | `@app.on_event("startup")` | [Events: startup - shutdown](https://fastapi.tiangolo.com/advanced/events/) | Validate configs at startup |
| **Dependency Errors** | Dependencies with exceptions | [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/) | Handle errors in dependencies |
| **Background Task Errors** | BackgroundTasks error handling | [Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) | Handle async task failures |
| **Response Models** | `response_model` | [Response Model](https://fastapi.tiangolo.com/tutorial/response-model/) | Ensure correct response shape |
| **Status Codes** | `status_code` parameter | [Response Status Code](https://fastapi.tiangolo.com/tutorial/response-status-code/) | Set appropriate HTTP codes |
| **Middleware** | Custom middleware | [Middleware](https://fastapi.tiangolo.com/tutorial/middleware/) | Error logging, request tracking |

### **Key FastAPI Error Handling Patterns**

**Pattern 1: Global Exception Handler**
```python
from fastapi import Request, status
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log internally
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Return safe message to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"}
    )
```
[FastAPI Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/)

**Pattern 2: Specific Exception Types**
```python
from sqlalchemy.exc import IntegrityError

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Resource already exists"}
    )
```
[Custom Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers)

**Pattern 3: HTTPException**
```python
from fastapi import HTTPException

@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    return user
```
[Using HTTPException](https://fastapi.tiangolo.com/tutorial/handling-errors/#use-httpexception)

**Pattern 4: Validation Error Override**
```python
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(
        str(exc),
        status_code=422
    )
```
[Override Validation Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/#override-request-validation-exceptions)

**Pattern 5: Startup Validation**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str  # Required!
    api_key: str       # Required!

@app.on_event("startup")
def validate_startup():
    settings = Settings()  # Raises if missing
    logger.info("✅ Config validated")
```
[Startup Events](https://fastapi.tiangolo.com/advanced/events/#startup-event)

**Pattern 6: Dependency Error Handling**
```python
from fastapi import Depends

def get_db():
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        logger.error(f"DB error: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")
    finally:
        db.close()
```
[Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)

**Pattern 7: Middleware for Error Logging**
```python
from starlette.middleware.base import BaseHTTPMiddleware

class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Request failed: {e}", extra={
                "path": request.url.path,
                "method": request.method
            })
            raise
```
[Middleware](https://fastapi.tiangolo.com/tutorial/middleware/)

---

## 🎓 Mastery Checklist

- [ ] List the 5 types of backend errors?
- [ ] Explain why logic errors are most dangerous?
- [ ] Handle database constraint violations?
- [ ] Implement retry with exponential backoff?
- [ ] Build a circuit breaker?
- [ ] Create deep health check endpoint?
- [ ] Set up global error handler in FastAPI?
- [ ] Sanitize error messages for security?
- [ ] Prevent authentication enumeration attacks?
- [ ] Log errors without leaking sensitive data?
- [ ] Implement graceful degradation?
- [ ] Validate config at startup?

---

**Last Updated**: 2026-01-29  
**Status**: ✅ Mapping Complete  
**Practice File**: error_handling_complete.py (next)