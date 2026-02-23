"""
Complete Authentication & Authorization Example - FastAPI
Demonstrates all 4 auth types from Lecture 8

Run with: fastapi dev authentication_complete.py
Visit: http://127.0.0.1:8000/docs

Install dependencies:
pip install "fastapi[standard]" python-jose[cryptography] passlib[bcrypt] python-multipart
"""

from fastapi import FastAPI, Depends, HTTPException, status, Cookie, Response, Request, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from enum import Enum
import secrets
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

app = FastAPI(
    title="Authentication & Authorization Complete Example",
    description="All 4 auth types: Stateful, Stateless (JWT), API Keys, and RBAC",
    version="1.0.0"
)

# JWT Configuration
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"  # Change in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# API Key scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ============================================================================
# DATA MODELS
# ============================================================================

class Role(str, Enum):
    """User roles for RBAC"""
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
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN_ACCESS],
    Role.MODERATOR: [Permission.READ, Permission.WRITE, Permission.DELETE],
    Role.USER: [Permission.READ, Permission.WRITE]
}


class UserInDB(BaseModel):
    """User model in database"""
    username: str
    email: EmailStr
    hashed_password: str
    role: Role = Role.USER
    disabled: bool = False

class User(BaseModel):
    """Public user model (no password)"""
    username: str
    email: EmailStr
    role: Role

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    """Login credentials"""
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def username_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        return v.strip()
    
    @field_validator('password')
    @classmethod
    def password_not_empty(cls, v):
        if not v or len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v

class RegisterRequest(BaseModel):
    """Registration data"""
    username: str
    email: EmailStr
    password: str
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

class Note(BaseModel):
    """Note model for RBAC demo"""
    id: int
    title: str
    content: str
    owner: str
    created_at: datetime = datetime.utcnow()

# ============================================================================
# DATA STORAGE (In production: use real database)
# ============================================================================

# Users database
users_db: Dict[str, UserInDB] = {
    "alice": UserInDB(
        username="alice",
        email="alice@example.com",
        hashed_password=pwd_context.hash("Password123"),
        role=Role.USER
    ),
    "bob": UserInDB(
        username="bob",
        email="bob@example.com",
        hashed_password=pwd_context.hash("Password123"),
        role=Role.MODERATOR
    ),
    "admin": UserInDB(
        username="admin",
        email="admin@example.com",
        hashed_password=pwd_context.hash("Admin123"),
        role=Role.ADMIN
    )
}

# Sessions database (simulates Redis)
sessions_db: Dict[str, dict] = {}

# Notes database
notes_db: Dict[int, Note] = {
    1: Note(id=1, title="Alice's Note", content="My first note", owner="alice"),
    2: Note(id=2, title="Bob's Note", content="Moderator note", owner="bob"),
}

# Deleted notes (Dead Zone)
deleted_notes_db: Dict[int, Note] = {}

# API Keys database
api_keys_db = {
    "sk_test_1234567890abcdef": {
        "name": "Development Key",
        "user": "alice",
        "created_at": datetime.utcnow(),
        "permissions": ["read", "write"]
    },
    "sk_live_abcdef1234567890": {
        "name": "Production Key", 
        "user": "service-bot",
        "created_at": datetime.utcnow(),
        "permissions": ["read"]
    }
}

# Rate limiting storage
login_attempts: Dict[str, dict] = {}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """
    Authenticate user with username and password
    Returns user if valid, None otherwise
    
    SECURITY: This function takes the same time regardless of whether
    user exists or not (prevents timing attacks)
    """
    user = users_db.get(username)
    
    if not user:
        # Hash a dummy password to equalize timing
        pwd_context.hash("dummy_password_for_timing")
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    if user.disabled:
        return None
    
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT token
    
    JWT Structure:
    {
      "header": {"alg": "HS256", "typ": "JWT"},
      "payload": {"sub": "alice", "role": "user", "exp": 1234567890},
      "signature": "cryptographic_signature_here"
    }
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ============================================================================
# SECTION 1: STATEFUL AUTHENTICATION (SESSION-BASED)
# ============================================================================

