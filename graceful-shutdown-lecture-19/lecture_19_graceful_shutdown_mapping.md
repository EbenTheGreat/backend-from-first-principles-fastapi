# Lecture 19: Graceful Shutdown - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Graceful Shutdown - Teaching Your Backend Good Manners  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Core Philosophy from Your Lecture

> **"A graceful shutdown is teaching your backend application 'good manners' when it needs to restart or deploy new code."**

### **The Problem: Abrupt Shutdown**

**❌ Without graceful shutdown:**
```
New deployment triggered
    ↓
Server killed instantly (SIGKILL)
    ↓
CONSEQUENCES:
- Lost e-commerce payments 💸
- Double-charged customers 💳
- Corrupted database transactions 🗄️
- Lost user data 📝
- Orphaned connections 🔌
- Memory leaks 💾
```

**✅ With graceful shutdown:**
```
New deployment triggered
    ↓
Server receives SIGTERM (polite request)
    ↓
Stop accepting new connections
    ↓
Finish processing current requests (30-60s timeout)
    ↓
Clean up resources (DB, files, connections)
    ↓
Shut down cleanly
    ↓
RESULT: Zero data loss, zero corruption ✨
```

---

## 📡 1. Understanding OS Signals

### **What Are Signals?**

> **"Signals are an established communication protocol between the operating system and your application."**

**Your backend runs as a process on Linux/Unix.**  
**The OS controls its lifecycle using signals.**

---

### **The Three Key Signals**

#### **SIGTERM (Signal Terminate)** - The Polite Request

**Who sends it:** Deployment systems (Kubernetes, PM2, systemd)

**What it means:** "Please finish up and shut down"

**Can be intercepted:** ✅ YES

**Your responsibility:** Handle gracefully

```python
import signal

def handle_sigterm(signum, frame):
    print("SIGTERM received - initiating graceful shutdown")
    # Stop accepting connections
    # Finish current requests
    # Clean up resources
    # Exit

signal.signal(signal.SIGTERM, handle_sigterm)
```

---

#### **SIGINT (Signal Interrupt)** - The Manual Request

**Who sends it:** Developer pressing `Ctrl+C` in terminal

**What it means:** "Please stop"

**Can be intercepted:** ✅ YES

**Your responsibility:** Same as SIGTERM (identical handling)

```python
import signal

def handle_sigint(signum, frame):
    print("SIGINT received (Ctrl+C) - initiating graceful shutdown")
    # Same logic as SIGTERM

signal.signal(signal.SIGINT, handle_sigint)
```

**Rule:** SIGTERM and SIGINT should trigger **identical** graceful shutdown logic!

---

#### **SIGKILL** - The Nuclear Option

**Who sends it:** OS (if app ignores SIGTERM too long)

**What it means:** "Die NOW"

**Can be intercepted:** ❌ NO (by design!)

**Timing:** Sent after ~30 seconds if SIGTERM ignored

```
SIGTERM sent → Wait 30s → SIGKILL (instant death)
```

**Result:** Process killed instantly, no cleanup possible

**Lesson:** ALWAYS handle SIGTERM properly to avoid SIGKILL!

---

### **Signal Flow in Production**

```
DEPLOYMENT TRIGGERED
    ↓
Kubernetes sends SIGTERM to pod
    ↓
[YOUR CODE] Receives SIGTERM
    ├─ Stop accepting new connections
    ├─ Wait for current requests (max 30s)
    └─ Clean up resources
    ↓
[YOUR CODE] Exits cleanly (exit code 0)
    ↓
Kubernetes starts new pod
    ↓
ZERO DOWNTIME DEPLOYMENT ✅

vs.

DEPLOYMENT WITHOUT GRACEFUL SHUTDOWN
    ↓
Kubernetes sends SIGTERM
    ↓
[YOUR CODE] Ignores it (no handler!)
    ↓
After 30s: SIGKILL (instant death)
    ↓
Active requests lost 💀
Database transactions corrupted 💀
Connections orphaned 💀
```

