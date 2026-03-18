"""
Complete Graceful Shutdown - FastAPI
Demonstrates all concepts from Lecture 19:

1. Signal handling (SIGTERM, SIGINT)
2. Connection draining
3. Shutdown timeout
4. Resource cleanup (reverse order)
5. Database connection cleanup
6. Background task cancellation
7. File handle cleanup
8. Logging shutdown progress
9. Modern lifespan context manager

Run with:
  fastapi dev graceful_shutdown_complete.py
  
Test shutdown:
  # Terminal 1: Start server
  fastapi dev graceful_shutdown_complete.py
  
  # Terminal 2: Send SIGTERM
  kill -TERM $(pgrep -f graceful_shutdown_complete)
  
  # Or just Ctrl+C (SIGINT)

Install:
  pip install "fastapi[standard]" sqlalchemy redis
"""

from fastapi import FastAPI, Request, BackgroundTasks
from contextlib import asynccontextmanager
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import asyncio
import signal
import time
import logging
from datetime import datetime
from typing import Set
import os

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL STATE (RESOURCES TO CLEAN UP)
# ============================================================================

class AppState:
    """
    Global application state
    
    Tracks resources that need cleanup on shutdown
    """
    def __init__(self):
        self.db_engine = None
        self.SessionLocal = None
        self.redis_client = None
        self.background_tasks: Set[asyncio.Task] = set()
        self.open_files = []
        self.is_shutting_down = False
        self.active_requests = 0

app_state = AppState()

# ============================================================================
# DATABASE SETUP
# ============================================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///./shutdown_demo.db"
Base = declarative_base()

class OrderModel(Base):
    """Order model (simulates e-commerce)"""
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Integer)
    status = Column(String, default="pending")

# ============================================================================
# SIMULATED EXTERNAL SERVICES
# ============================================================================

class FakeRedisClient:
    """Simulated Redis client"""
    def __init__(self):
        self.connected = False
        logger.info("Redis client created")
    
    def connect(self):
        self.connected = True
        logger.info("✅ Redis connected")
    
    def close(self):
        if self.connected:
            self.connected = False
            logger.info("✅ Redis connection closed")

# ============================================================================
# BACKGROUND WORKER
# ============================================================================

async def background_worker():
    """
    Simulated background worker
    
    Runs continuously until cancelled
    Must be cancelled on shutdown!
    """
    logger.info("Background worker started")
    
    try:
        while True:
            logger.info("Background worker: processing task...")
            await asyncio.sleep(5)
            
    except asyncio.CancelledError:
        logger.info("✅ Background worker cancelled gracefully")
    except Exception as e:
        logger.error(f"Background worker error: {e}")