@app.post("/auth/stateful/register")
def register_stateful(user_data: RegisterRequest):
    """
    Register new user
    """
    if user_data.username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Create new user
    new_user = UserInDB(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=Role.USER
    )
    
    users_db[user_data.username] = new_user
    
    return {
        "message": "User registered successfully",
        "username": user_data.username,
        "email": user_data.email
    }

@app.post("/auth/stateful/login")
def login_stateful(
    credentials: LoginRequest,
    response: Response,
    request: Request
):
    """
    STATEFUL AUTHENTICATION - Session-Based Login
    
    Workflow:
    1. User sends username + password
    2. Server verifies credentials
    3. Server generates random Session ID
    4. Server stores session data in Redis/database
    5. Server sends Session ID in HTTPOnly cookie
    6. Browser automatically includes cookie in future requests
    7. Server looks up session to verify user
    
    Pros:
    - Easy to revoke (just delete from Redis)
    - Centralized control over all sessions
    - Can see all active sessions
    
    Cons:
    - Requires database lookup for every request
    - Harder to scale across multiple servers/regions
    - Need Redis or similar for session storage
    """
    # Rate limiting check
    client_ip = request.client.host
    if client_ip in login_attempts:
        attempts = login_attempts[client_ip]
        if attempts["count"] >= 5 and time.time() < attempts["lockout_until"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Try again in 5 minutes."
            )
    
    # Authenticate user
    user = authenticate_user(credentials.username, credentials.password)
    
    if not user:
        # Track failed attempt
        if client_ip not in login_attempts:
            login_attempts[client_ip] = {"count": 0, "lockout_until": 0}
        
        login_attempts[client_ip]["count"] += 1
        
        if login_attempts[client_ip]["count"] >= 5:
            login_attempts[client_ip]["lockout_until"] = time.time() + 300  # 5 minutes
        
        # SECURITY: Generic error message (prevents user enumeration)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"  # Don't say "user not found" or "wrong password"!
        )
    
    # Success - reset rate limiting
    if client_ip in login_attempts:
        login_attempts[client_ip] = {"count": 0, "lockout_until": 0}
    
    # Generate random session ID
    session_id = secrets.token_urlsafe(32)
    
    # Store session in "Redis" (here just a dict)
    sessions_db[session_id] = {
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "created_at": datetime.utcnow().isoformat(),
        "ip": client_ip
    }
    
    # Set HTTPOnly cookie (JavaScript cannot access it - XSS protection)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,      # Prevents XSS attacks
        secure=False,       # Set True in production (HTTPS only)
        samesite="lax",     # CSRF protection
        max_age=1800        # 30 minutes
    )
    
    return {
        "message": "Login successful",
        "auth_type": "stateful (session-based)",
        "user": user.username,
        "role": user.role.value,
        "session_id": session_id[:16] + "...",  # Truncated for display
        "note": "Session ID stored in HTTPOnly cookie"
    }

def get_current_user_stateful(session_id: Optional[str] = Cookie(None)) -> User:
    """
    Dependency: Extract current user from session cookie
    
    This is called automatically by FastAPI for any endpoint
    that has: user = Depends(get_current_user_stateful)
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - no session cookie"
        )
    
    # Look up session in Redis/database
    session = sessions_db.get(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    # Return user info from session
    return User(
        username=session["username"],
        email=session["email"],
        role=Role(session["role"])
    )

@app.get("/auth/stateful/me")
def read_users_me_stateful(current_user: User = Depends(get_current_user_stateful)):
    """
    Get current user info (stateful auth)
    
    Requires valid session cookie
    FastAPI automatically extracts session_id from cookie
    """
    return {
        "message": "Authenticated via session",
        "user": current_user,
        "auth_type": "stateful"
    }

@app.post("/auth/stateful/logout")
def logout_stateful(
    response: Response,
    session_id: Optional[str] = Cookie(None)
):
    """
    Logout - Delete session
    
    This is easy with stateful auth!
    Just delete the session from Redis
    """
    if session_id and session_id in sessions_db:
        del sessions_db[session_id]
    
    # Clear cookie
    response.delete_cookie(key="session_id")
    
    return {
        "message": "Logged out successfully",
        "note": "Session deleted from server"
    }

@app.get("/auth/stateful/sessions")
def list_sessions(current_user: User = Depends(get_current_user_stateful)):
    """
    List all active sessions (only for demo - admin only in production)
    
    This shows the power of stateful auth:
    You can see ALL active sessions and revoke them!
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only"
        )
    
    return {
        "total_sessions": len(sessions_db),
        "sessions": [
            {
                "username": session["username"],
                "role": session["role"],
                "created_at": session["created_at"],
                "ip": session["ip"]
            }
            for session in sessions_db.values()
        ]
    }

