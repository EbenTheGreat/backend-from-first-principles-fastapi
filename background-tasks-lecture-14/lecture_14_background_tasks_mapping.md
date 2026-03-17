# Lecture 14: Background Tasks & Task Queues - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Background Tasks & Task Queues - Async Processing at Scale  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Core Concept from Your Lecture

> **"A background task is any piece of logic that runs outside the standard request-response lifecycle."**

### **The Problem: Synchronous Processing**

**Scenario:** User signs up → Send verification email

**❌ Synchronous (Bad):**
```python
@app.post("/signup")
def signup(user: UserCreate):
    # 1. Create user in database (50ms)
    create_user(user)
    
    # 2. Send email via external API (2-5 seconds!)
    send_email(user.email)  # BLOCKING! User waits!
    
    # 3. If email service is down → entire signup fails!
    return {"message": "Account created"}
```

**User Experience:**
- Waits 2-5 seconds staring at loading spinner
- If email service down → signup fails
- Must retry manually

**✅ Asynchronous (Good):**
```python
@app.post("/signup")
def signup(user: UserCreate, bg_tasks: BackgroundTasks):
    # 1. Create user (50ms)
    create_user(user)
    
    # 2. Queue email for background processing
    bg_tasks.add_task(send_email, user.email)
    
    # 3. Return immediately! (50ms total)
    return {"message": "Account created"}
```

**User Experience:**
- Instant response (50ms)
- If email service down → user doesn't notice, queue retries
- Email arrives in background

---

## 🏗️ Task Queue Architecture

### **The 3 Components**

```
┌─────────────────────────────────────────────────────────────┐
│                    TASK QUEUE SYSTEM                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. PRODUCER (Main API)                                       │
│     ├─ Gathers task data                                      │
│     ├─ Serializes to JSON                                     │
│     └─ Enqueues task                                          │
│                 ↓                                             │
│  2. BROKER (The Queue)                                        │
│     ├─ Redis / RabbitMQ / AWS SQS                            │
│     ├─ Temporary storage                                      │
│     └─ Holds tasks until processed                            │
│                 ↓                                             │
│  3. CONSUMER (Worker Process)                                 │
│     ├─ Separate process from API                              │
│     ├─ Monitors queue                                         │
│     ├─ Dequeues tasks                                         │
│     ├─ Deserializes data                                      │
│     └─ Executes handler                                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

### **Component Details**

#### **1. Producer (Your API)**
```python
# FastAPI handler
@app.post("/signup")
def signup(user: UserCreate, bg_tasks: BackgroundTasks):
    create_user(user)
    
    # Producer: Enqueue task
    bg_tasks.add_task(
        send_verification_email,  # Function to run
        user.email,               # Argument 1
        user.username             # Argument 2
    )
    
    return {"status": "success"}
```

**What happens:**
1. Gather data (email, username)
2. Serialize to JSON
3. Push to queue
4. Return immediately

---

#### **2. Broker (The Queue)**

**Common technologies:**
- **Redis** (recommended for small-medium scale)
- **RabbitMQ** (robust, enterprise-grade)
- **AWS SQS** (managed, serverless)
- **Celery + Redis** (Python standard)

**Responsibilities:**
- Store tasks temporarily
- Maintain order (FIFO)
- Handle visibility timeouts
- Track acknowledgements

---

#### **3. Consumer (Worker Process)**

**Separate process running continuously:**
```bash
# Start worker (separate from API)
celery -A app.celery worker --loglevel=info
```

**What it does:**
```python
# Worker loop (pseudocode)
while True:
    task = queue.dequeue()  # Pull next task
    
    if task:
        data = deserialize(task)
        handler = get_handler(task.name)
        
        try:
            handler(**data)  # Execute!
            queue.acknowledge(task)  # Mark complete
        except Exception as e:
            queue.retry(task)  # Re-queue for retry