# ============================================================================
# LIFESPAN CONTEXT MANAGER (MODERN APPROACH)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    LIFESPAN CONTEXT MANAGER
    
    Modern FastAPI approach for startup/shutdown
    
    Advantages:
    - More explicit about resource lifecycle
    - Automatic cleanup on exit
    - Cleaner than separate startup/shutdown events
    
    Resource Lifecycle:
    1. STARTUP (before yield): Acquire resources
    2. YIELD: Application runs
    3. SHUTDOWN (after yield): Release resources
    """
    # ========================================================================
    # STARTUP: ACQUIRE RESOURCES
    # ========================================================================
    
    logger.info("🚀 STARTUP: Initializing resources...")
    
    # 1. Initialize database
    logger.info("1/4 - Initializing database...")
    app_state.db_engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_size=10,
        max_overflow=20
    )
    Base.metadata.create_all(bind=app_state.db_engine)
    app_state.SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=app_state.db_engine
    )
    logger.info("   ✅ Database initialized")
    
    # 2. Connect to Redis
    logger.info("2/4 - Connecting to Redis...")
    app_state.redis_client = FakeRedisClient()
    app_state.redis_client.connect()
    logger.info("   ✅ Redis connected")
    
    # 3. Start background workers
    logger.info("3/4 - Starting background workers...")
    task = asyncio.create_task(background_worker())
    app_state.background_tasks.add(task)
    logger.info("   ✅ Background workers started")
    
    # 4. Open log file (simulated resource)
    logger.info("4/4 - Opening file handles...")
    log_file = open("app.log", "a")
    app_state.open_files.append(log_file)
    log_file.write(f"{datetime.now()} - Application started\n")
    log_file.flush()
    logger.info("   ✅ File handles opened")
    
    logger.info("✅ STARTUP COMPLETE - Application ready")
    
    # ========================================================================
    # YIELD: APPLICATION RUNS
    # ========================================================================
    
    yield  # Application runs here
    
    # ========================================================================
    # SHUTDOWN: RELEASE RESOURCES (REVERSE ORDER!)
    # ========================================================================
    
    logger.info("🛑 SHUTDOWN: Graceful shutdown initiated...")
    logger.info("   Signal received: SIGTERM or SIGINT")
    
    app_state.is_shutting_down = True
    
    # Step 1: Stop accepting new connections
    logger.info("Step 1/6 - Stop accepting new connections")
    logger.info("   ✅ New requests will receive 503")
    
    # Step 2: Wait for active requests to finish
    logger.info(f"Step 2/6 - Waiting for {app_state.active_requests} active requests...")
    timeout = 30  # 30 second timeout
    start = time.time()
    
    while app_state.active_requests > 0:
        if time.time() - start > timeout:
            logger.warning(f"   ⚠️  Timeout reached! Forcefully terminating {app_state.active_requests} requests")
            break
        await asyncio.sleep(0.1)
    
    if app_state.active_requests == 0:
        logger.info("   ✅ All active requests completed")
    
    # Step 3: Cancel background tasks
    logger.info("Step 3/6 - Cancelling background tasks...")
    for task in app_state.background_tasks:
        task.cancel()
    
    # Wait for cancellation
    await asyncio.gather(*app_state.background_tasks, return_exceptions=True)
    logger.info("   ✅ Background tasks cancelled")
    
    # Step 4: Close external connections (Redis)
    logger.info("Step 4/6 - Closing external connections...")
    if app_state.redis_client:
        app_state.redis_client.close()
    logger.info("   ✅ External connections closed")
    
    # Step 5: Close database connections
    logger.info("Step 5/6 - Closing database connections...")
    if app_state.db_engine:
        app_state.db_engine.dispose()
    logger.info("   ✅ Database connections closed")
    
    # Step 6: Close file handles
    logger.info("Step 6/6 - Closing file handles...")
    for file in app_state.open_files:
        if not file.closed:
            file.write(f"{datetime.now()} - Application shutdown\n")
            file.close()
    logger.info("   ✅ File handles closed")
    
    logger.info("✅ GRACEFUL SHUTDOWN COMPLETE")
    logger.info("   Application can now exit safely")

# ============================================================================
# FASTAPI APP WITH LIFESPAN
# ============================================================================

app = FastAPI(
    title="Graceful Shutdown Complete Example",
    description="Production-grade shutdown handling",
    version="1.0.0",
    lifespan=lifespan  # Attach lifespan context manager
)

# ============================================================================
# MIDDLEWARE: TRACK ACTIVE REQUESTS
# ============================================================================

@app.middleware("http")
async def track_requests(request: Request, call_next):
    """
    Track active requests
    
    Important for connection draining:
    - Increment on request start
    - Decrement on request end
    - Block new requests during shutdown
    """
    # Check if shutting down
    if app_state.is_shutting_down:
        return {"error": "Server is shutting down"}, 503
    
    # Increment active requests
    app_state.active_requests += 1
    logger.debug(f"Active requests: {app_state.active_requests}")
    
    try:
        response = await call_next(request)
        return response
    finally:
        # Decrement active requests
        app_state.active_requests -= 1
        logger.debug(f"Active requests: {app_state.active_requests}")

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Graceful Shutdown Complete API",
        "documentation": "/docs",
        "test_shutdown": "Press Ctrl+C or send SIGTERM to test",
        "endpoints": {
            "long_request": "GET /long-request (simulates slow request)",
            "create_order": "POST /orders (simulates e-commerce)",
            "health": "GET /health"
        },
        "shutdown_features": {
            "signal_handling": "SIGTERM, SIGINT",
            "connection_draining": "30s timeout",
            "resource_cleanup": "Database, Redis, files, tasks",
            "reverse_order_cleanup": True,
            "zero_data_loss": True
        }
    }

@app.get("/long-request")
async def long_request():
    """
    LONG REQUEST SIMULATION
    
    Use to test connection draining:
    1. Start this request
    2. Send SIGTERM
    3. Server waits for this to finish (up to 30s timeout)
    """
    logger.info("Long request started (10 seconds)")
    
    for i in range(10):
        await asyncio.sleep(1)
        logger.info(f"   Long request progress: {i+1}/10")
    
    logger.info("Long request completed")
    
    return {
        "message": "Long request completed",
        "duration_seconds": 10,
        "note": "If shutdown was triggered, server waited for this to finish"
    }

@app.post("/orders")
def create_order(user_id: int, amount: int):
    """
    CREATE ORDER (E-COMMERCE SIMULATION)
    
    Demonstrates why graceful shutdown matters:
    - Without it: Order might be lost during deployment
    - With it: Order is committed before shutdown
    
    Critical for:
    - Payment processing
    - Order creation
    - Any transactional operation
    """
    logger.info(f"Creating order: user_id={user_id}, amount={amount}")
    
    # Get database session
    db = app_state.SessionLocal()
    
    try:
        # Create order
        order = OrderModel(user_id=user_id, amount=amount, status="pending")
        db.add(order)
        
        # Simulate processing time
        time.sleep(2)
        
        # Commit transaction
        order.status = "completed"
        db.commit()
        db.refresh(order)
        
        logger.info(f"Order created successfully: order_id={order.id}")
        
        return {
            "order_id": order.id,
            "user_id": user_id,
            "amount": amount,
            "status": "completed",
            "note": "If shutdown happens during this, graceful shutdown ensures transaction commits"
        }
        
    finally:
        db.close()

@app.get("/health")
def health():
    """
    HEALTH CHECK
    
    Returns 503 during shutdown
    Load balancer should remove from rotation
    """
    if app_state.is_shutting_down:
        return {"status": "shutting_down"}, 503
    
    return {
        "status": "healthy",
        "active_requests": app_state.active_requests,
        "background_tasks": len(app_state.background_tasks),
        "database": "connected" if app_state.db_engine else "disconnected",
        "redis": "connected" if app_state.redis_client and app_state.redis_client.connected else "disconnected"
    }

# ============================================================================
# ALTERNATIVE: OLD-STYLE STARTUP/SHUTDOWN EVENTS
# ============================================================================

# Note: These are commented out because we're using lifespan context manager
# But this shows the old approach for reference

"""
@app.on_event("startup")
async def startup_event():
    '''
    OLD-STYLE STARTUP EVENT
    
    Use lifespan context manager instead (more modern)
    '''
    logger.info("Startup event triggered")
    # Initialize resources...

