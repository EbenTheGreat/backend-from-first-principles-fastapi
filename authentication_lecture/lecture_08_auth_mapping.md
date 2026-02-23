# Lecture 8: Authentication & Authorization - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Authentication & Authorization - "Who are you?" and "What can you do?"  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Key Concepts from Your Lecture

### 1. **Core Definitions**
- **Authentication (WHO)**: Assigns identity to a subject - "Who are you?"
- **Authorization (WHAT)**: Determines permissions - "What can you do?"

### 2. **Evolution of Authentication**
- **Pre-Digital**: Village elders, wax seals (physical trust)
- **1961**: MIT introduces passwords (CTSS)
- **Hashing**: Store passwords as irreversible cryptographic strings
- **MFA**: "Something you know" + "Something you have" + "Something you are"

### 3. **Core Components**
- **Sessions**: Server-side state, Session ID stored in Redis/DB
- **Cookies**: Browser automatically sends cookies with each request
- **JWTs**: Self-contained tokens with cryptographic signature

### 4. **Four Major Authentication Types**

**Type 1: Stateful (Session-Based)**
- Server stores session data in Redis/DB
- Session ID sent via HTTPOnly cookie
- ✅ Pro: Centralized control, easy revocation
- ❌ Con: Database lookup every request, harder to scale

**Type 2: Stateless (Token-Based/JWT)**
- JWT signed with secret key
- Token sent in Authorization header
- ✅ Pro: Infinite scalability, no DB lookup
- ❌ Con: Hard to revoke before expiry

**Type 3: API Key**
- Machine-to-Machine (M2M) communication
- Long-lived cryptographic string
- For automation, not humans

**Type 4: OAuth 2.0 / OpenID Connect (OIDC)**
- Solves "delegation problem"
- OAuth 2.0: Authorization (access tokens)
- OIDC: Authentication (ID tokens)
- Powers "Sign in with Google"

### 5. **Authorization Model: RBAC**
- **Role-Based Access Control**
- Users → Roles → Permissions
- Example: Admin role → Delete permission
- Middleware checks role → Returns 403 if unauthorized

### 6. **Security Best Practices**
- **Generic error messages**: Never "User not found" - Always "Authentication failed"
- **Timing attacks**: Use constant-time operations to prevent enumeration
- **HTTPOnly cookies**: Prevent XSS attacks
- **HTTPS only**: Encrypt all traffic

---

## 🔗 FastAPI Documentation Mapping

| Your Lecture Concept | FastAPI Tutorial Section | FastAPI Docs URL |
|---------------------|--------------------------|------------------|
| **Basic Security** | Security - First Steps | https://fastapi.tiangolo.com/tutorial/security/first-steps/ |
| **Get Current User** | Get Current User | https://fastapi.tiangolo.com/tutorial/security/get-current-user/ |
| **OAuth2 Password Flow** | Simple OAuth2 | https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/ |
| **JWT Tokens** | OAuth2 with JWT | https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ |
| **OAuth2 Scopes (RBAC)** | OAuth2 Scopes | https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/ |
| **HTTP Basic Auth** | HTTP Basic Auth | https://fastapi.tiangolo.com/advanced/security/http-basic-auth/ |
| **API Key** | Security (API Key Header) | https://fastapi.tiangolo.com/tutorial/security/ |
| **Dependencies** | Dependencies | https://fastapi.tiangolo.com/tutorial/dependencies/ |

---

## 💡 FastAPI's Security Approach

### Built-in Security Utilities

FastAPI provides security utilities that handle:
1. **OAuth2PasswordBearer**: For JWT/token-based auth
2. **OAuth2PasswordRequestForm**: Standard login form
3. **HTTPBasic**: For basic auth
4. **APIKeyHeader/APIKeyQuery**: For API keys
5. **OAuth2 Scopes**: For RBAC/permissions

### The Dependency Injection Pattern

FastAPI uses **dependencies** for auth:
```python
def get_current_user(token: str = Depends(oauth2_scheme)):
    # Verify token
    return user

@app.get("/protected")
def protected(user: User = Depends(get_current_user)):
    # User is authenticated automatically
    return user
```

