"""
Complete Backend Security - FastAPI
Demonstrates all concepts from Lecture 20:

1. SQL Injection (vulnerable vs safe)
2. NoSQL Injection (vulnerable vs safe)
3. Command Injection (vulnerable vs safe)
4. XSS (vulnerable vs safe + sanitization + CSP)
5. CSRF Protection (SameSite cookies)
6. Clickjacking Protection (X-Frame-Options)
7. Security Headers Middleware
8. Database Permission Restriction
9. Input Validation with Pydantic

⚠️  WARNING: This file contains VULNERABLE endpoints for educational purposes!
    - /vulnerable/* endpoints demonstrate attacks
    - /safe/* endpoints show proper defenses
    
    NEVER use vulnerable patterns in production!

Run with:
  fastapi dev backend_security_complete.py

Visit: http://localhost:8000/docs

Install:
  pip install "fastapi[standard]" sqlalchemy bleach
"""

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import subprocess
import bleach
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE SETUP
# ============================================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///./security_demo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserModel(Base):
    """User model for SQL injection demos"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password = Column(String)
    name = Column(String)

class CommentModel(Base):
    """Comment model for XSS demos"""
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    content = Column(String)
    user_id = Column(Integer)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Seed data
db = SessionLocal()
if db.query(UserModel).count() == 0:
    users = [
        UserModel(email="alice@example.com", password="secret123", name="Alice"),
        UserModel(email="bob@example.com", password="password456", name="Bob"),
        UserModel(email="admin@example.com", password="admin_pass", name="Admin")
    ]
    db.add_all(users)
    db.commit()
    logger.info("✅ Seeded demo users")
db.close()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class CommentCreate(BaseModel):
    """Safe comment with validation and sanitization"""
    content: str = Field(..., min_length=1, max_length=1000)
    user_id: int
    
    @field_validator('content')
    @classmethod
    def sanitize_content(cls, v):
        """
        SANITIZATION: Strip dangerous HTML tags
        
        Allowed tags: p, b, i, em, strong (safe formatting)
        Dangerous tags stripped: script, iframe, object, etc.
        """
        clean = bleach.clean(
            v,
            tags=['p', 'b', 'i', 'em', 'strong', 'a'],
            attributes={'a': ['href']},
            strip=True
        )
        return clean

class LoginRequest(BaseModel):
    """Login request with validation"""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)

# ============================================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    SECURITY HEADERS MIDDLEWARE
    
    Adds multiple security headers to every response:
    - CSP: Prevent XSS
    - X-Frame-Options: Prevent clickjacking
    - HSTS: Force HTTPS
    - X-Content-Type-Options: Prevent MIME sniffing
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Content Security Policy (XSS prevention)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "object-src 'none'"
        )
        
        # Clickjacking prevention
        response.headers["X-Frame-Options"] = "DENY"
        
        # Force HTTPS (in production)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS filter (legacy, but doesn't hurt)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Backend Security Complete - Educational Demo",
    description="⚠️  Contains VULNERABLE endpoints for education only!",
    version="1.0.0"
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Dev frontend
        "https://myapp.com"       # Prod frontend
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"]
)

# ============================================================================
# SECTION 1: SQL INJECTION
# ============================================================================

@app.get("/vulnerable/sql-injection")
def vulnerable_sql_injection(email: str, db: Session = Depends(get_db)):
    """
    ❌ VULNERABLE: SQL INJECTION
    
    Attack examples:
    - email=' OR 1=1 --
      → Returns all users!
    
    - email='; DROP TABLE users; --
      → Deletes users table!
    
    Test:
      curl "http://localhost:8000/vulnerable/sql-injection?email=' OR 1=1 --"
    """
    # ❌ DANGEROUS: String concatenation
    query = f"SELECT * FROM users WHERE email = '{email}'"
    
    logger.warning(f"⚠️  VULNERABLE SQL: {query}")
    
    try:
        result = db.execute(text(query))
        users = [dict(row._mapping) for row in result]
        
        return {
            "warning": "⚠️  This endpoint is VULNERABLE to SQL injection!",
            "query": query,
            "users": users,
            "attack_detected": "' OR 1=1" in email or "DROP TABLE" in email.upper()
        }
    except Exception as e:
        return {"error": str(e), "query": query}

@app.get("/safe/sql-injection")
def safe_sql_injection(email: str, db: Session = Depends(get_db)):
    """
    ✅ SAFE: PARAMETERIZED QUERY
    
    Attack attempts:
    - email=' OR 1=1 --
      → Treated as literal string!
      → No users found (as expected)
    
    Test:
      curl "http://localhost:8000/safe/sql-injection?email=' OR 1=1 --"
    """
    # ✅ SAFE: Parameterized query
    query = text("SELECT * FROM users WHERE email = :email")
    
    logger.info(f"✅ SAFE SQL with parameter: {email}")
    
    result = db.execute(query, {"email": email})
    users = [dict(row._mapping) for row in result]
    
    return {
        "message": "✅ Safe parameterized query",
        "users": users,
        "note": "Special characters in email are treated as literal strings"
    }

@app.get("/safe/sql-orm")
def safe_sql_orm(email: str, db: Session = Depends(get_db)):
    """
    ✅ SAFE: ORM (Automatic Parameterization)
    
    SQLAlchemy ORM automatically uses parameterized queries
    """
    # ✅ SAFE: ORM approach
    user = db.query(UserModel).filter(UserModel.email == email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "message": "✅ Safe ORM query",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }

# ============================================================================
# SECTION 2: NOSQL INJECTION
# ============================================================================

@app.post("/vulnerable/nosql-injection")
def vulnerable_nosql_injection(credentials: dict):
    """
    ❌ VULNERABLE: NoSQL INJECTION
    
    Attack:
    {
      "username": "admin",
      "password": {"$ne": null}
    }
    
    Result: Bypasses authentication! 💀
    
    Test:
      curl -X POST http://localhost:8000/vulnerable/nosql-injection \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":{"$ne":null}}'
    """
    logger.warning(f"⚠️  VULNERABLE NoSQL: {credentials}")
    
    # ❌ DANGEROUS: User controls entire structure
    # In real MongoDB: db.users.find_one(credentials)
    
    # Simulated check
    if isinstance(credentials.get('password'), dict):
        return {
            "warning": "⚠️  NoSQL injection detected!",
            "attack": "Password is object with MongoDB operator",
            "credentials": credentials,
            "result": "Authentication BYPASSED! 💀"
        }
    
    return {"message": "Login failed"}

@app.post("/safe/nosql-injection")
def safe_nosql_injection(credentials: LoginRequest):
    """
    ✅ SAFE: VALIDATED STRUCTURE
    
    Pydantic ensures username and password are strings!
    MongoDB operators like $ne are rejected.
    
    Test:
      curl -X POST http://localhost:8000/safe/nosql-injection \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":{"$ne":null}}'
      
      Result: 422 Validation Error ✅
    """
    logger.info(f"✅ SAFE NoSQL with validation: {credentials.username}")
    
    # Pydantic has validated: username and password are strings!
    # MongoDB operators rejected before reaching database
    
    return {
        "message": "✅ Safe validated login",
        "username": credentials.username,
        "note": "Pydantic ensures fields are strings, not objects"
    }

# ============================================================================
# SECTION 3: COMMAND INJECTION
# ============================================================================

@app.post("/vulnerable/command-injection")
def vulnerable_command_injection(filename: str):
    """
    ❌ VULNERABLE: COMMAND INJECTION
    
    Attack:
    - filename=output; ls -la
      → Executes: ffmpeg ... && ls -la
      → Lists directory contents!
    
    - filename=output; cat /etc/passwd
      → Reads password file!
    
    - filename=output; rm -rf /
      → DELETES EVERYTHING! 💀💀💀
    
    Test:
      curl -X POST "http://localhost:8000/vulnerable/command-injection?filename=output; ls -la"
    """
    # ❌ DANGEROUS: Shell command with user input
    command = f"echo 'Simulating: ffmpeg -i input.mp4 {filename}.mp4'"
    
    logger.warning(f"⚠️  VULNERABLE COMMAND: {command}")
    
    try:
        # Using shell=True makes it vulnerable!
        result = subprocess.run(
            command,
            shell=True,  # ❌ DANGEROUS!
            capture_output=True,
            text=True
        )
        
        return {
            "warning": "⚠️  This endpoint is VULNERABLE to command injection!",
            "command": command,
            "output": result.stdout,
            "attack_detected": ";" in filename or "&&" in filename or "|" in filename
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/safe/command-injection")
def safe_command_injection(filename: str):
    """
    ✅ SAFE: SUBPROCESS WITH ARRAY
    
    Attack attempts:
    - filename=output; ls -la
      → Treated as literal filename: "output; ls -la.mp4"
      → No command execution!
    
    Test:
      curl -X POST "http://localhost:8000/safe/command-injection?filename=output; ls -la"
    """
    # ✅ SAFE: Arguments as array (no shell)
    command = [
        "echo",
        f"Simulating: ffmpeg -i input.mp4 {filename}.mp4"
    ]
    
    logger.info(f"✅ SAFE COMMAND (array): {command}")
    
    try:
        # shell=False means ; && | have no special meaning
        result = subprocess.run(
            command,
            shell=False,  # ✅ SAFE!
            capture_output=True,
            text=True
        )
        
        return {
            "message": "✅ Safe subprocess call",
            "command": command,
            "output": result.stdout,
            "note": "Special characters treated as literal strings"
        }
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# SECTION 4: CROSS-SITE SCRIPTING (XSS)
# ============================================================================

@app.post("/vulnerable/xss")
def vulnerable_xss(content: str, user_id: int, db: Session = Depends(get_db)):
    """
    ❌ VULNERABLE: XSS (STORED)
    
    Attack:
    - content=<script>alert('XSS!')</script>
      → Saved to database as-is!
      → Executes when other users view it!
    
    Test:
      curl -X POST "http://localhost:8000/vulnerable/xss?content=<script>alert('XSS')</script>&user_id=1"
    """
    # ❌ DANGEROUS: No sanitization!
    comment = CommentModel(content=content, user_id=user_id)
    db.add(comment)
    db.commit()
    
    logger.warning(f"⚠️  VULNERABLE XSS: Saved unsanitized content")
    
    return {
        "warning": "⚠️  This endpoint saves content WITHOUT sanitization!",
        "content": content,
        "attack_detected": "<script>" in content.lower()
    }

@app.post("/safe/xss", response_model=dict)
def safe_xss(comment: CommentCreate, db: Session = Depends(get_db)):
    """
    ✅ SAFE: SANITIZED INPUT
    
    Attack attempts:
    - content=<script>alert('XSS!')</script>
      → Script tags stripped!
      → Saved as: alert('XSS!')
    
    Test:
      curl -X POST http://localhost:8000/safe/xss \
        -H "Content-Type: application/json" \
        -d '{"content":"<script>alert(XSS)</script>","user_id":1}'
    """
    # ✅ SAFE: Pydantic validator sanitizes content!
    # See CommentCreate.sanitize_content()
    
    db_comment = CommentModel(
        content=comment.content,  # Already sanitized!
        user_id=comment.user_id
    )
    db.add(db_comment)
    db.commit()
    
    logger.info(f"✅ SAFE XSS: Saved sanitized content")
    
    return {
        "message": "✅ Safe sanitized content",
        "content": comment.content,
        "note": "Dangerous tags stripped by Pydantic validator"
    }

@app.get("/xss-demo", response_class=HTMLResponse)
def xss_demo():
    """
    XSS DEMO PAGE
    
    Shows how CSP header blocks inline scripts
    Even if XSS payload gets through, CSP blocks execution
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>XSS Demo</title>
    </head>
    <body>
        <h1>XSS Protection Demo</h1>
        
        <h2>❌ Inline Script (Blocked by CSP)</h2>
        <p>Open browser console - you'll see CSP violation:</p>
        <script>
            alert('This inline script is BLOCKED by CSP!');
        </script>
        
        <h2>✅ External Script (Allowed by CSP)</h2>
        <p>External scripts from 'self' are allowed:</p>
        <script src="/static/safe.js"></script>
        
        <p>Check response headers - see Content-Security-Policy!</p>
    </body>
    </html>
    """

# ============================================================================
# SECTION 5: CSRF PROTECTION
# ============================================================================

@app.post("/login")
def login(credentials: LoginRequest):
    """
    LOGIN WITH CSRF PROTECTION
    
    Sets session cookie with SameSite=Lax
    Prevents CSRF attacks
    """
    # Authenticate user (simplified)
    if credentials.username == "admin" and credentials.password == "secret":
        response = JSONResponse(content={"message": "Logged in successfully"})
        
        # ✅ SAFE COOKIE CONFIGURATION
        response.set_cookie(
            key="session_id",
            value="simulated_session_token_123",
            httponly=True,   # ✅ XSS cannot steal
            secure=True,     # ✅ HTTPS only (in production)
            samesite="lax",  # ✅ CSRF protection
            max_age=3600     # 1 hour
        )
        
        logger.info("✅ Session cookie set with security flags")
        
        return response
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/csrf-demo", response_class=HTMLResponse)
def csrf_demo():
    """
    CSRF ATTACK DEMO
    
    Shows how SameSite cookie prevents CSRF
    """
    return """
    <!DOCTYPE html>
    <html>
    <head><title>CSRF Demo</title></head>
    <body>
        <h1>CSRF Protection Demo</h1>
        
        <h2>Scenario:</h2>
        <ol>
            <li>User logs in to bank.com (sets session cookie)</li>
            <li>User visits evil.com (this page)</li>
            <li>evil.com tries to make request to bank.com</li>
        </ol>
        
        <h2>Attack Attempt:</h2>
        <form action="http://localhost:8000/transfer" method="POST">
            <input name="to" value="attacker">
            <input name="amount" value="10000">
            <button>Transfer Money</button>
        </form>
        
        <h2>Result:</h2>
        <p>With SameSite=Lax cookie: ❌ Cookie NOT sent cross-site!</p>
        <p>Request rejected (unauthenticated)</p>
        <p>Attack fails! ✅</p>
    </body>
    </html>
    """

# ============================================================================
# SECTION 6: CLICKJACKING PROTECTION
# ============================================================================

@app.get("/clickjacking-demo", response_class=HTMLResponse)
def clickjacking_demo():
    """
    CLICKJACKING DEMO
    
    Try to embed this page in iframe - blocked by X-Frame-Options!
    """
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Clickjacking Demo</title></head>
    <body>
        <h1>Clickjacking Protection Demo</h1>
        
        <h2>Try to embed this page in iframe:</h2>
        <iframe src="/" width="600" height="400"></iframe>
        
        <h2>Result:</h2>
        <p>❌ Refused to display in iframe!</p>
        <p>Check console - X-Frame-Options: DENY</p>
        <p>Clickjacking attack prevented! ✅</p>
    </body>
    </html>
    """

