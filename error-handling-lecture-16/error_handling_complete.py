"""
Complete Error Handling & Fault-Tolerant Systems - FastAPI
Demonstrates all concepts from Lecture 16:

1. The 5 types of backend errors
2. Prevention & proactive detection
3. Retry mechanisms with exponential backoff
4. Circuit breaker pattern
5. Graceful degradation
6. Global error handling middleware
7. Security considerations
8. Deep health checks
9. Configuration validation

Run with: fastapi dev error_handling_complete.py
Visit: http://127.0.0.1:8000/docs

Install:
  pip install "fastapi[standard]" sqlalchemy redis requests pydantic-settings
"""

from fastapi import FastAPI, HTTPException, Request, status, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from sqlalchemy import Column, Integer, String, create_engine, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import Optional
import logging
import time
import random
import os
from datetime import datetime

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION VALIDATION (FAIL AT STARTUP)
# ============================================================================

class Settings(BaseSettings):
    """
    CONFIGURATION ERROR PREVENTION
    
    Using pydantic-settings ensures all required config exists AT STARTUP.
    
    ❌ BAD: Check config when endpoint is called (runtime failure)
    ✅ GOOD: Validate config at startup (fail fast)
    """
    database_url: str = "sqlite:///./error_demo.db"
    api_key: str = "demo-api-key-12345"
    jwt_secret: str = "super-secret-key"
    external_api_url: str = "https://httpbin.org"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# This will raise ValidationError if any required field is missing
try:
    settings = Settings()
    logger.info("✅ Configuration validated successfully")
except Exception as e:
    logger.error(f"❌ Configuration error: {e}")
    logger.error("Application will not start. Fix configuration and restart.")
    raise  # Fail fast!

# ============================================================================
# DATABASE SETUP
# ============================================================================

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserModel(Base):
    """User model with unique email constraint"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)  # Unique constraint!
    username = Column(String, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('email', name='uix_email'),
    )

class OrderModel(Base):
    """Order model with foreign key"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # Foreign key (not enforced in SQLite)
    amount = Column(Integer, nullable=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# CIRCUIT BREAKER PATTERN
# ============================================================================

class CircuitBreaker:
    """
    CIRCUIT BREAKER - Prevent cascading failures
    
    States:
    - CLOSED: Normal operation
    - OPEN: Service is down, reject immediately
    - HALF_OPEN: Testing if service recovered
    
    Prevents overwhelming a failing service with requests.
    """
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.success_count = 0
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            # Check if timeout expired
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker: OPEN → HALF_OPEN (testing recovery)")
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"Circuit breaker OPEN. Service unavailable. Try again in {int(self.timeout - (time.time() - self.last_failure_time))}s"
                )
        
        try:
            result = func(*args, **kwargs)
            
            if self.state == "HALF_OPEN":
                self.success_count += 1
                if self.success_count >= 3:  # 3 successes = recovered
                    self.state = "CLOSED"
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info("Circuit breaker: HALF_OPEN → CLOSED (service recovered)")
            
            return result
        
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker: CLOSED → OPEN (failures: {self.failure_count})")
            
            raise

# Global circuit breakers for external services
payment_circuit = CircuitBreaker(failure_threshold=5, timeout=60)
email_circuit = CircuitBreaker(failure_threshold=3, timeout=30)

# ============================================================================
# RETRY WITH EXPONENTIAL BACKOFF
# ============================================================================

