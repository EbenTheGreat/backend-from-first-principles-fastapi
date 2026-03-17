"""
Complete Background Tasks & Task Queues - FastAPI
Demonstrates all concepts from Lecture 14:

1. Producer-Broker-Consumer architecture
2. One-off tasks
3. Recurring tasks (cron)
4. Chained tasks (parent-child)
5. Batch tasks
6. Retry with exponential backoff
7. Idempotency
8. Visibility timeout & acknowledgements
9. Monitoring & alerting

Run with:
  # Terminal 1: Start FastAPI
  fastapi dev background_tasks_complete.py
  
  # Terminal 2: Start Celery worker (if using Celery)
  celery -A background_tasks_complete.celery worker --loglevel=info

Visit: http://127.0.0.1:8000/docs

Install:
  pip install "fastapi[standard]" sqlalchemy redis celery
  
  # Run Redis with Docker (for Celery broker)
  docker run -d -p 6379:6379 redis:7-alpine

NOTE: This file demonstrates BOTH approaches:
      1. FastAPI BackgroundTasks (simple, built-in)
      2. Celery (production-ready, persistent)
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from celery import Celery, chain, group
from celery.schedules import crontab
from datetime import datetime, timedelta
from typing import Optional, List
import time
import logging
import random

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CELERY SETUP (Production Task Queue)
# ============================================================================

# Initialize Celery
celery = Celery(
    'background_tasks',
    broker='redis://localhost:6379/0',  # Message broker
    backend='redis://localhost:6379/0'  # Result backend
)

# Celery configuration
celery.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # Acknowledge after task completes (safety)
    worker_prefetch_multiplier=1,  # Take one task at a time
)

# Celery Beat schedule (recurring tasks)
celery.conf.beat_schedule = {
    'cleanup-sessions-daily': {
        'task': 'background_tasks_complete.cleanup_orphan_sessions',
        'schedule': crontab(hour=0, minute=0),  # Midnight daily
    },
    'generate-reports-weekly': {
        'task': 'background_tasks_complete.generate_weekly_report',
        'schedule': crontab(day_of_week=0, hour=0),  # Sunday midnight
    },
}

# ============================================================================
# DATABASE SETUP
# ============================================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///./background_tasks.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserModel(Base):
    """User model"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SessionModel(Base):
    """Session model (for cleanup demo)"""
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    token = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)

class VideoModel(Base):
    """Video model (for chained tasks demo)"""
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    status = Column(String, default="uploaded")  # uploaded, encoding, encoded, processing, ready
    encoded_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    subtitle_url = Column(String, nullable=True)

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

class UserCreate(BaseModel):
    email: str
    username: str

class VideoUpload(BaseModel):
    title: str

# ============================================================================
# SIMULATED EXTERNAL SERVICES
# ============================================================================

def send_email_service(to: str, subject: str, body: str):
    """
    Simulated email service (e.g., Resend, Mailgun)
    
    In real app: Calls external API
    Here: Simulates delay and random failures
    """
    logger.info(f"Sending email to {to}: {subject}")
    
    # Simulate network delay
    time.sleep(1)
    
    # Simulate 20% failure rate
    if random.random() < 0.2:
        raise Exception("Email service timeout")
    
    logger.info(f"Email sent successfully to {to}")
    return {"status": "sent"}

def process_payment_service(user_id: int, amount: int):
    """Simulated payment processor (e.g., Stripe)"""
    logger.info(f"Processing payment for user {user_id}: ${amount/100}")
    time.sleep(0.5)
    
    if random.random() < 0.1:
        raise Exception("Payment gateway timeout")
    
    logger.info(f"Payment processed successfully")
    return {"transaction_id": f"txn_{random.randint(1000, 9999)}"}

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Background Tasks & Task Queues Complete Example",
    description="All background task patterns from Lecture 14",
    version="1.0.0"
)

# ============================================================================
# SECTION 1: FASTAPI BACKGROUNDTASKS (SIMPLE APPROACH)
# ============================================================================