---

## 🔄 2. Connection Draining - The Restaurant Analogy

### **The Restaurant Closing Process**

> **"Like a restaurant closing for the night — finish serving current customers, but don't let new ones in."**

```
9:00 PM - Restaurant Open
    ├─ Accepting new customers ✅
    └─ Serving existing customers ✅

9:55 PM - Kitchen Closing Soon (SIGTERM received)
    ├─ STOP accepting new customers ❌ (lock the door)
    └─ CONTINUE serving existing customers ✅

10:00 PM - Kitchen Closed
    ├─ All existing customers served ✅
    └─ Restaurant shuts down ✅
```

---

### **In Backend Terms**

```
NORMAL OPERATION
    ├─ Accept new HTTP connections ✅
    └─ Process existing requests ✅

SIGTERM RECEIVED (graceful shutdown triggered)
    ├─ STOP accepting new connections ❌
    │   └─ Return 503 Service Unavailable to new requests
    │
    └─ FINISH existing connections ✅
        └─ Wait for in-flight requests to complete

TIMEOUT (30-60 seconds)
    ├─ If all requests finished → shut down cleanly ✅
    └─ If requests still running → force shutdown ⚠️
        └─ Log warning: "Forcefully terminated N requests"
```

---

### **The Timeout Limit**

**Why needed:** Can't wait forever (deployment must complete)

**Typical values:**
- **30 seconds:** Standard (most requests finish quickly)
- **60 seconds:** For long-running operations
- **120 seconds:** Only for batch jobs/reports

**What happens on timeout:**
```python
# After 30 seconds
if requests_still_running:
    logger.warning(f"Forcefully terminating {count} requests")
    # Close connections
    # Exit anyway
```

**Best practice:** Set timeout based on your longest typical request duration + buffer.

---

## 🧹 3. Resource Cleanup

### **What Needs Cleaning?**

```
Resources Acquired During Runtime:
├─ Database connections (TCP sockets)
├─ Redis connections
├─ File handles (open files)
├─ Network sockets (HTTP connections)
├─ Background tasks (threads, workers)
├─ Message queue connections (RabbitMQ, Redis)
└─ Temporary files
```

**If NOT cleaned up:**
- **Memory leaks** (RAM never freed)
- **File descriptor leaks** (OS runs out of handles)
- **Database deadlocks** (connections never closed)
- **Orphaned processes** (workers keep running)

---

### **The Golden Rule of Cleanup**

> **"Resources must be cleaned up in the REVERSE order of how they were acquired."**

**Why?** Don't terminate foundation that dependent operations need!

**Example:**

```
STARTUP ORDER:
1. Initialize database connection pool
2. Start background worker (uses database)
3. Start HTTP server (uses database + worker)

SHUTDOWN ORDER (REVERSE!):
1. Stop HTTP server (stop accepting requests)
2. Stop background worker (finish tasks)
3. Close database connections (after worker done)
```

**❌ Wrong order:**
```python
# BAD: Close database first
db.close()
# Worker still trying to use database → ERROR!
worker.stop()
```

**✅ Correct order:**
```python
# GOOD: Stop dependents first
worker.stop()  # Stop using database
db.close()     # Then close database
```

---

### **Cleanup Checklist**

```python
def cleanup():
    """
    GRACEFUL SHUTDOWN CLEANUP
    
    Order matters: Stop dependents before dependencies!
    """
    logger.info("Starting cleanup...")
    
    # 1. Stop accepting new work
    http_server.stop_accepting_connections()
    
    # 2. Finish current work (with timeout)
    http_server.wait_for_requests(timeout=30)
    
    # 3. Stop background workers
    celery_worker.stop()
    background_tasks.cancel()
    
    # 4. Close external connections
    redis_client.close()
    message_queue.disconnect()
    
    # 5. Commit/rollback database transactions
    for session in active_sessions:
        if session.in_transaction():
            session.rollback()  # Or commit if safe
    
    # 6. Close database connections
    db_pool.close_all()
    
    # 7. Close file handles
    for file in open_files:
        file.close()
    
    # 8. Clean up temporary files
    temp_dir.cleanup()
    
    logger.info("✅ Cleanup complete - shutting down")
```