@app.on_event("shutdown")
async def shutdown_event():
    '''
    OLD-STYLE SHUTDOWN EVENT
    
    Use lifespan context manager instead (more modern)
    
    This is automatically called on:
    - SIGTERM received
    - SIGINT received (Ctrl+C)
    '''
    logger.info("Shutdown event triggered")
    # Clean up resources...
"""

# ============================================================================
# MANUAL SIGNAL HANDLING (ADVANCED)
# ============================================================================

def setup_signal_handlers():
    """
    MANUAL SIGNAL HANDLING (Advanced)
    
    FastAPI/Uvicorn already handles signals automatically,
    but this shows how to add custom logic.
    
    Use case: Additional cleanup beyond FastAPI lifecycle
    """
    def handle_sigterm(signum, frame):
        logger.info("🛑 SIGTERM received manually")
        # FastAPI will handle actual shutdown
        # This is just for logging/alerting
    
    def handle_sigint(signum, frame):
        logger.info("🛑 SIGINT received manually (Ctrl+C)")
        # FastAPI will handle actual shutdown
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigint)
    
    logger.info("✅ Custom signal handlers registered")

# Uncomment to enable custom signal handlers
# setup_signal_handlers()

# ============================================================================
# TEST INSTRUCTIONS
# ============================================================================
"""
SETUP:
  pip install "fastapi[standard]" sqlalchemy