# ============================================================================
# ROOT
# ============================================================================

@app.get("/")
def root():
    return {
        "message": "Backend Security Complete - Educational Demo",
        "warning": "⚠️  Contains VULNERABLE endpoints for education only!",
        "documentation": "/docs",
        "sections": {
            "sql_injection": {
                "vulnerable": "GET /vulnerable/sql-injection?email=' OR 1=1 --",
                "safe": "GET /safe/sql-injection?email=' OR 1=1 --"
            },
            "nosql_injection": {
                "vulnerable": "POST /vulnerable/nosql-injection",
                "safe": "POST /safe/nosql-injection"
            },
            "command_injection": {
                "vulnerable": "POST /vulnerable/command-injection?filename=output; ls",
                "safe": "POST /safe/command-injection?filename=output; ls"
            },
            "xss": {
                "vulnerable": "POST /vulnerable/xss",
                "safe": "POST /safe/xss",
                "demo": "GET /xss-demo"
            },
            "csrf": {
                "login": "POST /login",
                "demo": "GET /csrf-demo"
            },
            "clickjacking": {
                "demo": "GET /clickjacking-demo"
            }
        },
        "security_features": {
            "parameterized_queries": "SQL injection prevention",
            "pydantic_validation": "NoSQL injection + XSS prevention",
            "subprocess_arrays": "Command injection prevention",
            "csp_headers": "XSS prevention",
            "samesite_cookies": "CSRF prevention",
            "x_frame_options": "Clickjacking prevention",
            "security_middleware": "Multiple headers automatically"
        }
    }