def retry_with_exponential_backoff(
    func,
    max_retries=3,
    base_delay=1,
    max_delay=10,
    exceptions=(Exception,)
):
    """
    RETRY MECHANISM - Exponential Backoff
    
    Retry pattern:
    - Attempt 1: Immediate
    - Attempt 2: Wait 1s
    - Attempt 3: Wait 2s
    - Attempt 4: Wait 4s
    
    Adds jitter to prevent thundering herd problem.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except exceptions as e:
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} retry attempts failed: {e}")
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)
            
            # Add jitter (0-10% of delay) to prevent thundering herd
            jitter = random.uniform(0, delay * 0.1)
            total_delay = delay + jitter
            
            logger.warning(
                f"Attempt {attempt + 1} failed: {e}. "
                f"Retrying in {total_delay:.2f}s..."
            )
            time.sleep(total_delay)

# ============================================================================
# PYDANTIC MODELS WITH VALIDATION
# ============================================================================

class UserCreate(BaseModel):
    """
    INPUT VALIDATION ERROR PREVENTION
    
    Pydantic automatically validates:
    - Type checking
    - Required fields
    - Format validation
    - Range validation
    
    Returns 422 Unprocessable Entity automatically!
    """
    email: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        description="Valid email address"
    )
    username: str = Field(..., min_length=3, max_length=50)
    age: int = Field(..., ge=0, le=150, description="Age must be 0-150")
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v):
        """Custom validation: Only allow certain domains"""
        allowed_domains = ['gmail.com', 'yahoo.com', 'company.com']
        domain = v.split('@')[1]
        if domain not in allowed_domains:
            raise ValueError(f'Email must be from: {", ".join(allowed_domains)}')
        return v.lower()

class OrderCreate(BaseModel):
    user_id: int = Field(..., gt=0)
    amount: int = Field(..., gt=0, description="Amount in cents")

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Error Handling & Fault-Tolerant Systems",
    description="Complete implementation of all error handling patterns from Lecture 16",
    version="1.0.0"
)

# ============================================================================
# GLOBAL ERROR HANDLER - THE FINAL SAFETY NET
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    GLOBAL ERROR HANDLING MIDDLEWARE
    
    The final safety net - catches ALL unhandled exceptions.
    
    Responsibilities:
    1. Log error details internally (with context)
    2. Map error types to HTTP status codes
    3. Return sanitized message to client
    4. Never leak internal details
    """
    
    # 1. Log full error with context (internal only!)
    logger.error(
        f"Unhandled exception",
        extra={
            "error": str(exc),
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host,
        },
        exc_info=True  # Include stack trace
    )
    
    # 2. Map specific error types to HTTP status codes
    
    # DATABASE CONSTRAINT VIOLATIONS
    if isinstance(exc, IntegrityError):
        error_msg = str(exc).lower()
        
        if "unique constraint" in error_msg or "unique" in error_msg:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Resource already exists"}  # Generic, no leak!
            )
        
        if "foreign key" in error_msg:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Referenced resource does not exist"}
            )
        
        if "not null" in error_msg:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Required field missing"}
            )
    
    # DATABASE CONNECTION ISSUES
    if isinstance(exc, OperationalError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Service temporarily unavailable. Please try again."}
        )
    
    # BUSINESS LOGIC VALIDATION
    if isinstance(exc, ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}  # Safe - business validation message
        )
    
    # HTTP EXCEPTIONS (already handled by FastAPI)
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    # 3. Default: Generic 500 error (NEVER leak internal details!)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
            "request_id": id(request)  # For support to track in logs
        }
    )

# ============================================================================
# SECTION 1: THE 5 TYPES OF ERRORS
# ============================================================================

# TYPE 1: LOGIC ERRORS (Most Dangerous!)
@app.post("/demo/logic-error")
def logic_error_demo(price: int, discount_code: Optional[str] = None):
    """
    LOGIC ERROR DEMO - The Most Dangerous Type
    
    This code has a bug: discount applied twice!
    - User expects 10% off ($100 → $90)
    - Actually gets 19% off ($100 → $81)
    
    No crash, no error message - just wrong business logic!
    
    Prevention:
    - Thorough testing
    - Code reviews
    - Business logic validation
    """
    # ❌ BUG: Discount applied twice!
    discounted = price * 0.9  # 10% off
    
    if discount_code == "SAVE10":
        discounted = discounted * 0.9  # ANOTHER 10% off!
    
    return {
        "original_price": price,
        "final_price": discounted,
        "bug": "Discount applied twice! Should be $90, actually $81",
        "lesson": "Logic errors don't crash - they silently corrupt business logic"
    }