RUN:
  fastapi dev graceful_shutdown_complete.py

TEST GRACEFUL SHUTDOWN:

1. Basic Shutdown (Ctrl+C):
   # Terminal 1: Start server
   fastapi dev graceful_shutdown_complete.py
   
   # Press Ctrl+C
   # Watch logs: See graceful shutdown in action

2. Long Request + Shutdown:
   # Terminal 1: Start server
   fastapi dev graceful_shutdown_complete.py
   
   # Terminal 2: Start long request
   curl http://localhost:8000/long-request
   
   # Terminal 1: Press Ctrl+C immediately
   # Watch: Server waits for request to finish!

3. SIGTERM (Production Deployment):
   # Terminal 1: Start server
   fastapi dev graceful_shutdown_complete.py
   
   # Terminal 2: Send SIGTERM
   kill -TERM $(pgrep -f graceful_shutdown_complete)
   
   # Watch logs: Same as Ctrl+C

4. Multiple Active Requests:
   # Terminal 1: Start server
   
   # Terminal 2-5: All start long requests simultaneously
   curl http://localhost:8000/long-request &
   curl http://localhost:8000/long-request &
   curl http://localhost:8000/long-request &
   curl http://localhost:8000/long-request &
   
   # Terminal 1: Press Ctrl+C
   # Watch: Server waits for ALL requests (30s timeout)

5. E-commerce Order (Transaction Safety):
   # Terminal 1: Start server
   
   # Terminal 2: Create order
   curl -X POST "http://localhost:8000/orders?user_id=123&amount=5000"
   
   # Terminal 1: Press Ctrl+C during order creation
   # Result: Transaction still commits before shutdown ✅

KEY INSIGHTS:

Graceful Shutdown Flow:
  1. SIGTERM/SIGINT received
  2. Stop accepting new connections (503)
  3. Wait for active requests (30s timeout)
  4. Cancel background tasks
  5. Close external connections (Redis)
  6. Close database connections
  7. Close file handles
  8. Exit cleanly (exit code 0)

Resource Cleanup Order (CRITICAL!):
  REVERSE ORDER of acquisition!
  
  Startup:
    1. Database
    2. Redis
    3. Background worker
    4. HTTP server
  
  Shutdown (REVERSE!):
    1. HTTP server (stop accepting)
    2. Background worker (cancel)
    3. Redis (close)
    4. Database (close)

Why It Matters:
  ❌ Without: Lost transactions, corrupted data, memory leaks
  ✅ With: Zero data loss, clean deployments, happy customers

Signals:
  SIGTERM: Polite request (can intercept)
  SIGINT: Ctrl+C (can intercept)
  SIGKILL: Nuclear option (cannot intercept)

Timeout:
  30s default - enough for most requests
  Force shutdown if exceeded
  Prevents deployment hanging forever

Real-World Impact:
  E-commerce: Don't lose $500 payment during deploy
  Banking: Don't corrupt transaction
  User data: Don't lose form submission
  
  Result: Zero-downtime deployments ✅
"""