# ============================================================================
# TEST COMMANDS
# ============================================================================
"""
SETUP:
  pip install "fastapi[standard]" sqlalchemy bleach
  
RUN:
  fastapi dev backend_security_complete.py

TESTS:

1. SQL Injection:
   # Vulnerable
   curl "http://localhost:8000/vulnerable/sql-injection?email=' OR 1=1 --"
   # Returns ALL users! 💀
   
   # Safe
   curl "http://localhost:8000/safe/sql-injection?email=' OR 1=1 --"
   # No users found ✅

2. NoSQL Injection:
   # Vulnerable
   curl -X POST http://localhost:8000/vulnerable/nosql-injection \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":{"$ne":null}}'
   # Authentication bypassed! 💀
   
   # Safe
   curl -X POST http://localhost:8000/safe/nosql-injection \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":{"$ne":null}}'
   # 422 Validation Error ✅

3. Command Injection:
   # Vulnerable
   curl -X POST "http://localhost:8000/vulnerable/command-injection?filename=output; ls -la"
   # Command executed! 💀
   
   # Safe
   curl -X POST "http://localhost:8000/safe/command-injection?filename=output; ls -la"
   # Treated as literal filename ✅

4. XSS:
   # Vulnerable
   curl -X POST "http://localhost:8000/vulnerable/xss?content=<script>alert('XSS')</script>&user_id=1"
   # Script saved to DB! 💀
   
   # Safe
   curl -X POST http://localhost:8000/safe/xss \
     -H "Content-Type: application/json" \
     -d '{"content":"<script>alert(XSS)</script>","user_id":1}'
   # Script tags stripped ✅

5. View XSS Demo:
   Open browser: http://localhost:8000/xss-demo
   Check console - CSP blocks inline script ✅

6. CSRF Demo:
   Open browser: http://localhost:8000/csrf-demo
   Cookie not sent cross-site ✅

7. Clickjacking Demo:
   Open browser: http://localhost:8000/clickjacking-demo
   Iframe blocked by X-Frame-Options ✅

KEY INSIGHTS:

Root Cause:
  Data crossing boundary → confused with code
  Solution: NEVER concatenate user input into commands!

SQL Injection Prevention:
  ❌ f"SELECT * FROM users WHERE email = '{email}'"
  ✅ text("SELECT * FROM users WHERE email = :email")

NoSQL Injection Prevention:
  ❌ Direct dict from user
  ✅ Pydantic validation (ensure strings, not objects)

Command Injection Prevention:
  ❌ subprocess.run(f"ffmpeg {filename}", shell=True)
  ✅ subprocess.run(["ffmpeg", filename], shell=False)

XSS Prevention (3 layers):
  1. Sanitize input (bleach.clean)
  2. CSP header (block inline scripts)
  3. HttpOnly cookies (can't steal session)

CSRF Prevention:
  SameSite=Lax cookies

Clickjacking Prevention:
  X-Frame-Options: DENY

Defense in Depth:
  Database: Restrict permissions (DML only, no DDL)
  Application: Parameterized queries
  Browser: Security headers (CSP, X-Frame-Options)
"""