---

## 💻 FastAPI Implementation

### **FastAPI Lifecycle Events**

FastAPI provides built-in events for startup and shutdown:

```python
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """
    STARTUP: Initialize resources
    """
    # Initialize database pool
    db.connect()
    
    # Start background tasks
    scheduler.start()
    
    logger.info("✅ Application started")

@app.on_event("shutdown")
async def shutdown_event():
    """
    SHUTDOWN: Clean up resources
    
    Automatically called when:
    - SIGTERM received
    - SIGINT received (Ctrl+C)
    """
    logger.info("🛑 Shutdown signal received - cleaning up...")
    
    # Stop accepting new connections (automatic)
    
    # Finish current requests (automatic, with timeout)
    
    # Clean up resources (YOUR code)
    scheduler.stop()
    db.close_all()
    
    logger.info("✅ Cleanup complete")
```

**FastAPI automatically handles:**
- ✅ Signal interception (SIGTERM, SIGINT)
- ✅ Stop accepting new connections
- ✅ Wait for current requests (with timeout)
- ✅ Call shutdown event handlers

**You must handle:**
- ⚠️ Resource cleanup (database, files, connections)
- ⚠️ Background task cancellation
- ⚠️ Transaction commit/rollback

---

## 🔗 FastAPI Documentation Mapping