```

---

## 🔄 Reliability Mechanisms

### **1. Retry with Exponential Backoff**

**Pattern:**
```
Attempt 1: Immediate
Attempt 2: Wait 1 minute
Attempt 3: Wait 2 minutes
Attempt 4: Wait 4 minutes
Attempt 5: Wait 8 minutes
...
```

**Why:** Give external service time to recover

**Implementation:**
```python
@celery.task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 5},
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600  # Max 10 minutes
)
def send_email(email, subject, body):
    # If this fails, Celery auto-retries with backoff
    external_email_api.send(email, subject, body)
```

---

### **2. Visibility Timeout & Acknowledgements**

**The Problem:** What if worker crashes mid-task?

**The Solution: Visibility Timeout**

```
1. Worker pulls task from queue
   → Task enters "visibility timeout" (invisible to other workers)
   → Timer starts (e.g., 30 minutes)

2a. Worker succeeds:
    → Sends ACK (acknowledgement)
    → Task removed from queue permanently

2b. Worker crashes (no ACK):
    → Timeout expires
    → Task becomes visible again
    → Another worker picks it up
    → Task is NEVER lost!
```

**Result:** Tasks are never lost, even if worker crashes

---

## 📋 The 4 Types of Background Tasks

### **1. One-Off Tasks**

**Definition:** Triggered by specific event, runs once

**Examples:**
- Send verification email after signup
- Send push notification
- Process payment webhook
- Generate invoice PDF

**FastAPI Implementation:**
```python
@app.post("/signup")
def signup(user: UserCreate, bg_tasks: BackgroundTasks):
    create_user(user)
    
    # One-off task
    bg_tasks.add_task(send_verification_email, user.email)
    
    return {"status": "success"}
```

---

### **2. Recurring Tasks (Cron Jobs)**

**Definition:** Scheduled jobs at specific intervals

**Examples:**
- Daily report generation (every day at midnight)
- Database cleanup (every Sunday)
- Orphan session deletion (monthly)
- Backup database (hourly)

**Implementation (Celery Beat):**
```python
from celery.schedules import crontab

celery.conf.beat_schedule = {
    'cleanup-sessions-daily': {
        'task': 'tasks.cleanup_orphan_sessions',
        'schedule': crontab(hour=0, minute=0),  # Midnight daily
    },
    'generate-reports-weekly': {
        'task': 'tasks.generate_weekly_reports',
        'schedule': crontab(day_of_week=0, hour=0),  # Sunday midnight
    },
}
```

---

### **3. Chained Tasks (Parent-Child)**

**Definition:** Tasks with dependencies, workflow

**Example: Video Processing**
```
1. Upload video
   ↓
2. Encode video (parent task)
   ↓ (wait for completion)
3. Generate thumbnails (child 1) | Create subtitles (child 2)
   ↓                              ↓
4. Both complete → notify user
```

**Implementation:**
```python
from celery import chain

# Define workflow
workflow = chain(
    encode_video.s(video_id),         # Parent
    generate_thumbnails.s(),           # Child 1 (waits for parent)
    create_subtitles.s()               # Child 2 (waits for child 1)
)

# Execute chain
workflow.apply_async()
```

**Why chained?**
- Thumbnail needs encoded video
- Subtitle needs encoded video
- If thumbnail fails, only retry that step (not entire encoding!)

---

### **4. Batch Tasks**

**Definition:** Single trigger spawns many tasks

**Examples:**
- Delete user account (wipe 1000s of records)
- Send email to 10,000 users
- Export all data to CSV
- Bulk import products

**Example: Delete Account**
```python
@app.delete("/account")
def delete_account(user_id: int, bg_tasks: BackgroundTasks):
    # Immediate: Log user out
    invalidate_session(user_id)
    
    # Background: Spawn batch deletion
    bg_tasks.add_task(delete_user_data_batch, user_id)
    
    # Return immediately (deletion takes minutes)
    return {"message": "Account deletion in progress"}