# TYPE 2: DATABASE ERRORS - Constraint Violations
@app.post("/demo/database-error")
def database_error_demo(email: str, username: str, db: Session = Depends(get_db)):
    """
    DATABASE ERROR DEMO - Constraint Violations
    
    Try creating user with duplicate email:
    - First call: Success
    - Second call: IntegrityError (unique constraint)
    
    Global error handler catches and converts to 400 Bad Request
    """
    user = UserModel(email=email, username=username)
    db.add(user)
    db.commit()  # Will raise IntegrityError if email exists
    db.refresh(user)
    
    return {
        "message": "User created",
        "user_id": user.id,
        "try_again": "Call with same email to trigger constraint violation"
    }

# TYPE 3: EXTERNAL SERVICE ERRORS - With Retry
@app.get("/demo/external-service-retry")
def external_service_with_retry():
    """
    EXTERNAL SERVICE ERROR - Retry with Exponential Backoff
    
    Simulates calling external API that might fail.
    Uses retry mechanism to handle transient failures.
    
    Try multiple times to see retry logic in action.
    """
    def call_external_api():
        # Simulate external API (50% failure rate)
        if random.random() < 0.5:
            raise ConnectionError("External API timeout")
        return {"data": "Success from external API"}
    
    try:
        result = retry_with_exponential_backoff(
            call_external_api,
            max_retries=3,
            exceptions=(ConnectionError,)
        )
        return {
            "status": "success",
            "result": result,
            "note": "Retry mechanism succeeded"
        }
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail="External service unavailable after 3 retries"
        )

# TYPE 4: INPUT VALIDATION ERRORS (Easiest to Handle!)
@app.post("/demo/validation-error")
def validation_error_demo(user: UserCreate):
    """
    INPUT VALIDATION ERROR - Automatic Validation
    
    Pydantic automatically validates:
    - Email format
    - Username length (3-50 chars)
    - Age range (0-150)
    - Email domain (gmail, yahoo, company only)
    
    Returns 422 Unprocessable Entity with detailed errors!
    
    Try:
    - Invalid email: "not-an-email"
    - Short username: "ab"
    - Invalid age: -5 or 200
    - Wrong domain: "user@hotmail.com"
    """
    return {
        "message": "Validation passed!",
        "user": user.dict(),
        "note": "All fields validated automatically by Pydantic"
    }

# TYPE 5: CONFIGURATION ERRORS (Already handled at startup!)
@app.get("/demo/config-validation")
def config_validation_demo():
    """
    CONFIGURATION ERROR - Validated at Startup
    
    Settings are validated when app starts using pydantic-settings.
    Missing env vars = app won't start!
    
    ✅ GOOD: Fail fast at startup
    ❌ BAD: Discover missing config in production
    """
    return {
        "message": "Configuration is valid",
        "settings": {
            "database_url": settings.database_url[:20] + "...",  # Partial
            "api_key": settings.api_key[:10] + "...",  # Partial
            "jwt_secret": "***hidden***"  # Never log secrets!
        },
        "note": "App would not have started if config was invalid"
    }

# ============================================================================
# SECTION 2: CIRCUIT BREAKER PATTERN
# ============================================================================

# Simulated failing service
failing_service_call_count = 0