| Your Lecture Concept | FastAPI Feature | FastAPI Docs | Notes |
|---------------------|-----------------|--------------|-------|
| **Graceful Shutdown** | Automatic signal handling | [Events: startup - shutdown](https://fastapi.tiangolo.com/advanced/events/) | Built-in SIGTERM/SIGINT handling |
| **Shutdown Event** | `@app.on_event("shutdown")` | [Shutdown Events](https://fastapi.tiangolo.com/advanced/events/#shutdown-event) | Clean up resources |
| **Startup Event** | `@app.on_event("startup")` | [Startup Events](https://fastapi.tiangolo.com/advanced/events/#startup-event) | Initialize resources |
| **Lifespan Context** | `lifespan` parameter (new) | [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/#lifespan-events) | Modern async context manager |
| **Background Tasks** | `BackgroundTasks` | [Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) | Cancel on shutdown |
| **Database Cleanup** | Custom shutdown logic | [SQL Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/) | Close connections |
| **Signal Handling** | Built into Uvicorn | [Deployment](https://fastapi.tiangolo.com/deployment/concepts/) | Automatic |

---

### **Pattern 1: Basic Shutdown Handler**

```python
from fastapi import FastAPI

app = FastAPI()

@app.on_event("shutdown")
async def shutdown():
    """
    BASIC SHUTDOWN
    
    Called automatically on SIGTERM or SIGINT
    """
    print("Shutting down gracefully...")
    
    # Your cleanup code
    await cleanup_resources()
```

[FastAPI Shutdown Events](https://fastapi.tiangolo.com/advanced/events/#shutdown-event)

---

### **Pattern 2: Startup + Shutdown (Resource Lifecycle)**

```python
@app.on_event("startup")
async def startup():
    """STARTUP: Acquire resources"""
    app.state.db = create_database_pool()
    app.state.redis = create_redis_client()
    print("✅ Resources initialized")

@app.on_event("shutdown")
async def shutdown():
    """SHUTDOWN: Release resources (reverse order!)"""
    # Reverse order of acquisition
    await app.state.redis.close()
    await app.state.db.close()
    print("✅ Resources cleaned up")
```

---

### **Pattern 3: Lifespan Context Manager (Modern)**

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    LIFESPAN CONTEXT MANAGER (Modern FastAPI)
    
    Replaces separate startup/shutdown events
    More explicit about resource lifecycle
    """
    # STARTUP
    db = create_database_pool()
    redis = create_redis_client()
    
    yield {"db": db, "redis": redis}
    
    # SHUTDOWN (automatic cleanup)
    await redis.close()
    await db.close()

app = FastAPI(lifespan=lifespan)
```

[Lifespan Events](https://fastapi.tiangolo.com/advanced/events/#lifespan-events)

---

### **Pattern 4: Database Connection Cleanup**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@app.on_event("startup")
def startup():
    engine = create_engine(DATABASE_URL, pool_size=10)
    SessionLocal = sessionmaker(bind=engine)
    app.state.engine = engine

@app.on_event("shutdown")
def shutdown():
    """
    CRITICAL: Close database connections
    
    Prevents:
    - Connection leaks
    - Database deadlocks
    - Memory leaks
    """
    app.state.engine.dispose()
    print("✅ Database connections closed")
```

---

### **Pattern 5: Background Task Cancellation**

```python
import asyncio

background_tasks = set()

@app.on_event("startup")
async def startup():
    # Start background task
    task = asyncio.create_task(background_worker())
    background_tasks.add(task)

@app.on_event("shutdown")
async def shutdown():
    """
    CANCEL BACKGROUND TASKS
    
    Important: Don't leave workers running!
    """
    for task in background_tasks:
        task.cancel()
    
    # Wait for cancellation
    await asyncio.gather(*background_tasks, return_exceptions=True)
    
    print("✅ Background tasks cancelled")
```

---

## 🎓 Mastery Checklist

- [ ] Understand why graceful shutdown matters?
- [ ] Explain the difference between SIGTERM, SIGINT, and SIGKILL?
- [ ] Implement shutdown event handler in FastAPI?
- [ ] Stop accepting new connections on shutdown?
- [ ] Wait for current requests to finish?
- [ ] Set appropriate shutdown timeout?
- [ ] Clean up resources in reverse order?
- [ ] Close database connections properly?
- [ ] Cancel background tasks on shutdown?
- [ ] Commit or rollback pending transactions?
- [ ] Close file handles and network sockets?
- [ ] Log shutdown progress?

---

## 📍 Graceful Shutdown in Architecture

```
NORMAL OPERATION
    ↓
[SIGTERM/SIGINT Received]
    ↓
[FastAPI Shutdown Event Triggered]
    ↓
1. Stop Accepting New Connections
    └─ Return 503 to new requests
    ↓
2. Connection Draining (30s timeout)
    ├─ Finish current HTTP requests
    └─ Wait for in-flight operations
    ↓
3. Resource Cleanup (REVERSE ORDER!)
    ├─ Stop background workers
    ├─ Cancel async tasks
    ├─ Close Redis connections
    ├─ Commit/rollback transactions
    ├─ Close database connections
    └─ Close file handles
    ↓
4. Exit Cleanly (exit code 0)
    └─ OS can now start new version
    ↓
ZERO-DOWNTIME DEPLOYMENT ✅
```

---

## 🔥 Real-World Impact

### **Without Graceful Shutdown:**

```
E-commerce scenario:
1. User submits payment ($500)
2. Payment processor charged ✅
3. SIGKILL received (deployment)
4. Database transaction never committed ❌
5. Order lost, but customer charged 💸
6. Customer service nightmare 😱
```

### **With Graceful Shutdown:**

```
E-commerce scenario:
1. User submits payment ($500)
2. Payment processor charged ✅
3. SIGTERM received (deployment)
4. Server finishes request (30s timeout)
5. Database transaction committed ✅
6. Order recorded ✅
7. Customer happy ✅
8. Clean shutdown ✅
```

---

**Last Updated**: 2026-01-29  
**Status**: ✅ Mapping Complete  
**Practice File**: graceful_shutdown_complete.py (next)