This is cleaner than manual middleware!

---

## 🏗️ FastAPI Implementation Examples

### PART 1: STATEFUL AUTHENTICATION (SESSION-BASED)

```python
from fastapi import FastAPI, Depends, HTTPException, status, Cookie, Response
from pydantic import BaseModel
from typing import Optional
import secrets
import hashlib

app = FastAPI()

# Simulated session storage (use Redis in production)
sessions_db = {}
users_db = {
    "alice": {
        "username": "alice",
        "hashed_password": hashlib.sha256("password123".encode()).hexdigest(),
        "role": "user"
    },
    "admin": {
        "username": "admin",
        "hashed_password": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin"
    }
}

class LoginRequest(BaseModel):
    username: str
    password: str

def hash_password(password: str) -> str:
    """Hash password (use bcrypt in production)"""
    return hashlib.sha256(password.encode()).hexdigest()

@app.post("/stateful/login")
def login_stateful(
    credentials: LoginRequest,
    response: Response
):
    """
    STATEFUL AUTHENTICATION - Session-Based
    
    Workflow:
    1. User sends username + password
    2. Server verifies credentials
    3. Server generates Session ID
    4. Server stores session data in Redis/DB
    5. Server sends Session ID in HTTPOnly cookie
    6. Browser automatically includes cookie in future requests
    
    Pros:
    - Easy revocation (delete from Redis)
    - Centralized control
    - Server knows all active sessions
    
    Cons:
    - DB lookup every request
    - Harder to scale across regions
    """
    # Verify user exists
    user = users_db.get(credentials.username)
    if not user:
        # SECURITY: Generic message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    
    # Verify password
    if hash_password(credentials.password) != user["hashed_password"]:
        # SECURITY: Same generic message
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    
    # Generate Session ID
    session_id = secrets.token_urlsafe(32)
    
    # Store session in "Redis" (simulated)
    sessions_db[session_id] = {
        "username": user["username"],
        "role": user["role"]
    }
    
    # Set HTTPOnly cookie (prevents JavaScript access - XSS protection)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,  # Prevents XSS
        secure=True,    # HTTPS only (set False for local testing)
        samesite="lax"  # CSRF protection
    )
    
    return {
        "message": "Login successful",
        "auth_type": "stateful",
        "session_id": session_id[:10] + "...",  # Truncated for display
        "note": "Session ID stored in HTTPOnly cookie"
    }

def get_current_user_stateful(session_id: Optional[str] = Cookie(None)):
    """
    Dependency: Extract user from session
    
    This runs automatically for any endpoint that depends on it
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Look up session in Redis/DB
    session = sessions_db.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )
    
    return session

@app.get("/stateful/protected")
def protected_stateful(user: dict = Depends(get_current_user_stateful)):
    """
    Protected endpoint with stateful auth
    
    The dependency automatically:
    1. Extracts session_id from cookie
    2. Looks up session in Redis
    3. Returns user data
    4. Or raises 401 if invalid
    """
    return {
        "message": "Access granted",
        "user": user["username"],
        "role": user["role"],
        "auth_type": "stateful"
    }

@app.post("/stateful/logout")
def logout_stateful(
    response: Response,
    user: dict = Depends(get_current_user_stateful)
):
    """
    Logout - Delete session (easy with stateful auth)
    """
    # Delete from sessions store
    # (In real app, iterate to find by username if needed)
    response.delete_cookie(key="session_id")
    
    return {"message": "Logged out successfully"}
```

### PART 2: STATELESS AUTHENTICATION (JWT)

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from pydantic import BaseModel

# JWT Configuration
SECRET_KEY = "your-secret-key-keep-it-secret"  # Use environment variable in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme (tells FastAPI where to look for token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# User database (in production: real database)
users_db = {
    "alice": {
        "username": "alice",
        "hashed_password": pwd_context.hash("password123"),
        "role": "user",
        "email": "alice@example.com"
    },
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123"),
        "role": "admin",
        "email": "admin@example.com"
    }
}

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    email: str
    role: str

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create JWT token
    
    JWT Structure:
    {
      "header": {"alg": "HS256", "typ": "JWT"},
      "payload": {"sub": "alice", "role": "user", "exp": 1234567890},
      "signature": "cryptographic_signature"
    }
    
    The signature ensures the token hasn't been tampered with
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    
    # Sign the token with SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/token", response_model=Token)