@app.get("/demo/circuit-breaker")
def circuit_breaker_demo(force_fail: bool = False):
    """
    CIRCUIT BREAKER PATTERN
    
    Prevents cascading failures when external service is down.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Service down, reject immediately (no wasted calls)
    - HALF_OPEN: Testing if service recovered
    
    Try:
    1. Call with force_fail=true 5 times → Opens circuit
    2. Call again → Immediate rejection (no timeout!)
    3. Wait 60s, call again → Half-open (testing)
    4. Call succeeds 3x → Circuit closes
    """
    def simulated_payment_service():
        global failing_service_call_count
        failing_service_call_count += 1
        
        if force_fail:
            raise Exception("Payment service timeout")
        
        return {"status": "payment processed"}
    
    try:
        result = payment_circuit.call(simulated_payment_service)
        return {
            "status": "success",
            "result": result,
            "circuit_state": payment_circuit.state,
            "call_count": failing_service_call_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# ============================================================================
# SECTION 3: GRACEFUL DEGRADATION
# ============================================================================

# Simulated cache
analytics_cache = {"views": 1000, "clicks": 250, "cached_at": datetime.now()}

@app.get("/demo/graceful-degradation")
def graceful_degradation_demo(force_failure: bool = False):
    """
    GRACEFUL DEGRADATION
    
    When external service fails, use cached data instead of crashing.
    
    Flow:
    1. Try to fetch live analytics
    2. If fails → use cached data
    3. Main app still works!
    
    Try with force_failure=true to see fallback.
    """
    try:
        if force_failure:
            raise Exception("Analytics service timeout")
        
        # Simulate fetching live analytics
        analytics = {
            "views": 1234,
            "clicks": 567,
            "source": "live"
        }
    except Exception:
        # Fallback to cached data
        logger.warning("Analytics service failed, using cached data")
        analytics = {
            **analytics_cache,
            "source": "cache (analytics temporarily unavailable)"
        }
    
    return {
        "user": {"id": 1, "name": "Alice"},
        "notifications": {"count": 5},
        "analytics": analytics,
        "note": "Main dashboard works even if analytics fails!"
    }

# ============================================================================
# SECTION 4: DEEP HEALTH CHECKS
# ============================================================================

@app.get("/health/simple")
def simple_health_check():
    """
    ❌ BAD HEALTH CHECK
    
    Always returns 200 OK, even if database is down!
    Useless for monitoring.
    """
    return {"status": "ok"}

@app.get("/health/deep")
def deep_health_check(db: Session = Depends(get_db)):
    """
    ✅ GOOD HEALTH CHECK
    
    Actually tests critical dependencies:
    - Database connectivity
    - External APIs
    - Cache availability
    
    Returns 503 if any component is unhealthy.
    """
    checks = {}
    all_healthy = True
    
    # 1. Database check
    try:
        db.execute("SELECT 1")
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False
    
    # 2. External API check
    try:
        import requests
        response = requests.get(
            f"{settings.external_api_url}/status/200",
            timeout=2
        )
        checks["external_api"] = {
            "status": "healthy" if response.ok else "degraded"
        }
    except Exception as e:
        checks["external_api"] = {"status": "unhealthy", "error": str(e)}
        all_healthy = False
    
    # 3. Circuit breaker status
    checks["circuit_breakers"] = {
        "payment": payment_circuit.state,
        "email": email_circuit.state
    }
    
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "checks": checks
        }
    )

# ============================================================================
# SECTION 5: SECURITY - ERROR MESSAGE SANITIZATION
# ============================================================================

@app.post("/demo/login-bad")
def login_bad(email: str, password: str, db: Session = Depends(get_db)):
    """
    ❌ BAD: Enumeration Attack Vulnerability
    
    Reveals if email exists in database!
    Attacker can guess registered emails.
    
    Try:
    - Existing email: "alice@gmail.com" → "Incorrect password"
    - Non-existing email: "bob@gmail.com" → "Email not found"
    
    Attacker learns which emails are registered!
    """
    user = db.query(UserModel).filter(UserModel.email == email).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Email not found")  # ❌ REVEALS!
    
    # Simulate password check
    if password != "correct-password":
        raise HTTPException(status_code=401, detail="Incorrect password")  # ❌ REVEALS!
    
    return {"token": "fake-jwt-token"}