# ============================================================================
# SECTION 2: STATELESS AUTHENTICATION (JWT / TOKEN-BASED)
# ============================================================================

@app.post("/token", response_model=Token)
def login_jwt(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    STATELESS AUTHENTICATION - JWT Login
    
    Workflow:
    1. User sends username + password
    2. Server verifies credentials
    3. Server creates JWT token with user data (payload/claims)
    4. Server SIGNS token with SECRET_KEY
    5. Server returns token to client
    6. Client stores token (localStorage, memory, secure storage)
    7. Client sends token in Authorization header: "Bearer <token>"
    8. Server verifies signature - NO DATABASE LOOKUP!
    
    Pros:
    - Infinite scalability (no DB lookup per request)
    - Perfect for microservices (any service can verify)
    - Stateless - no server memory needed
    - Great for mobile apps and SPAs
    
    Cons:
    - Cannot revoke token before expiry
    - If token is stolen, it's valid until expiration
    - To revoke one user, must change SECRET_KEY (logs everyone out)
    - Or implement blacklist (reintroduces state)
    """
    # Authenticate user
    user = authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",  # Generic message
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create JWT token with user data
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,      # Subject (username)
            "email": user.email,
            "role": user.role.value,
            "type": "access"
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

def get_current_user_jwt(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency: Verify JWT and extract user
    
    This is STATELESS - no database lookup!
    Just verifies the cryptographic signature
    
    If signature is valid, we trust the token's payload
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        # Decode JWT and verify signature
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract user data from payload
        username: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")
        
        if username is None:
            raise credentials_exception
        
        # Return user (no DB lookup needed!)
        return User(username=username, email=email, role=Role(role))
    
    except JWTError:
        raise credentials_exception

@app.get("/auth/jwt/me")
def read_users_me_jwt(current_user: User = Depends(get_current_user_jwt)):
    """
    Get current user info (JWT auth)
    
    Send request with header:
    Authorization: Bearer <your_jwt_token>
    
    Try in Swagger UI: Click "Authorize" button, enter token
    """
    return {
        "message": "Authenticated via JWT",
        "user": current_user,
        "auth_type": "stateless (JWT)",
        "note": "No database lookup was performed to verify this!"
    }

@app.get("/auth/jwt/verify")
def verify_jwt_token(token: str):
    """
    Manually verify a JWT token (for demonstration)
    
    Shows what's inside the token without the Depends()
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "valid": True,
            "payload": payload,
            "expires_at": datetime.fromtimestamp(payload["exp"]).isoformat(),
            "note": "Token is cryptographically signed and valid"
        }
    except JWTError as e:
        return {
            "valid": False,
            "error": str(e),
            "note": "Token signature is invalid or token is expired"
        }

# ============================================================================
# SECTION 3: AUTHORIZATION (RBAC - ROLE-BASED ACCESS CONTROL)
# ============================================================================

def require_role(*required_roles: Role):
    """
    Dependency factory: Require one of the specified roles
    
    Usage:
    @app.get("/admin")
    def admin_only(user = Depends(require_role(Role.ADMIN))):
        ...
    """
    def role_checker(current_user: User = Depends(get_current_user_jwt)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {[r.value for r in required_roles]}"
            )
        return current_user
    
    return role_checker