def login_jwt(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    STATELESS AUTHENTICATION - JWT Login
    
    Workflow:
    1. User sends username + password
    2. Server verifies credentials
    3. Server creates JWT with user data (claims)
    4. Server SIGNS JWT with secret key
    5. Server returns JWT to client
    6. Client stores JWT (localStorage, memory)
    7. Client sends JWT in Authorization header: "Bearer <token>"
    8. Server verifies signature - NO DB LOOKUP NEEDED
    
    Pros:
    - Infinite scalability (no DB lookup)
    - Perfect for microservices
    - Any service with SECRET_KEY can verify
    
    Cons:
    - Cannot revoke before expiry
    - Token lives until expiration
    - Changing secret logs out EVERYONE
    """
    # Verify user
    user = users_db.get(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verify password
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user["username"],
            "role": user["role"],
            "email": user["email"]
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

def get_current_user_jwt(token: str = Depends(oauth2_scheme)):
    """
    Dependency: Verify JWT and extract user
    
    This is stateless - no DB lookup!
    Just verifies the cryptographic signature
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        # Decode and verify JWT signature
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        email: str = payload.get("email")
        
        if username is None:
            raise credentials_exception
        
        return User(username=username, email=email, role=role)
    
    except JWTError:
        raise credentials_exception

@app.get("/jwt/protected", response_model=User)
def protected_jwt(current_user: User = Depends(get_current_user_jwt)):
    """
    Protected endpoint with JWT auth
    
    Send request with header:
    Authorization: Bearer <your_jwt_token>
    
    FastAPI automatically:
    1. Extracts token from Authorization header
    2. Verifies signature
    3. Decodes payload
    4. Returns user object
    """
    return current_user

@app.get("/jwt/me")
def read_users_me(current_user: User = Depends(get_current_user_jwt)):
    """Get current user info from JWT"""
    return {
        "message": "JWT verified successfully",
        "user": current_user,
        "auth_type": "stateless (JWT)",
        "note": "No database lookup was performed!"
    }
```

### PART 3: AUTHORIZATION (RBAC)

```python
from fastapi import Depends, HTTPException, status
from enum import Enum

class Role(str, Enum):
    """User roles"""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"

class Permission(str, Enum):
    """Permissions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN_ACCESS = "admin_access"

# Role → Permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN_ACCESS],
    Role.MODERATOR: [Permission.READ, Permission.WRITE, Permission.DELETE],
    Role.USER: [Permission.READ, Permission.WRITE]
}

def require_role(required_role: Role):
    """
    Dependency factory: Require specific role
    
    Usage:
    @app.get("/admin")
    def admin_only(user = Depends(require_role(Role.ADMIN))):
        ...
    """
    def role_checker(current_user: User = Depends(get_current_user_jwt)):
        # Check if user has required role
        user_role = Role(current_user.role)
        
        # Admin can access everything
        if user_role == Role.ADMIN:
            return current_user
        
        # Check specific role
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}"
            )
        
        return current_user
    
    return role_checker

def require_permission(required_permission: Permission):
    """
    Dependency factory: Require specific permission
    
    More granular than roles
    """
    def permission_checker(current_user: User = Depends(get_current_user_jwt)):
        user_role = Role(current_user.role)
        user_permissions = ROLE_PERMISSIONS.get(user_role, [])
        
        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permission.value}"
            )
        
        return current_user
    
    return permission_checker

# Regular endpoint - any authenticated user
@app.get("/notes")
def get_notes(current_user: User = Depends(get_current_user_jwt)):
    """
    Any authenticated user can access
    Returns 401 if not authenticated
    """
    return {
        "notes": ["Note 1", "Note 2"],
        "user": current_user.username
    }

# Moderator or Admin only
@app.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    current_user: User = Depends(require_permission(Permission.DELETE))
):
    """
    Requires DELETE permission
    - USER role: 403 Forbidden
    - MODERATOR role: 200 OK
    - ADMIN role: 200 OK
    """
    return {
        "message": f"Note {note_id} deleted",
        "deleted_by": current_user.username,
        "role": current_user.role
    }

# Admin only - Dead Zone access
@app.get("/admin/dead-zone")
def access_dead_zone(
    current_user: User = Depends(require_role(Role.ADMIN))
):
    """
    Admin-only endpoint - Dead Zone example from lecture
    
    - USER role: 403 Forbidden
    - MODERATOR role: 403 Forbidden
    - ADMIN role: 200 OK
    """
    return {
        "message": "Dead Zone accessed",
        "deleted_notes": ["All deleted notes from all users"],
        "admin": current_user.username,
        "warning": "High-risk operation - admin access only"
    }

# Permission-based endpoint
@app.post("/admin/users/ban")
def ban_user(
    username: str,
    current_user: User = Depends(require_permission(Permission.ADMIN_ACCESS))
):
    """
    Requires ADMIN_ACCESS permission
    Only ADMIN role has this permission
    """
    return {
        "message": f"User {username} banned",
        "banned_by": current_user.username
    }
```

### PART 4: API KEY AUTHENTICATION

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

# API Key storage (in production: database with hashing)
api_keys_db = {
    "sk_test_123456789": {
        "name": "Development Key",
        "user": "alice",
        "permissions": ["read", "write"]
    },
    "sk_live_987654321": {
        "name": "Production Key",
        "user": "service-bot",
        "permissions": ["read"]
    }
}

# Define where to look for API key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    """
    API KEY AUTHENTICATION
    
    Use Case: Machine-to-Machine (M2M) communication
    - Server scripts
    - Automation
    - Third-party integrations
    
    Workflow:
    1. User generates API key in UI
    2. Server stores key in database
    3. Client includes key in header: X-API-Key: sk_test_123456789
    4. Server validates key
    
    Characteristics:
    - Long-lived (months/years)
    - No expiration (until revoked)
    - No user login required
    - For automation, not humans
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # Verify key exists
    key_info = api_keys_db.get(api_key)
    if not key_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return key_info

@app.get("/api/data")
def get_api_data(key_info: dict = Depends(verify_api_key)):
    """
    API endpoint requiring API key
    
    Send request with header:
    X-API-Key: sk_test_123456789
    
    Use for:
    - Programmatic access
    - CI/CD pipelines
    - Scheduled jobs
    - External integrations
    """
    return {
        "data": "Sensitive API data",
        "key_name": key_info["name"],
        "user": key_info["user"],
        "permissions": key_info["permissions"]
    }
```

### PART 5: SECURITY BEST PRACTICES

```python
import time
from fastapi import Request

# SECURITY PRACTICE 1: Generic Error Messages
@app.post("/secure/login")
def secure_login(credentials: LoginRequest):
    """
    SECURITY: Always return generic messages
    
    ❌ BAD:
    - "User not found" → Attacker knows username invalid
    - "Incorrect password" → Attacker knows username valid
    
    ✅ GOOD:
    - "Authentication failed" → No info leaked
    """
    user = users_db.get(credentials.username)
    
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        # SAME message for both cases
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"  # Generic!
        )
    
    return {"message": "Login successful"}