@app.post("/demo/login-good")
def login_good(email: str, password: str, db: Session = Depends(get_db)):
    """
    ✅ GOOD: Prevents Enumeration Attack
    
    Same message for all failures!
    Attacker cannot determine if email exists.
    
    Try:
    - Existing email + wrong password: "Invalid email or password"
    - Non-existing email: "Invalid email or password"
    
    Same message = no information leak!
    """
    user = db.query(UserModel).filter(UserModel.email == email).first()
    
    # Same message for both cases!
    if not user or password != "correct-password":
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"  # ✅ AMBIGUOUS!
        )
    
    return {"token": "fake-jwt-token"}

@app.get("/demo/error-leakage")
def error_leakage_demo(leak: bool = False):
    """
    ERROR MESSAGE SANITIZATION
    
    ❌ BAD: Leak internal details
    ✅ GOOD: Generic message to client, detailed in logs
    
    Try with leak=true vs leak=false
    """
    try:
        # Simulate error
        raise Exception("Database connection failed on server db-prod-01.internal:5432")
    except Exception as e:
        # Log internally (detailed)
        logger.error(f"Internal error: {e}")
        
        if leak:
            # ❌ BAD: Leak internal details to client
            raise HTTPException(status_code=500, detail=str(e))
        else:
            # ✅ GOOD: Generic message to client
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred"
            )

# ============================================================================
# SECTION 6: SECURE LOGGING
# ============================================================================

@app.post("/demo/logging-bad")
def logging_bad(email: str, password: str, credit_card: str):
    """
    ❌ BAD LOGGING - Security Violation
    
    NEVER log:
    - Passwords
    - API keys
    - Credit card numbers
    - SSNs
    - Session tokens
    
    This demo shows what NOT to do!
    """
    # ❌ BAD: Logs sensitive data
    logger.info(f"Login attempt: email={email}, password={password}")
    logger.info(f"Processing payment with card: {credit_card}")
    
    return {
        "warning": "This endpoint logs sensitive data (BAD!)",
        "check_logs": "See server logs for leaked data"
    }

@app.post("/demo/logging-good")
def logging_good(email: str, password: str, credit_card: str):
    """
    ✅ GOOD LOGGING - Secure
    
    Log:
    - User IDs (not emails)
    - Request IDs
    - Event types
    - Masked sensitive data
    
    DON'T log:
    - Passwords
    - Full credit card numbers
    - API keys
    """
    user_id = 123  # From authentication
    request_id = id(email)  # Generate unique ID
    
    # ✅ GOOD: Safe logging
    logger.info(f"Login attempt for user_id={user_id}, request_id={request_id}")
    logger.info(f"Payment processed for card ending in {credit_card[-4:]}")
    
    return {
        "message": "Logged securely",
        "user_id": user_id,
        "request_id": request_id,
        "note": "No sensitive data in logs!"
    }

# ============================================================================
# ROOT
# ============================================================================

@app.get("/")
def root():
    return {
        "message": "Error Handling & Fault-Tolerant Systems Complete API",
        "documentation": "/docs",
        "sections": {
            "1_logic_error": "POST /demo/logic-error",
            "2_database_error": "POST /demo/database-error",
            "3_external_retry": "GET /demo/external-service-retry",
            "4_validation": "POST /demo/validation-error",
            "5_config": "GET /demo/config-validation",
            "6_circuit_breaker": "GET /demo/circuit-breaker",
            "7_graceful_degradation": "GET /demo/graceful-degradation",
            "8_health_simple": "GET /health/simple",
            "9_health_deep": "GET /health/deep",
            "10_login_bad": "POST /demo/login-bad",
            "11_login_good": "POST /demo/login-good",
            "12_error_leak": "GET /demo/error-leakage",
            "13_logging_bad": "POST /demo/logging-bad",
            "14_logging_good": "POST /demo/logging-good"
        },
        "key_concepts": {
            "5_error_types": ["Logic", "Database", "External Service", "Input Validation", "Configuration"],
            "retry_pattern": "Exponential backoff with jitter",
            "circuit_breaker": "CLOSED → OPEN → HALF_OPEN",
            "graceful_degradation": "Fallback to cache when service fails",
            "global_handler": "Centralized error mapping and sanitization",
            "security": "Never leak internal details, prevent enumeration"
        }
    }