def require_permission(required_permission: Permission):
    """
    Dependency factory: Require specific permission
    
    More granular than roles - checks if user's role has the permission
    """
    def permission_checker(current_user: User = Depends(get_current_user_jwt)):
        user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
        
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
    Get all notes (any authenticated user)
    
    Returns:
    - 401 if not authenticated (no token or invalid token)
    - 200 if authenticated (returns user's notes)
    """
    # Filter notes by owner
    user_notes = [note for note in notes_db.values() if note.owner == current_user.username]
    
    return {
        "notes": user_notes,
        "count": len(user_notes),
        "user": current_user.username,
        "role": current_user.role.value
    }

@app.post("/notes")
def create_note(
    title: str,
    content: str,
    current_user: User = Depends(get_current_user_jwt)
):
    """
    Create a note (requires authentication + WRITE permission)
    
    All roles have WRITE permission, so any authenticated user can create
    """
    note_id = max(notes_db.keys()) + 1 if notes_db else 1
    
    new_note = Note(
        id=note_id,
        title=title,
        content=content,
        owner=current_user.username
    )
    
    notes_db[note_id] = new_note
    
    return {
        "message": "Note created",
        "note": new_note
    }

@app.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    current_user: User = Depends(require_permission(Permission.DELETE))
):
    """
    Delete a note (requires DELETE permission)
    
    Permission check:
    - USER role: 403 Forbidden (no DELETE permission)
    - MODERATOR role: 200 OK (has DELETE permission)
    - ADMIN role: 200 OK (has DELETE permission)
    """
    if note_id not in notes_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    note = notes_db[note_id]
    
    # Move to deleted notes (Dead Zone)
    deleted_notes_db[note_id] = note
    del notes_db[note_id]
    
    return {
        "message": "Note deleted and moved to Dead Zone",
        "note_id": note_id,
        "deleted_by": current_user.username,
        "role": current_user.role.value
    }

@app.get("/admin/dead-zone")
def access_dead_zone(
    current_user: User = Depends(require_role(Role.ADMIN))
):
    """
    ADMIN ONLY - Access Dead Zone (deleted notes from ALL users)
    
    This is the example from your lecture!
    
    Role check:
    - USER role: 403 Forbidden
    - MODERATOR role: 403 Forbidden
    - ADMIN role: 200 OK
    
    Use case:
    - Compliance (need to access deleted data)
    - Storage management
    - Audit purposes
    """
    return {
        "message": "Dead Zone accessed",
        "deleted_notes": list(deleted_notes_db.values()),
        "count": len(deleted_notes_db),
        "admin": current_user.username,
        "warning": "⚠️ High-risk operation - admin access only"
    }

@app.post("/admin/users/{username}/disable")
def disable_user(
    username: str,
    current_user: User = Depends(require_permission(Permission.ADMIN_ACCESS))
):
    """
    Disable a user account (requires ADMIN_ACCESS permission)
    
    Only ADMIN role has ADMIN_ACCESS permission
    """
    if username not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    users_db[username].disabled = True
    
    return {
        "message": f"User {username} disabled",
        "disabled_by": current_user.username
    }

@app.get("/rbac/demo")
def rbac_demo(current_user: User = Depends(get_current_user_jwt)):
    """
    Show RBAC in action - display user's role and permissions
    """
    user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
    
    return {
        "user": current_user.username,
        "role": current_user.role.value,
        "permissions": [p.value for p in user_permissions],
        "can_access": {
            "/notes (GET)": True,  # All authenticated users
            "/notes (POST)": Permission.WRITE in user_permissions,
            "/notes/{id} (DELETE)": Permission.DELETE in user_permissions,
            "/admin/dead-zone": Permission.ADMIN_ACCESS in user_permissions
        }
    }

# ============================================================================
# SECTION 4: API KEY AUTHENTICATION
# ============================================================================

def verify_api_key(api_key: str = Security(api_key_header)) -> dict:
    """
    API KEY AUTHENTICATION
    
    Use Case: Machine-to-Machine (M2M) communication
    - Server-to-server requests
    - Automation scripts
    - CI/CD pipelines
    - Cron jobs
    - Third-party integrations
    
    Characteristics:
    - Long-lived (months/years)
    - No expiration (until manually revoked)
    - No login required
    - For automation, not humans
    - Simple header-based auth
    
    Workflow:
    1. User generates API key in dashboard
    2. Server stores key (hashed) in database
    3. Client includes key in header: X-API-Key: sk_test_123...
    4. Server validates key
    5. Server tracks usage/quotas per key
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include X-API-Key header."
        )
    
    # Validate key (in production: hash and compare)
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
    X-API-Key: sk_test_1234567890abcdef
    
    Use for:
    - Programmatic access (not browser)
    - Automation scripts
    - Server-to-server communication
    - CI/CD pipelines
    """
    return {
        "data": "Sensitive API data",
        "auth_type": "api_key",
        "key_name": key_info["name"],
        "key_user": key_info["user"],
        "permissions": key_info["permissions"],
        "note": "This is for M2M communication, not human users"
    }

@app.post("/api/process")
def process_data(
    data: dict,
    key_info: dict = Depends(verify_api_key)
):
    """
    API endpoint with write access
    
    Requires API key with "write" permission
    """
    if "write" not in key_info["permissions"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This API key does not have write permission"
        )
    
    return {
        "message": "Data processed",
        "data": data,
        "processed_by": key_info["user"]
    }

@app.get("/api/keys/list")
def list_api_keys(current_user: User = Depends(require_role(Role.ADMIN))):
    """
    List all API keys (admin only)
    
    In production, this would show keys for the current user
    """
    return {
        "keys": [
            {
                "key": key[:20] + "...",  # Truncated
                "name": info["name"],
                "user": info["user"],
                "created_at": info["created_at"].isoformat(),
                "permissions": info["permissions"]
            }
            for key, info in api_keys_db.items()
        ]
    }

# ============================================================================
# SECTION 5: SECURITY DEMONSTRATIONS
# ============================================================================

@app.post("/security/timing-attack-vulnerable")
def vulnerable_login(credentials: LoginRequest):
    """
    ❌ VULNERABLE to timing attacks
    
    Problem: Response time differs based on whether user exists
    - User doesn't exist: Instant response (no password check)
    - User exists: Delayed response (password hashing/comparison)
    
    Attacker can enumerate valid usernames by measuring response times!
    
    DO NOT USE THIS IN PRODUCTION!
    """
    user = users_db.get(credentials.username)
    
    # Fast path if user doesn't exist
    if not user:
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    # Slow path - password verification
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    return {"message": "Login successful"}

@app.post("/security/timing-attack-safe")
def safe_login(credentials: LoginRequest):
    """
    ✅ SAFE from timing attacks
    
    Solution: Always perform the same operations
    - Hash dummy password even if user doesn't exist
    - This equalizes response time
    - Attacker cannot distinguish between "user not found" and "wrong password"
    """
    user = users_db.get(credentials.username)
    
    if not user:
        # Hash dummy password to equalize timing
        pwd_context.hash("dummy_password_to_equalize_timing")
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    # Now verify actual password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    return {"message": "Login successful"}

@app.post("/security/user-enumeration-bad")
def bad_error_messages(credentials: LoginRequest):
    """
    ❌ BAD - Reveals whether username exists
    
    Attacker can enumerate all usernames!
    
    DO NOT USE THIS!
    """
    user = users_db.get(credentials.username)
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")  # ❌ BAD!
    
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password")  # ❌ BAD!
    
    return {"message": "Login successful"}

@app.post("/security/user-enumeration-good")
def good_error_messages(credentials: LoginRequest):
    """
    ✅ GOOD - Generic error message
    
    Attacker cannot distinguish between:
    - Username doesn't exist
    - Username exists but wrong password
    
    USE THIS!
    """
    user = authenticate_user(credentials.username, credentials.password)
    
    if not user:
        # Generic message - no info leaked!
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    return {"message": "Login successful"}

# ============================================================================
# SECTION 6: COMPARISON & INFO ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """API overview and documentation"""
    return {
        "message": "Authentication & Authorization Complete API",
        "documentation": "/docs",
        "auth_types": {
            "stateful": {
                "login": "POST /auth/stateful/login",
                "protected": "GET /auth/stateful/me",
                "logout": "POST /auth/stateful/logout",
                "use_case": "Web applications with sessions"
            },
            "stateless_jwt": {
                "login": "POST /token",
                "protected": "GET /auth/jwt/me",
                "use_case": "APIs, mobile apps, SPAs"
            },
            "api_key": {
                "endpoint": "GET /api/data",
                "header": "X-API-Key: sk_test_1234567890abcdef",
                "use_case": "Machine-to-machine communication"
            },
            "rbac": {
                "demo": "GET /rbac/demo",
                "admin_only": "GET /admin/dead-zone",
                "use_case": "Permission-based access control"
            }
        },
        "test_users": {
            "alice": {"password": "Password123", "role": "user"},
            "bob": {"password": "Password123", "role": "moderator"},
            "admin": {"password": "Admin123", "role": "admin"}
        },
        "test_api_keys": {
            "dev_key": "sk_test_1234567890abcdef",
            "prod_key": "sk_live_abcdef1234567890"
        }
    }

@app.get("/auth/compare")
def compare_auth_types():
    """
    Compare all authentication types
    
    When to use what?
    """
    return {
        "comparison": {
            "stateful_sessions": {
                "pros": [
                    "Easy to revoke (delete from Redis)",
                    "Centralized control",
                    "Can see all active sessions",
                    "Instant logout on all devices"
                ],
                "cons": [
                    "Database lookup every request",
                    "Harder to scale across regions",
                    "Need Redis or session store"
                ],
                "use_cases": [
                    "Traditional web applications",
                    "When you need instant revocation",
                    "When you need to see all active sessions"
                ],
                "example": "SaaS admin dashboards"
            },
            "stateless_jwt": {
                "pros": [
                    "No database lookup (infinitely scalable)",
                    "Perfect for microservices",
                    "Self-contained (includes user data)",
                    "Great for mobile apps"
                ],
                "cons": [
                    "Cannot revoke before expiry",
                    "Stolen token is valid until expiration",
                    "Need refresh token strategy"
                ],
                "use_cases": [
                    "REST APIs",
                    "Mobile applications",
                    "Microservices architecture",
                    "SPAs (Single Page Applications)"
                ],
                "example": "Mobile app backends, API gateways"
            },
            "api_keys": {
                "pros": [
                    "Simple to implement",
                    "Long-lived (no login needed)",
                    "Perfect for automation"
                ],
                "cons": [
                    "No expiration (until revoked)",
                    "All-or-nothing access",
                    "If leaked, valid forever"
                ],
                "use_cases": [
                    "Server-to-server communication",
                    "CI/CD pipelines",
                    "Automation scripts",
                    "Third-party integrations"
                ],
                "example": "OpenAI API, Stripe API"
            }
        },
        "decision_tree": {
            "web_app_with_users": "Use Stateful (sessions)",
            "mobile_app": "Use Stateless (JWT)",
            "public_api": "Use Stateless (JWT)",
            "internal_microservices": "Use Stateless (JWT) or mTLS",
            "automation_scripts": "Use API Keys",
            "social_login": "Use OAuth/OIDC (future topic)"
        }
    }

@app.get("/auth/status")
def auth_status():
    """System status"""
    return {
        "status": "operational",
        "active_sessions": len(sessions_db),
        "registered_users": len(users_db),
        "api_keys": len(api_keys_db),
        "notes_count": len(notes_db),
        "deleted_notes_count": len(deleted_notes_db)
    }

# ============================================================================
# RUN INSTRUCTIONS
# ============================================================================
"""
SETUP:
1. Install dependencies:
   pip install "fastapi[standard]" python-jose[cryptography] passlib[bcrypt] python-multipart

2. Run the server:
   fastapi dev authentication_complete.py

3. Open browser:
   http://127.0.0.1:8000/docs

TEST STATEFUL AUTH (Sessions):
1. POST /auth/stateful/login
   Body: {"username": "alice", "password": "Password123"}
   → Sets session cookie

2. GET /auth/stateful/me
   → Uses cookie automatically (no header needed!)

3. POST /auth/stateful/logout
   → Deletes session

TEST STATELESS AUTH (JWT):
1. POST /token
   Body: username=alice&password=Password123 (form data)
   → Returns JWT token

2. Click "Authorize" button in Swagger UI
   Enter: <paste_your_token>

3. GET /auth/jwt/me
   → Uses token from Authorization header

TEST RBAC:
1. Login as alice (user role)
   Try DELETE /notes/1
   → 403 Forbidden (no DELETE permission)

2. Login as bob (moderator role)
   Try DELETE /notes/1
   → 200 OK (has DELETE permission)

3. Login as admin
   Try GET /admin/dead-zone
   → 200 OK (admin only)

TEST API KEY:
GET /api/data
Header: X-API-Key: sk_test_1234567890abcdef
→ 200 OK

COMPARE AUTH TYPES:
GET /auth/compare
→ See when to use each type
"""