# SECURITY PRACTICE 2: Timing Attack Prevention
@app.post("/secure/timing-safe-login")
def timing_safe_login(credentials: LoginRequest):
    """
    SECURITY: Prevent timing attacks
    
    Problem:
    - If user doesn't exist: instant response (no password check)
    - If user exists: delayed response (password verification)
    - Attacker measures timing to enumerate valid usernames
    
    Solution:
    - Always perform same operations
    - Use constant-time comparison
    - Or add artificial delay
    """
    user = users_db.get(credentials.username)
    
    # Always hash the password (even if user doesn't exist)
    # This equalizes timing
    if not user:
        # Hash dummy password to equalize timing
        pwd_context.hash("dummy_password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    
    # Now verify actual password
    if not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    
    return {"message": "Login successful - timing attack resistant"}

# SECURITY PRACTICE 3: Rate Limiting Login Attempts
login_attempts = {}

@app.post("/secure/rate-limited-login")
def rate_limited_login(request: Request, credentials: LoginRequest):
    """
    SECURITY: Rate limit login attempts
    
    Prevents brute force attacks
    """
    client_ip = request.client.host
    
    # Track attempts
    if client_ip not in login_attempts:
        login_attempts[client_ip] = {"count": 0, "lockout_until": 0}
    
    # Check if locked out
    if time.time() < login_attempts[client_ip]["lockout_until"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later."
        )
    
    # Verify credentials
    user = users_db.get(credentials.username)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        login_attempts[client_ip]["count"] += 1
        
        # Lock out after 5 failed attempts
        if login_attempts[client_ip]["count"] >= 5:
            login_attempts[client_ip]["lockout_until"] = time.time() + 300  # 5 min
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Locked out for 5 minutes."
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
    
    # Success - reset counter
    login_attempts[client_ip] = {"count": 0, "lockout_until": 0}
    return {"message": "Login successful"}
```

---

## 🎯 Practice Exercises

### Exercise 1: Implement Session Auth ✅
```python
# TODO:
# 1. Implement login with session creation
# 2. Store session in dict (simulate Redis)
# 3. Create protected endpoint
# 4. Implement logout (delete session)
# 5. Test with Swagger UI
```

### Exercise 2: Implement JWT Auth ✅
```python
# TODO:
# 1. Create JWT login endpoint
# 2. Generate signed JWT with user data
# 3. Create protected endpoint requiring JWT
# 4. Test token expiration
```

### Exercise 3: RBAC Implementation ✅
```python
# TODO:
# 1. Create 3 roles: user, moderator, admin
# 2. Create role-checking dependencies
# 3. Create endpoints with different role requirements
# 4. Test 403 errors for unauthorized roles
```

### Exercise 4: Security Hardening ✅
```python
# TODO:
# 1. Implement generic error messages
# 2. Add timing attack prevention
# 3. Implement rate limiting
# 4. Add password strength validation
```

### Exercise 5: API Key System ✅
```python
# TODO:
# 1. Create API key generation endpoint
# 2. Store keys in database
# 3. Create API key validation middleware
# 4. Create protected endpoints requiring API key
```

---

## 🎓 Mastery Checklist

Can you:
- [ ] Explain the difference between authentication and authorization?
- [ ] Implement stateful auth with sessions?
- [ ] Implement stateless auth with JWTs?
- [ ] Create and verify JWT tokens?
- [ ] Implement RBAC with roles and permissions?
- [ ] Use FastAPI dependencies for auth?
- [ ] Distinguish between 401 (Unauthorized) and 403 (Forbidden)?
- [ ] Implement API key authentication?
- [ ] Apply security best practices (generic errors, timing attacks)?
- [ ] Choose between stateful vs stateless auth for different use cases?

---

## 💭 Key Insights

### When to Use What
- **Stateful (Sessions)**: Web apps, need to revoke instantly
- **Stateless (JWT)**: APIs, microservices, mobile apps
- **API Keys**: M2M communication, automation
- **OAuth/OIDC**: Third-party login, social auth

### Security Critical Points
1. NEVER return "User not found" vs "Wrong password"
2. ALWAYS use HTTPS in production
3. Use HTTPOnly cookies to prevent XSS
4. Hash passwords with bcrypt (never store plain text)
5. Implement rate limiting on login endpoints
6. JWT: Keep expiry short (15-30 min), use refresh tokens

### 401 vs 403
- **401 Unauthorized**: "I don't know who you are" (no auth token)
- **403 Forbidden**: "I know who you are, but you can't do this" (insufficient role/permission)

---

**Last Updated**: 2026-01-29  
**Status**: 🟡 In Progress  
**Next**: Implement complete auth system with all types