# ============================================================================
# SEED DATA
# ============================================================================

@app.on_event("startup")
def seed():
    db = SessionLocal()
    if db.query(UserModel).count() == 0:
        users = [
            UserModel(email="alice@gmail.com", username="alice"),
            UserModel(email="bob@yahoo.com", username="bob"),
        ]
        db.add_all(users)
        db.commit()
        logger.info("✅ Seeded sample users")
    db.close()

# ============================================================================
# TEST COMMANDS
# ============================================================================
"""
SETUP:
  pip install "fastapi[standard]" sqlalchemy pydantic-settings requests
  fastapi dev error_handling_complete.py
  Open: http://localhost:8000/docs

TEST ERROR TYPES:

1. Logic Error (silent bug):
   curl -X POST "http://localhost:8000/demo/logic-error?price=100&discount_code=SAVE10"
   # Returns $81 instead of $90!

2. Database Constraint Violation:
   # First call: succeeds
   curl -X POST "http://localhost:8000/demo/database-error?email=test@gmail.com&username=test"
   
   # Second call: triggers unique constraint error → global handler converts to 400
   curl -X POST "http://localhost:8000/demo/database-error?email=test@gmail.com&username=test2"

3. Retry with Exponential Backoff:
   # Call multiple times - see retry logic in logs
   curl http://localhost:8000/demo/external-service-retry

4. Input Validation (automatic):
   # Invalid email
   curl -X POST http://localhost:8000/demo/validation-error \
     -H "Content-Type: application/json" \
     -d '{"email":"not-an-email","username":"bob","age":25}'
   
   # Invalid age
   curl -X POST http://localhost:8000/demo/validation-error \
     -H "Content-Type: application/json" \
     -d '{"email":"bob@gmail.com","username":"bob","age":200}'

5. Circuit Breaker:
   # Trigger failures 5x to open circuit
   for i in {1..6}; do
     curl "http://localhost:8000/demo/circuit-breaker?force_fail=true"
   done
   # Now circuit is OPEN - immediate rejection!

6. Graceful Degradation:
   # Normal: live data
   curl http://localhost:8000/demo/graceful-degradation
   
   # Forced failure: cached data
   curl "http://localhost:8000/demo/graceful-degradation?force_failure=true"

7. Deep Health Check:
   curl http://localhost:8000/health/deep

8. Enumeration Attack:
   # BAD endpoint: reveals if email exists
   curl -X POST "http://localhost:8000/demo/login-bad?email=alice@gmail.com&password=wrong"
   # Returns: "Incorrect password" (reveals email exists!)
   
   # GOOD endpoint: same message always
   curl -X POST "http://localhost:8000/demo/login-good?email=alice@gmail.com&password=wrong"
   # Returns: "Invalid email or password" (no information leak)

KEY INSIGHTS:

The 5 Error Types:
  1. Logic Errors: Most dangerous (no crash, wrong results)
  2. Database Errors: Constraints, connections, deadlocks
  3. External Service: Timeouts, outages, rate limits
  4. Input Validation: Easiest (Pydantic handles automatically)
  5. Configuration: Catch at startup (fail fast)

Prevention:
  - Deep health checks (test DB, external APIs)
  - Config validation at startup
  - Monitoring (error rates, latency, business metrics)

Recovery:
  - Retry with exponential backoff (transient failures)
  - Circuit breaker (cascading failure prevention)
  - Graceful degradation (fallback to cache)

Global Error Handler:
  - Centralized error mapping
  - Consistent logging
  - Sanitized client messages
  - No internal detail leaks

Security:
  - Never leak database details
  - Prevent enumeration attacks (same message)
  - Secure logging (never log passwords/keys)
  - Generic 500 messages

The Mindset:
  "Errors are inevitable. Build systems that detect and handle them gracefully."
"""