def delete_user_data_batch(user_id: int):
    """
    Batch task: Delete ALL user data
    - Profile, settings, preferences
    - Projects (100s)
    - Assets (1000s)
    - Comments, likes, shares
    - Logs, analytics
    
    Takes 1-5 minutes → runs in background
    """
    delete_profile(user_id)
    delete_projects(user_id)
    delete_assets(user_id)
    delete_social_data(user_id)
    # ... thousands of operations
```

---

## ✅ Best Practices

### **1. Idempotency**

**Definition:** Task can be safely executed multiple times without side effects

**Why:** Tasks WILL be retried on failure

**❌ NOT Idempotent:**
```python
def charge_credit_card(user_id, amount):
    # If this runs twice → user charged twice!
    stripe.charge(user_id, amount)
```

**✅ Idempotent:**
```python
def charge_credit_card(user_id, amount, idempotency_key):
    # Same key = same charge (won't double-charge)
    stripe.charge(
        user_id,
        amount,
        idempotency_key=idempotency_key  # Unique per request
    )
```

**With Database:**
```python
def process_payment(order_id):
    order = db.query(Order).filter(Order.id == order_id).first()
    
    # Check if already processed
    if order.status == "paid":
        return  # Already done, skip!
    
    # Use transaction for atomicity
    with db.begin():
        charge_card(order.amount)
        order.status = "paid"
        db.commit()
```

---

### **2. Keep Tasks Small & Focused**

**❌ BAD: Monolithic task**
```python
def process_video(video_id):
    # If this fails at step 5, retry from step 1! Waste!
    upload_to_s3(video_id)           # Step 1
    encode_video(video_id)            # Step 2 (5 min)
    generate_thumbnail(video_id)      # Step 3
    create_subtitles(video_id)        # Step 4
    send_notification(video_id)       # Step 5
```

**✅ GOOD: Small, chained tasks**
```python
# Each task is small, focused, retryable independently
@celery.task
def upload_to_s3(video_id):
    # Just upload
    pass

@celery.task
def encode_video(video_id):
    # Just encode
    pass

# Chain them
chain(
    upload_to_s3.s(video_id),
    encode_video.s(),
    generate_thumbnail.s(),
    create_subtitles.s(),
    send_notification.s()
).apply_async()
```

**Benefit:** If step 4 fails, retry ONLY step 4!

---

### **3. Robust Error Handling & Logging**

**Why:** Background tasks run in separate process, no API feedback

```python
@celery.task
def send_email(email, subject, body):
    try:
        logger.info(f"Sending email to {email}")
        
        result = email_service.send(email, subject, body)
        
        logger.info(f"Email sent successfully to {email}")
        return result
        
    except EmailServiceError as e:
        logger.error(f"Email service error: {e}", exc_info=True)
        raise  # Re-raise for retry mechanism
        
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}", exc_info=True)
        raise
```

**Key points:**
- ✅ Log start of task
- ✅ Log success
- ✅ Log errors with stack trace
- ✅ Re-raise exceptions for retry

---

### **4. Monitor Queue Length & Worker Health**

**Metrics to track:**
```python
# Queue metrics
- queue_length: Current tasks waiting
- tasks_processed: Total completed
- tasks_failed: Total failures
- average_time: Per-task duration

# Worker metrics
- workers_active: Currently running
- workers_crashed: Total crashes
- cpu_usage: Worker CPU %
- memory_usage: Worker RAM
```

**Tools:**
- Prometheus (collect metrics)
- Grafana (visualize)
- Flower (Celery monitoring UI)

**Alerts:**
```python
# Alert if queue backs up
if queue_length > 1000:
    alert("Queue backed up! Add more workers")

# Alert if workers crash
if workers_crashed > 5:
    alert("Workers crashing! Check logs")