@app.post("/simple/signup")
def simple_signup(user: UserCreate, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    FASTAPI BACKGROUNDTASKS - Simple One-Off Task
    
    Pros:
    - Built-in, no external dependencies
    - Easy to use
    - Good for simple tasks
    
    Cons:
    - Not persistent (task lost if server crashes)
    - Same process (not scalable)
    - No retry mechanism
    - No monitoring
    
    Use for: Simple, non-critical tasks
    """
    # 1. Create user (synchronous)
    db_user = UserModel(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # 2. Queue verification email (background)
    bg_tasks.add_task(
        send_verification_email_simple,
        db_user.email,
        db_user.username
    )
    
    # 3. Return immediately!
    return {
        "message": "User created",
        "user_id": db_user.id,
        "note": "Verification email will be sent in background",
        "approach": "FastAPI BackgroundTasks (simple)"
    }

def send_verification_email_simple(email: str, username: str):
    """
    Background task function (FastAPI BackgroundTasks)
    
    Runs in separate thread of same process
    """
    try:
        logger.info(f"Background task started: send verification email to {email}")
        
        send_email_service(
            to=email,
            subject="Verify your email",
            body=f"Hi {username}, please verify your email..."
        )
        
        logger.info(f"Background task completed: email sent to {email}")
    except Exception as e:
        logger.error(f"Background task failed: {e}")
        # No retry - task is lost!

# ============================================================================
# SECTION 2: CELERY ONE-OFF TASKS (PRODUCTION APPROACH)
# ============================================================================

@celery.task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 5},
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minutes
    retry_jitter=True  # Add randomness to prevent thundering herd
)
def send_verification_email_celery(email: str, username: str):
    """
    CELERY TASK - Production One-Off Task
    
    Features:
    - Persistent (survives server restart)
    - Automatic retry with exponential backoff
    - Separate process (scalable)
    - Monitoring via Flower
    - Acknowledgement after completion
    
    Retry pattern:
    - Attempt 1: Immediate
    - Attempt 2: ~1 minute
    - Attempt 3: ~2 minutes
    - Attempt 4: ~4 minutes
    - Attempt 5: ~8 minutes
    """
    logger.info(f"Celery task started: send_verification_email to {email}")
    
    # This will auto-retry if it fails
    send_email_service(
        to=email,
        subject="Verify your email",
        body=f"Hi {username}, please verify your email..."
    )
    
    logger.info(f"Celery task completed: email sent to {email}")
    return {"status": "sent", "email": email}

@app.post("/celery/signup")
def celery_signup(user: UserCreate, db: Session = Depends(get_db)):
    """
    CELERY - Production Background Tasks
    
    Demonstrates:
    - Producer (this API)
    - Broker (Redis)
    - Consumer (Celery worker)
    """
    # 1. Create user (synchronous)
    db_user = UserModel(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # 2. Queue task to Celery (via Redis broker)
    task = send_verification_email_celery.delay(
        db_user.email,
        db_user.username
    )
    
    # 3. Return immediately with task ID
    return {
        "message": "User created",
        "user_id": db_user.id,
        "task_id": task.id,
        "note": "Email queued for background processing",
        "approach": "Celery (production-ready)",
        "monitor": f"Check task status at /celery/task/{task.id}"
    }

@app.get("/celery/task/{task_id}")
def get_task_status(task_id: str):
    """
    Check status of Celery task
    
    States:
    - PENDING: Not started yet
    - STARTED: Currently running
    - SUCCESS: Completed successfully
    - FAILURE: Failed
    - RETRY: Retrying after failure
    """
    task = celery.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "state": task.state,
        "result": task.result if task.ready() else None,
        "info": task.info
    }

# ============================================================================
# SECTION 3: RECURRING TASKS (CRON JOBS)
# ============================================================================

@celery.task
def cleanup_orphan_sessions():
    """
    RECURRING TASK - Database Maintenance
    
    Scheduled: Daily at midnight (via Celery Beat)
    
    Purpose: Delete sessions older than 30 days
    
    Real-world use:
    - Free up database storage
    - Remove inactive sessions
    - GDPR compliance
    """
    logger.info("Starting session cleanup task")
    
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Delete old sessions
        deleted = db.query(SessionModel).filter(
            SessionModel.last_accessed < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleanup complete: {deleted} orphan sessions deleted")
        return {"deleted": deleted}
        
    finally:
        db.close()

@celery.task
def generate_weekly_report():
    """
    RECURRING TASK - Report Generation
    
    Scheduled: Sunday at midnight (via Celery Beat)
    
    Purpose: Generate weekly analytics report
    
    Real-world:
    - Compile week's data
    - Generate PDF
    - Email to admins
    """
    logger.info("Generating weekly report")
    
    db = SessionLocal()
    try:
        # Get week's data
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users = db.query(UserModel).filter(
            UserModel.created_at >= week_ago
        ).count()
        
        # Generate report (simulated)
        report = {
            "week": week_ago.strftime("%Y-%m-%d"),
            "new_users": new_users,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Weekly report generated: {report}")
        return report
        
    finally:
        db.close()

@app.post("/demo/trigger-cleanup")
def trigger_cleanup_manually():
    """
    Manually trigger recurring task (for testing)
    
    Normally runs automatically via Celery Beat
    """
    task = cleanup_orphan_sessions.delay()
    
    return {
        "message": "Cleanup task triggered manually",
        "task_id": task.id,
        "note": "Normally runs automatically at midnight"
    }

# ============================================================================
# SECTION 4: CHAINED TASKS (PARENT-CHILD)
# ============================================================================

@celery.task
def encode_video(video_id: int):
    """
    CHAINED TASK - Parent
    
    Step 1: Encode video
    Must complete before thumbnail/subtitle generation
    """
    logger.info(f"Encoding video {video_id}")
    
    db = SessionLocal()
    try:
        video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
        if not video:
            raise Exception(f"Video {video_id} not found")
        
        # Update status
        video.status = "encoding"
        db.commit()
        
        # Simulate encoding (takes 5 seconds)
        time.sleep(5)
        
        # Update with encoded URL
        video.encoded_url = f"https://cdn.example.com/encoded/{video_id}.mp4"
        video.status = "encoded"
        db.commit()
        
        logger.info(f"Video {video_id} encoded successfully")
        return video_id
        
    finally:
        db.close()

@celery.task
def generate_thumbnail(video_id: int):
    """
    CHAINED TASK - Child 1
    
    Step 2a: Generate thumbnail
    Depends on video being encoded
    """
    logger.info(f"Generating thumbnail for video {video_id}")
    
    db = SessionLocal()
    try:
        video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
        
        # Simulate thumbnail generation
        time.sleep(2)
        
        video.thumbnail_url = f"https://cdn.example.com/thumbnails/{video_id}.jpg"
        db.commit()
        
        logger.info(f"Thumbnail generated for video {video_id}")
        return video_id
        
    finally:
        db.close()

@celery.task
def create_subtitles(video_id: int):
    """
    CHAINED TASK - Child 2
    
    Step 2b: Create subtitles
    Depends on video being encoded
    """
    logger.info(f"Creating subtitles for video {video_id}")
    
    db = SessionLocal()
    try:
        video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
        
        # Simulate subtitle generation
        time.sleep(3)
        
        video.subtitle_url = f"https://cdn.example.com/subtitles/{video_id}.vtt"
        video.status = "ready"
        db.commit()
        
        logger.info(f"Subtitles created for video {video_id}")
        return video_id
        
    finally:
        db.close()

@app.post("/video/upload")
def upload_video(video: VideoUpload, db: Session = Depends(get_db)):
    """
    CHAINED TASKS DEMO
    
    Workflow:
    1. Upload video (sync)
    2. Encode video (async, parent)
    3. Generate thumbnail (async, child) | Create subtitles (async, child)
    
    If thumbnail fails → only retry thumbnail
    If encoding fails → retry encoding (children wait)
    """
    # 1. Create video record
    db_video = VideoModel(title=video.title, status="uploaded")
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    
    # 2. Create workflow chain
    workflow = chain(
        encode_video.s(db_video.id),      # Parent
        group(                             # Children (parallel)
            generate_thumbnail.s(),
            create_subtitles.s()
        )
    )
    
    # 3. Execute workflow
    result = workflow.apply_async()
    
    return {
        "message": "Video uploaded",
        "video_id": db_video.id,
        "workflow_id": result.id,
        "workflow": [
            "1. Encode video (parent)",
            "2. Generate thumbnail (child, parallel)",
            "3. Create subtitles (child, parallel)"
        ],
        "note": "Check video status at /video/status/{video_id}"
    }

@app.get("/video/status/{video_id}")
def get_video_status(video_id: int, db: Session = Depends(get_db)):
    """Check video processing status"""
    video = db.query(VideoModel).filter(VideoModel.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return {
        "video_id": video_id,
        "title": video.title,
        "status": video.status,
        "encoded_url": video.encoded_url,
        "thumbnail_url": video.thumbnail_url,
        "subtitle_url": video.subtitle_url
    }

# ============================================================================
# SECTION 5: BATCH TASKS
# ============================================================================

@celery.task
def delete_user_data(user_id: int):
    """
    BATCH TASK - Delete User Account
    
    Single trigger spawns many operations:
    - Delete profile
    - Delete projects (100s)
    - Delete assets (1000s)
    - Delete comments, likes
    - Delete logs
    
    Takes 1-5 minutes → must run in background
    """
    logger.info(f"Starting batch deletion for user {user_id}")
    
    db = SessionLocal()
    try:
        # Simulate deleting many records
        operations = [
            "Delete profile",
            "Delete 150 projects",
            "Delete 3500 assets",
            "Delete 890 comments",
            "Delete 1200 likes",
            "Delete analytics data",
            "Delete notification settings",
            "Remove from search index"
        ]
        
        for i, operation in enumerate(operations):
            logger.info(f"[{i+1}/{len(operations)}] {operation}")
            time.sleep(0.5)  # Simulate work
        
        # Actually delete user
        db.query(UserModel).filter(UserModel.id == user_id).delete()
        db.commit()
        
        logger.info(f"User {user_id} fully deleted")
        return {"user_id": user_id, "operations": len(operations)}
        
    finally:
        db.close()

@app.delete("/account/{user_id}")
def delete_account(user_id: int, db: Session = Depends(get_db)):
    """
    DELETE ACCOUNT - Batch Task Demo
    
    Flow:
    1. Verify user exists
    2. Log user out immediately
    3. Queue batch deletion (background)
    4. Return success
    
    User sees instant response, deletion happens in background
    """
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Queue batch deletion
    task = delete_user_data.delay(user_id)
    
    return {
        "message": "Account deletion in progress",
        "user_id": user_id,
        "task_id": task.id,
        "note": "You are logged out. Deletion will complete in 1-5 minutes.",
        "warning": "This is a batch task with thousands of operations"
    }

# ============================================================================
# SECTION 6: IDEMPOTENCY DEMO
# ============================================================================

@celery.task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3}
)
def charge_credit_card_idempotent(order_id: int, amount: int):
    """
    IDEMPOTENT TASK
    
    Can be safely run multiple times without double-charging
    
    Pattern:
    1. Check if already processed
    2. If yes → return (skip)
    3. If no → process with transaction
    """
    logger.info(f"Processing payment for order {order_id}")
    
    db = SessionLocal()
    try:
        # Simulate order check
        # In real app: Check order.status in database
        already_paid = False  # Simulate
        
        if already_paid:
            logger.info(f"Order {order_id} already paid, skipping")
            return {"status": "already_paid"}
        
        # Process payment
        result = process_payment_service(user_id=1, amount=amount)
        
        # Update order status (atomic transaction)
        # order.status = "paid"
        # db.commit()
        
        logger.info(f"Payment processed for order {order_id}")
        return {"status": "paid", "transaction": result}
        
    finally:
        db.close()

@app.post("/demo/idempotent-payment")
def demo_idempotent_payment(order_id: int, amount: int):
    """
    Idempotency Demo
    
    Call this multiple times with same order_id
    → Only charged once!
    """
    task = charge_credit_card_idempotent.delay(order_id, amount)
    
    return {
        "message": "Payment queued",
        "order_id": order_id,
        "task_id": task.id,
        "note": "Call again with same order_id → won't charge twice (idempotent)"
    }

# ============================================================================
# MONITORING & STATS
# ============================================================================

@app.get("/celery/stats")
def get_celery_stats():
    """
    MONITORING - Queue & Worker Stats
    
    Track:
    - Active workers
    - Queue length
    - Task success/failure rates
    """
    inspector = celery.control.inspect()
    
    # Get active tasks
    active = inspector.active()
    
    # Get stats
    stats = inspector.stats()
    
    # Get registered tasks
    registered = inspector.registered()
    
    return {
        "active_tasks": active,
        "worker_stats": stats,
        "registered_tasks": registered,
        "note": "Use Flower for better monitoring: pip install flower, celery -A app flower"
    }

# ============================================================================
# ROOT
# ============================================================================

@app.get("/")
def root():
    return {
        "message": "Background Tasks & Task Queues Complete API",
        "documentation": "/docs",
        "sections": {
            "1_simple_backgroundtasks": "POST /simple/signup",
            "2_celery_one_off": "POST /celery/signup",
            "3_task_status": "GET /celery/task/{task_id}",
            "4_recurring_cleanup": "POST /demo/trigger-cleanup",
            "5_chained_video": "POST /video/upload",
            "6_video_status": "GET /video/status/{video_id}",
            "7_batch_delete": "DELETE /account/{user_id}",
            "8_idempotent": "POST /demo/idempotent-payment",
            "9_monitoring": "GET /celery/stats"
        },
        "task_types": {
            "one_off": "Send email, process payment",
            "recurring": "Daily cleanup, weekly reports (cron)",
            "chained": "Video workflow (encode → thumbnail → subtitle)",
            "batch": "Delete account (1000s of operations)"
        },
        "architecture": {
            "producer": "This FastAPI app (enqueues tasks)",
            "broker": "Redis (stores tasks)",
            "consumer": "Celery worker (processes tasks)"
        }
    }

# ============================================================================
# SEED DATA
# ============================================================================

@app.on_event("startup")
def seed():
    db = SessionLocal()
    
    # Seed some sessions for cleanup demo
    if db.query(SessionModel).count() == 0:
        old_sessions = [
            SessionModel(
                user_id=i,
                token=f"token_{i}",
                last_accessed=datetime.utcnow() - timedelta(days=35)  # Old!
            )
            for i in range(10)
        ]
        db.add_all(old_sessions)
        db.commit()
        logger.info("✅ Seeded 10 old sessions for cleanup demo")
    
    db.close()

# ============================================================================
# TEST COMMANDS
# ============================================================================
"""
SETUP:
  # Install
  pip install "fastapi[standard]" sqlalchemy redis celery
  
  # Start Redis (broker)
  docker run -d -p 6379:6379 redis:7-alpine
  
  # Terminal 1: Start FastAPI
  fastapi dev background_tasks_complete.py
  
  # Terminal 2: Start Celery worker
  celery -A background_tasks_complete.celery worker --loglevel=info
  
  # Terminal 3 (optional): Start Celery Beat (for cron jobs)
  celery -A background_tasks_complete.celery beat --loglevel=info
  
  # Terminal 4 (optional): Flower monitoring UI
  pip install flower
  celery -A background_tasks_complete.celery flower

TESTS:

1. Simple BackgroundTasks (no Celery):
   curl -X POST http://localhost:8000/simple/signup \
     -H "Content-Type: application/json" \
     -d '{"email":"alice@example.com","username":"alice"}'
   
   # Check logs - email sent in background thread

2. Celery One-Off Task:
   curl -X POST http://localhost:8000/celery/signup \
     -H "Content-Type: application/json" \
     -d '{"email":"bob@example.com","username":"bob"}'
   
   # Get task ID from response, check status:
   curl http://localhost:8000/celery/task/TASK_ID_HERE

3. Recurring Task (manual trigger):
   curl -X POST http://localhost:8000/demo/trigger-cleanup
   
   # Check worker logs - see cleanup in action

4. Chained Tasks (video workflow):
   curl -X POST http://localhost:8000/video/upload \
     -H "Content-Type: application/json" \
     -d '{"title":"My Video"}'
   
   # Check status:
   curl http://localhost:8000/video/status/1
   
   # Watch worker logs - see chain: encode → thumbnail → subtitle

5. Batch Task (delete account):
   curl -X DELETE http://localhost:8000/account/1
   
   # Watch worker logs - see many operations

6. Idempotency:
   # Call twice with same order_id
   curl -X POST "http://localhost:8000/demo/idempotent-payment?order_id=123&amount=1000"
   curl -X POST "http://localhost:8000/demo/idempotent-payment?order_id=123&amount=1000"
   
   # Only processed once!

7. Monitor queue:
   curl http://localhost:8000/celery/stats

KEY INSIGHTS:

Synchronous vs Asynchronous:
  Sync: User waits → bad UX, blocks on external API
  Async: User gets instant response → good UX, queue retries

The 3 Components:
  Producer: API (enqueues tasks)
  Broker: Redis (stores tasks)
  Consumer: Worker (processes tasks)

Task Types:
  One-off: Triggered by event (email, payment)
  Recurring: Cron schedule (cleanup, reports)
  Chained: Parent-child dependencies (video workflow)
  Batch: Single trigger, many operations (delete account)

Reliability:
  Retry: Auto-retry with exponential backoff
  Visibility timeout: Task never lost if worker crashes
  Acknowledgement: Worker confirms completion

Best Practices:
  Idempotency: Safe to run multiple times
  Small tasks: Easy to retry, scale, debug
  Logging: Track everything (no API feedback)
  Monitoring: Queue length, worker health
  Rate limiting: Don't overwhelm external APIs

FastAPI BackgroundTasks vs Celery:
  BackgroundTasks: Simple, same process, not persistent
  Celery: Production, persistent, scalable, monitoring
"""
