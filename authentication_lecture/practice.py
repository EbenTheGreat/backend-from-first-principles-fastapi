from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, Cookie
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm, APIKeyHeader
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict
from datetime import datetime, timedelta, UTC
from enum import Enum
from passlib.context import CryptContext
import secrets 
import time
from pyjwt import jwt


# ============================================================================
# CONFIGURATION
# ============================================================================
app = FastAPI(
    title="Authentication and Authorization practice",
    description="All 4 auth types: Stateful, Stateless (JWT), API Keys, and RBAC",
    version="1.0.0"
)

# JWT Configuration
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# API Key scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ============================================================================
# DATA MODELS
# ============================================================================
class Role(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"

class Permissions(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN_ACCESS = "admin_access"


ROLE_PERMISSIONS: Dict[Role, List[Permissions]] = {
    Role.ADMIN: [Permissions.READ, Permissions.WRITE, Permissions.DELETE, Permissions.ADMIN_ACCESS],
    Role.MODERATOR: [Permissions.READ, Permissions.WRITE, Permissions.DELETE], 
    Role.USER: [Permissions.READ, Permissions.WRITE]
}


class UserInDB(BaseModel):
    """User model in database"""
    username: str
    email: EmailStr
    hashed_password: str
    role: Role = Role.USER
    disabled: bool = False


class User(BaseModel):
    """Public User Model (No Password)"""
    username: str
    email: EmailStr
    role: Role = Role.USER


class Token(BaseModel):
    """JWT Token Response"""
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    """Login credentials"""
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v):
        if not v or len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class RegisterRequest(BaseModel):
    """Registration data"""
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(not char.isalnum() for char in v):
            raise ValueError("Password must contain at least one special character (e.g. @, !, #, $)")
        return v


class Note(BaseModel):
    """Note model for RBAC demo"""
    id: int
    title: str
    content: str
    owner: str
    created_at: datetime = datetime.now(UTC)

# ============================================================================
# DATA STORAGE (In production: use real database)
# ============================================================================

# Users database
users_db: Dict[str, UserInDB] = {
    "tony": UserInDB(
        username="tony",
        email="tonygee@gmail.com",
        hashed_password=pwd_context.hash("tonygee"),
        role= Role.USER,
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
    1: Note(id=1, title="Tony's Note", content="My first note", owner="tony"),
    2: Note(id=2, title="Bob's Note", content="Moderator note", owner="bob"),
}

# Deleted notes (Dead Zone)
deleted_notes_db: Dict[int, Note] = {}


# API Keys database
api_keys_db = {
    "sk_test_1234567890abcdef": {
        "name": "Development Key",
        "user": "tony",
        "created_at": datetime.now(UTC),
        "permissions": ["read", "write"]
    },
    "sk_live_abcdef1234567890": {
        "name": "Production Key", 
        "user": "service-bot",
        "created_at": datetime.now(UTC),
        "permissions": ["read"]
    }
}

# Rate limiting storage
login_attempts: Dict[str, dict] = {}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """hash a password"""
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
    to_encode= data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify JWT token
    Returns payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ============================================================================
# SECTION 1: STATEFUL AUTHENTICATION (SESSION-BASED)
# ============================================================================
@app.post("/auth/stateful/register")
async def register_user(user_data: RegisterRequest):
    """
    Register new user
    """
    if user_data.username in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Create new user
    new_user= UserInDB(
        username= user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role= Role.USER
    )

    users_db[user_data.username] = new_user
    return {
        "message": "user registered successfully",
        "username": user_data.username,
        "email": user_data.email
    }


@app.post("/auth/stateful/login")
async def user_login(
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

    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        # Track failed attempts
        if client_ip not in login_attempts:
            login_attempts[client_ip] = {"count": 0, "lockout_until": 0}
        login_attempts[client_ip]["count"] += 1

        if login_attempts[client_ip]["count"] >= 5:
            login_attempts[client_ip]["lockout_until"] = time.time() + 300
        
        # SECURITY: Generic error message (prevents user enumeration)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"  # Don't say "user not found" or "wrong password"!
        )

    # Success - reset rate limiting
    if client_ip in login_attempts:
        login_attempts[client_ip] = {"count": 0, "lockout_until": 0}

    # Generate a random session_id
    session_id = secrets.token_urlsafe(32)

    # Store Session in Redis
    sessions_db[session_id] = {
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "created_at": datetime.now(UTC),
        "ip": client_ip
    }

    # Set HTTPOnly cookie (JavaScript cannot access it - XSS protection)
    response.set_cookie(
        key="sessions_id",
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



def get_current_user_stateful(session_id: Optional[str]= Cookie(None)) -> User:
    """
    Dependency: Extract current user from session cookie
    
    This is called automatically by FastAPI for any endpoint
    that has: user = Depends(get_current_user_stateful)
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Not Authenticated"
        )

    # Look up session in Redis/database
    session = sessions_db.get(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )

    # Return User Info from session
    return User(
        username=session["username"],
        email=session["email"],
        role=Role(session["role"])
    )


@app.get("/auth/stateful/me")
def read_user_stateful(current_user: User=Depends(get_current_user_stateful)):
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
    """
    # Authenticate user
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

    # Create JWT Token with user data
    access_token_expires = timedelta(minutes=20)
    access_token = create_access_token(
        data={
        "sub": user.username,
        "email": user.email,
        "role": user.role.value,
        "type": "access"
        },
        expires_delta= access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def get_current_user_jwt(token: str= Depends(oauth2_scheme)) -> User:
    """
    Dependency: Verify JWT and extract user
    
    This is STATELESS - no database lookup!
    Just verifies the cryptographic signature
    
    If signature is valid, we trust the token's payload
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        # Decode JWT and verify signature
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)

        # Extract user data from payload
        username: str= payload.get("sub")
        email: str= payload.get("email")
        role: str= payload.get("role")

        if username is None:
            raise credentials_exception

        # Return User
        return User(username=username, email=email, role=Role(role))
    except JWTError:
        raise credentials_exception
















    