```

**Scaling:**
- Queue length high → Add more workers (horizontal scaling)
- Tasks failing → Debug error logs

---

### **5. Rate Limiting for External APIs**

**Problem:** Batch task spawns 10,000 email sends → hits API rate limit

**Solution: Rate limiting**
```python
from time import sleep

@celery.task(rate_limit='100/m')  # Max 100 per minute
def send_email(email, subject, body):
    email_service.send(email, subject, body)

# Or manual throttling
def send_emails_batch(emails):
    for email in emails:
        send_email.delay(email)  # Queue task
        
        if len(emails) > 1000:
            sleep(0.1)  # Throttle to avoid burst
```

---

## 🔗 FastAPI Integration Patterns

### **Pattern 1: Built-in BackgroundTasks (Simple)**

**Use for:** Simple, short tasks in same process

```python
from fastapi import BackgroundTasks

@app.post("/signup")
def signup(user: UserCreate, bg_tasks: BackgroundTasks):
    create_user(user)
    
    # Run in background thread (same process)
    bg_tasks.add_task(send_email, user.email)
    
    return {"status": "success"}
```

**Pros:** Simple, no external dependencies
**Cons:** Not persistent, same process (not scalable)

---

### **Pattern 2: Celery (Production)**

**Use for:** Production apps, persistent tasks, scalability

```python
from celery import Celery

# Configure Celery
celery = Celery(
    'app',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Define task
@celery.task
def send_email(email, subject, body):
    email_service.send(email, subject, body)

# In API
@app.post("/signup")
def signup(user: UserCreate):
    create_user(user)
    
    # Queue task (Redis broker)
    send_email.delay(user.email, "Welcome", "Thanks for signing up")
    
    return {"status": "success"}
```

**Pros:** Production-ready, persistent, scalable, monitoring
**Cons:** Requires Redis/RabbitMQ, separate worker process

---

## 📊 Common Use Cases Summary

| Use Case | Task Type | Why Background | Example |
|----------|-----------|----------------|---------|
| **Send email** | One-off | External API (slow, unreliable) | Verification email |
| **Send SMS/push** | One-off | External API | Notification |
| **Process image** | One-off | CPU-intensive | Resize, optimize |
| **Process video** | Chained | Very CPU-intensive | Encode → thumbnail → subtitle |
| **Generate PDF** | One-off | CPU/memory intensive | Invoice, report |
| **Daily reports** | Recurring | Scheduled | Cron job |
| **DB cleanup** | Recurring | Maintenance | Delete orphan sessions |
| **Delete account** | Batch | Many operations | Wipe 1000s of records |
| **Bulk email** | Batch | Many external API calls | Newsletter to 10K users |

---

## 🎓 Mastery Checklist

- [ ] Explain the problem with synchronous processing?
- [ ] Describe the 3 components of a task queue?
- [ ] Understand producer, broker, consumer roles?
- [ ] Implement retry with exponential backoff?
- [ ] Explain visibility timeout & acknowledgements?
- [ ] Differentiate the 4 task types (one-off, recurring, chained, batch)?
- [ ] Design idempotent tasks?
- [ ] Keep tasks small and focused?
- [ ] Set up proper logging for background tasks?
- [ ] Monitor queue length and worker health?
- [ ] Implement rate limiting for external APIs?
- [ ] Use FastAPI BackgroundTasks?
- [ ] Set up Celery with Redis?

---

## 📍 Task Queue in the Architecture

```
HTTP Request
    ↓
Handler/Controller
    ↓
Service Layer
    ├─ Synchronous work (return immediately)
    │   └─ Create user in DB
    │
    └─ Asynchronous work (enqueue)
        └─ Queue task → Redis
                           ↓
                    [Worker Process]
                           ↓
                    Execute task
                    (send email, process video, etc.)
```

---

**Last Updated**: 2026-01-29  
**Status**: ✅ Mapping Complete  
**Practice File**: background_tasks_complete.py (next)
