"""
Complete Backend Architecture Example - FastAPI
Demonstrates all 5 components from Lecture 10:
1. Handler/Controller
2. Service Layer
3. Repository Layer
4. Middleware
5. Request Context

Run with: fastapi dev architecture_complete.py
Visit: http://127.0.0.1:8000/docs

Install dependencies:
pip install "fastapi[standard]" sqlalchemy passlib[bcrypt] python-jose[cryptography]
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose import jwt, JWTError
from typing import Optional, List
from datetime import datetime, timedelta
import time
import uuid
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

# Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./architecture_demo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# JWT
SECRET_KEY = "your-secret-key-keep-it-safe"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE MODELS (SQLAlchemy)
# ============================================================================

class UserModel(Base):
    """User database model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user")
    
    # Relationships
    books = relationship("BookModel", back_populates="owner", cascade="all, delete-orphan")

class BookModel(Base):
    """Book database model"""
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    owner = relationship("UserModel", back_populates="books")

# Create tables
Base.metadata.create_all(bind=engine)

# ============================================================================
# PYDANTIC MODELS (API Schemas)
# ============================================================================

class UserCreate(BaseModel):
    """Schema for creating a user"""
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """Schema for user response"""
    id: int
    username: str
    email: str
    role: str
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """Schema for login"""
    username: str
    password: str

class Token(BaseModel):
    """Schema for JWT token"""
    access_token: str
    token_type: str

class BookCreate(BaseModel):
    """Schema for creating a book"""
    title: str
    author: str

class BookResponse(BaseModel):
    """Schema for book response"""
    id: int
    title: str
    author: str
    owner_id: int
    
    class Config:
        from_attributes = True

# ============================================================================
# COMPONENT 5: REQUEST CONTEXT (Shared State)
# ============================================================================

class RequestContext:
    """
    REQUEST CONTEXT - Component 5
    
    Purpose:
    - Shared state scoped to single request
    - Stores TRUSTED metadata (User ID from auth middleware)
    - Prevents identity spoofing
    - Available to all middleware and handlers
    
    Security Pattern:
    - Auth middleware verifies JWT → extracts user_id → stores in context
    - Handler reads from context (TRUSTED)
    - Handler ignores user_id in request body (UNTRUSTED)
    """
    
    def __init__(self):
        self.user_id: Optional[int] = None
        self.username: Optional[str] = None
        self.role: Optional[str] = None
        self.request_id: Optional[str] = None
        self.start_time: Optional[float] = None
    
    @classmethod
    def from_request(cls, request: Request) -> "RequestContext":
        """Get or create context from request state"""
        if not hasattr(request.state, "context"):
            request.state.context = cls()
        return request.state.context

def get_context(request: Request) -> RequestContext:
    """
    Dependency: Get request context
    
    Usage in handlers:
    def handler(context: RequestContext = Depends(get_context)):
        user_id = context.user_id  # TRUSTED from auth
    """
    return RequestContext.from_request(request)

# ============================================================================
# COMPONENT 3: REPOSITORY LAYER (Database Access)
# ============================================================================

class UserRepository:
    """
    REPOSITORY LAYER - Component 3
    
    Responsibility: Database operations ONLY
    - Constructs SQL queries
    - Executes queries
    - Returns raw database models
    
    Does NOT:
    - Contain business logic
    - Know about HTTP
    - Make business decisions
    
    Design Rule: One method = One purpose (Granularity)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, username: str, email: str, hashed_password: str) -> UserModel:
        """
        Create user in database
        
        One purpose: INSERT new user
        """
        db_user = UserModel(
            username=username,
            email=email,
            hashed_password=hashed_password
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def get_user_by_id(self, user_id: int) -> Optional[UserModel]:
        """
        Get user by ID
        
        Separate method (not combined with get_all_users)
        """
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[UserModel]:
        """
        Get user by username
        
        Different query type = different method
        """
        return self.db.query(UserModel).filter(UserModel.username == username).first()
    
    def get_all_users(self) -> List[UserModel]:
        """
        Get all users
        
        Separate method (granularity rule)
        """
        return self.db.query(UserModel).all()
    
    def update_user_role(self, user_id: int, role: str) -> Optional[UserModel]:
        """Update user role"""
        user = self.get_user_by_id(user_id)
        if user:
            user.role = role
            self.db.commit()
            self.db.refresh(user)
        return user

class BookRepository:
    """Book repository"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_book(self, title: str, author: str, owner_id: int) -> BookModel:
        """Create book"""
        db_book = BookModel(title=title, author=author, owner_id=owner_id)
        self.db.add(db_book)
        self.db.commit()
        self.db.refresh(db_book)
        return db_book
    
    def get_book_by_id(self, book_id: int) -> Optional[BookModel]:
        """Get book by ID"""
        return self.db.query(BookModel).filter(BookModel.id == book_id).first()
    
    def get_books_by_owner(self, owner_id: int) -> List[BookModel]:
        """Get all books for an owner"""
        return self.db.query(BookModel).filter(BookModel.owner_id == owner_id).all()
    
    def get_all_books(self) -> List[BookModel]:
        """Get all books"""
        return self.db.query(BookModel).all()
    
    def delete_book(self, book_id: int) -> bool:
        """Delete book"""
        book = self.get_book_by_id(book_id)
        if book:
            self.db.delete(book)
            self.db.commit()
            return True
        return False

# ============================================================================
# COMPONENT 2: SERVICE LAYER (Business Logic)
# ============================================================================

class UserService:
    """
    SERVICE LAYER - Component 2
    
    Responsibility: Business Logic & Orchestration
    - Contains actual processing
    - Protocol-agnostic (no HTTP knowledge)
    - Orchestrates repositories
    - Handles side effects (emails, external APIs)
    
    Design Rule: "Just a function"
    - Takes native Python types
    - Returns native Python types
    - Can be used in CLI, background jobs, APIs
    """
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    def register_user(self, username: str, email: str, password: str) -> UserModel:
        """
        BUSINESS LOGIC: Register new user
        
        Steps:
        1. Check if username exists (business rule)
        2. Check if email exists (business rule)
        3. Hash password (security)
        4. Create user (delegate to repository)
        5. Send welcome email (side effect - simulated)
        
        Note: Protocol-agnostic! No HTTP knowledge.
        """
        # Business rule: Check uniqueness
        existing = self.user_repo.get_user_by_username(username)
        if existing:
            raise ValueError(f"Username '{username}' already exists")
        
        # Hash password (security)
        hashed_password = pwd_context.hash(password)
        
        # Delegate to repository
        user = self.user_repo.create_user(username, email, hashed_password)
        
        # Side effect: Send email (simulated)
        logger.info(f"📧 Welcome email sent to {email}")
        
        return user
    
    def authenticate(self, username: str, password: str) -> Optional[UserModel]:
        """
        BUSINESS LOGIC: Authenticate user
        
        Returns user if credentials valid, None otherwise
        """
        user = self.user_repo.get_user_by_username(username)
        
        if not user:
            return None
        
        if not pwd_context.verify(password, user.hashed_password):
            return None
        
        return user
    
    def get_user_profile(self, user_id: int) -> Optional[UserModel]:
        """
        BUSINESS LOGIC: Get user profile
        
        Simple case: delegates to repository
        Complex case: could orchestrate multiple repos
        (e.g., merge user + orders + preferences)
        """
        return self.user_repo.get_user_by_id(user_id)
    
    def promote_to_admin(self, user_id: int, requesting_user_id: int) -> UserModel:
        """
        BUSINESS LOGIC: Promote user to admin
        
        Business Rules:
        1. Requesting user must be admin
        2. Target user must exist
        3. Can't change your own role
        """
        # Check permissions
        requesting_user = self.user_repo.get_user_by_id(requesting_user_id)
        if not requesting_user or requesting_user.role != "admin":
            raise PermissionError("Only admins can promote users")
        
        # Check target exists
        target_user = self.user_repo.get_user_by_id(user_id)
        if not target_user:
            raise ValueError(f"User {user_id} not found")
        
        # Business rule: Can't change own role
        if user_id == requesting_user_id:
            raise ValueError("Cannot change your own role")
        
        # Delegate to repository
        return self.user_repo.update_user_role(user_id, "admin")

class BookService:
    """Book service with business logic"""
    
    def __init__(self, book_repo: BookRepository, user_repo: UserRepository):
        self.book_repo = book_repo
        self.user_repo = user_repo
    
    def create_book(self, title: str, author: str, owner_id: int) -> BookModel:
        """
        BUSINESS LOGIC: Create a book
        
        Business Rules:
        1. Owner must exist
        2. Future: Could add limits (e.g., max 100 books per user)
        """
        # Business rule: Owner must exist
        owner = self.user_repo.get_user_by_id(owner_id)
        if not owner:
            raise ValueError(f"User {owner_id} not found")
        
        # Delegate to repository
        book = self.book_repo.create_book(title, author, owner_id)
        
        # Side effect: Log creation
        logger.info(f"📚 Book '{title}' created by {owner.username}")
        
        return book
    
    def get_user_books(self, user_id: int) -> List[BookModel]:
        """Get all books for a user"""
        return self.book_repo.get_books_by_owner(user_id)
    
    def delete_book(self, book_id: int, requesting_user_id: int) -> bool:
        """
        BUSINESS LOGIC: Delete a book
        
        Business Rules:
        1. Book must exist
        2. Only owner or admin can delete
        """
        # Get book
        book = self.book_repo.get_book_by_id(book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found")
        
        # Get requesting user
        user = self.user_repo.get_user_by_id(requesting_user_id)
        if not user:
            raise PermissionError("User not found")
        
        # Business rule: Only owner or admin
        if book.owner_id != requesting_user_id and user.role != "admin":
            raise PermissionError("You can only delete your own books")
        
        # Delegate to repository
        return self.book_repo.delete_book(book_id)

# ============================================================================
# COMPONENT 4: MIDDLEWARE (Request Pipeline)
# ============================================================================

async def request_id_middleware(request: Request, call_next):
    """
    MIDDLEWARE 1: Request ID & Timing
    
    Position: First (early in chain)
    
    Responsibilities:
    - Generate unique request ID
    - Track request timing
    - Store in context for tracing
    """
    # Generate request ID
    request_id = str(uuid.uuid4())
    
    # Get context
    context = RequestContext.from_request(request)
    context.request_id = request_id
    context.start_time = time.time()
    
    # Pass to next middleware
    response = await call_next(request)
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response

async def logging_middleware(request: Request, call_next):
    """
    MIDDLEWARE 2: Logging
    
    Position: Early (after request ID)
    
    Logs every request for debugging
    """
    context = RequestContext.from_request(request)
    
    # Log request
    logger.info(f"[{context.request_id}] {request.method} {request.url.path}")
    
    # Pass to next
    response = await call_next(request)
    
    # Log response
    if context.start_time:
        duration = time.time() - context.start_time
        logger.info(
            f"[{context.request_id}] "
            f"{request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Duration: {duration:.3f}s"
        )
    
    return response

async def auth_middleware(request: Request, call_next):
    """
    MIDDLEWARE 3: Authentication
    
    Position: After logging, before handlers
    
    THE CRITICAL SECURITY COMPONENT:
    1. Extracts JWT token from Authorization header
    2. Verifies token signature
    3. Extracts TRUSTED user_id, username, role
    4. Stores in REQUEST CONTEXT (not request body!)
    5. Handler reads from context (trusted source)
    
    This prevents identity spoofing attacks!
    """
    # Get context
    context = RequestContext.from_request(request)
    
    # Skip auth for public endpoints
    public_paths = ["/", "/docs", "/openapi.json", "/api/register", "/api/login"]
    if request.url.path in public_paths:
        return await call_next(request)
    
    # Extract token
    auth_header = request.headers.get("Authorization")
    
    if auth_header:
        try:
            scheme, token = auth_header.split()
            if scheme.lower() == "bearer":
                # Verify JWT
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                
                # Extract TRUSTED metadata from token
                user_id = payload.get("sub")
                username = payload.get("username")
                role = payload.get("role")
                
                # Store in CONTEXT (trusted source)
                context.user_id = int(user_id) if user_id else None
                context.username = username
                context.role = role
                
                logger.info(f"[{context.request_id}] Authenticated: {username} (ID: {user_id})")
        
        except (ValueError, JWTError) as e:
            # Invalid token - continue without auth
            logger.warning(f"[{context.request_id}] Invalid token: {e}")
    
    # Pass to next (handler can check context.user_id)
    return await call_next(request)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict) -> str:
    """Create JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency: Create user service"""
    user_repo = UserRepository(db)
    return UserService(user_repo)

def get_book_service(db: Session = Depends(get_db)) -> BookService:
    """Dependency: Create book service"""
    book_repo = BookRepository(db)
    user_repo = UserRepository(db)
    return BookService(book_repo, user_repo)

def require_auth(context: RequestContext = Depends(get_context)):
    """Dependency: Require authentication"""
    if not context.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return context

# ============================================================================
# COMPONENT 1: HANDLERS/CONTROLLERS (HTTP Layer)
# ============================================================================

app = FastAPI(
    title="Complete Backend Architecture Example",
    description="All 5 components: Handler, Service, Repository, Middleware, Context",
    version="1.0.0"
)

# ============================================================================
# MIDDLEWARE REGISTRATION (ORDER MATTERS!)
# ============================================================================

# 1. CORS (First - security boundary)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 2. Request ID & Timing (Early)
app.middleware("http")(request_id_middleware)

# 3. Logging (After request ID)
app.middleware("http")(logging_middleware)

# 4. Authentication (Before handlers)
app.middleware("http")(auth_middleware)

# ============================================================================
# HANDLERS - AUTH
# ============================================================================

@app.post("/api/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    service: UserService = Depends(get_user_service)
):
    """
    HANDLER: Register new user
    
    Responsibilities:
    1. Receive & validate input (Pydantic does this)
    2. Call service layer
    3. Handle exceptions → HTTP errors
    4. Decide status code (201)
    5. Return response
    
    Does NOT:
    - Hash passwords (service does)
    - Check duplicates (service does)
    - Access database (repository does)
    """
    try:
        user = service.register_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password
        )
        return user
    
    except ValueError as e:
        # Service raised business rule violation
        # Handler translates to HTTP error
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/login", response_model=Token)
def login(
    credentials: UserLogin,
    service: UserService = Depends(get_user_service)
):
    """
    HANDLER: Login user
    
    Returns JWT token on success
    """
    user = service.authenticate(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "role": user.role
        }
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# ============================================================================
# HANDLERS - USERS
# ============================================================================

@app.get("/api/users/me", response_model=UserResponse)
def get_current_user(
    context: RequestContext = Depends(require_auth),
    service: UserService = Depends(get_user_service)
):
    """
    HANDLER: Get current user profile
    
    SECURITY PATTERN:
    - Reads user_id from CONTEXT (trusted from auth middleware)
    - Does NOT trust user_id from request body/query
    """
    user = service.get_user_profile(context.user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@app.post("/api/users/{user_id}/promote")
def promote_user(
    user_id: int,
    context: RequestContext = Depends(require_auth),
    service: UserService = Depends(get_user_service)
):
    """
    HANDLER: Promote user to admin
    
    Service layer handles permission checks
    """
    try:
        user = service.promote_to_admin(user_id, context.user_id)
        return {"message": "User promoted to admin", "user": UserResponse.from_orm(user)}
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/users", response_model=List[UserResponse])
def list_users(
    context: RequestContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    HANDLER: List all users (admin only)
    """
    if context.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    user_repo = UserRepository(db)
    users = user_repo.get_all_users()
    return users

# ============================================================================
# HANDLERS - BOOKS
# ============================================================================

@app.post("/api/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(
    book_data: BookCreate,
    context: RequestContext = Depends(require_auth),
    service: BookService = Depends(get_book_service)
):
    """
    HANDLER: Create a book
    
    CRITICAL SECURITY PATTERN:
    - Uses owner_id from CONTEXT (trusted from JWT)
    - Does NOT use owner_id from request body (untrusted)
    
    Attack Prevention:
    Client tries: {"title": "Book", "owner_id": 999}  ← IGNORED!
    Handler uses: context.user_id  ← TRUSTED from verified token
    
    This prevents identity spoofing!
    """
    try:
        book = service.create_book(
            title=book_data.title,
            author=book_data.author,
            owner_id=context.user_id  # TRUSTED (from auth middleware)
        )
        return book
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/books/my-books", response_model=List[BookResponse])
def get_my_books(
    context: RequestContext = Depends(require_auth),
    service: BookService = Depends(get_book_service)
):
    """
    HANDLER: Get books for current user
    
    Uses context.user_id (trusted)
    """
    books = service.get_user_books(context.user_id)
    return books

@app.get("/api/books", response_model=List[BookResponse])
def get_all_books(
    context: RequestContext = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    HANDLER: Get all books
    """
    book_repo = BookRepository(db)
    books = book_repo.get_all_books()
    return books

@app.delete("/api/books/{book_id}")
def delete_book(
    book_id: int,
    context: RequestContext = Depends(require_auth),
    service: BookService = Depends(get_book_service)
):
    """
    HANDLER: Delete a book
    
    Service layer handles:
    - Book existence check
    - Permission check (owner or admin)
    """
    try:
        success = service.delete_book(book_id, context.user_id)
        
        if success:
            return {"message": "Book deleted"}
        else:
            raise HTTPException(status_code=404, detail="Book not found")
    
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ============================================================================
# INFO ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """API overview and architecture explanation"""
    return {
        "message": "Complete Backend Architecture API",
        "documentation": "/docs",
        "architecture": {
            "component_1_handler": {
                "purpose": "HTTP protocol management",
                "location": "This file - route functions",
                "responsibilities": [
                    "Validate input (Pydantic)",
                    "Call service layer",
                    "Decide HTTP status codes",
                    "Return responses"
                ],
                "does_not": [
                    "Contain business logic",
                    "Access database directly"
                ]
            },
            "component_2_service": {
                "purpose": "Business logic & orchestration",
                "location": "UserService, BookService classes",
                "responsibilities": [
                    "Implement business rules",
                    "Orchestrate repositories",
                    "Handle side effects (emails, logs)"
                ],
                "does_not": [
                    "Know about HTTP",
                    "Access database directly"
                ],
                "key_feature": "Protocol-agnostic (can be used in CLI, background jobs)"
            },
            "component_3_repository": {
                "purpose": "Database access only",
                "location": "UserRepository, BookRepository classes",
                "responsibilities": [
                    "Construct SQL queries",
                    "Execute queries",
                    "Return raw data"
                ],
                "does_not": [
                    "Contain business logic",
                    "Know about HTTP"
                ],
                "key_rule": "One method = one purpose (granularity)"
            },
            "component_4_middleware": {
                "purpose": "Request pipeline / checkpoints",
                "location": "Middleware functions",
                "types": [
                    "CORS (security boundary)",
                    "Request ID (tracing)",
                    "Logging (debugging)",
                    "Auth (verify JWT, set context)"
                ],
                "execution_order": "CORS → Request ID → Logging → Auth → Handler",
                "key_feature": "Can pass, modify, or terminate requests"
            },
            "component_5_context": {
                "purpose": "Shared state per request",
                "location": "RequestContext class",
                "stores": [
                    "user_id (TRUSTED from JWT)",
                    "username",
                    "role",
                    "request_id (tracing)"
                ],
                "security_pattern": "Prevents identity spoofing (handler uses context, not request body)"
            }
        },
        "request_flow": [
            "1. HTTP Request arrives",
            "2. MIDDLEWARE: CORS check",
            "3. MIDDLEWARE: Generate request ID",
            "4. MIDDLEWARE: Log request",
            "5. MIDDLEWARE: Verify JWT → Store user_id in CONTEXT",
            "6. HANDLER: Validate input (Pydantic)",
            "7. HANDLER: Call SERVICE layer",
            "8. SERVICE: Business logic, call REPOSITORY",
            "9. REPOSITORY: Execute SQL query",
            "10. DATABASE: Return data",
            "11. Back up: Repository → Service → Handler",
            "12. HANDLER: Decide status code, format response",
            "13. HTTP Response"
        ],
        "test_flow": {
            "step_1": "POST /api/register - Create user",
            "step_2": "POST /api/login - Get JWT token",
            "step_3": "GET /api/users/me - Use token (reads from context)",
            "step_4": "POST /api/books - Create book (owner_id from context, NOT body)",
            "step_5": "GET /api/books/my-books - Get your books"
        }
    }

@app.get("/architecture/flow")
def architecture_flow():
    """Detailed request flow explanation"""
    return {
        "title": "Complete Request Life Cycle",
        "example": "POST /api/books",
        "flow": {
            "step_1_request_arrives": {
                "http": "POST /api/books",
                "headers": {"Authorization": "Bearer eyJ..."},
                "body": {"title": "1984", "author": "Orwell"}
            },
            "step_2_middleware_cors": {
                "component": "CORS Middleware",
                "action": "Check origin is allowed",
                "result": "✅ Pass to next"
            },
            "step_3_middleware_request_id": {
                "component": "Request ID Middleware",
                "action": "Generate UUID: abc-123",
                "context": "context.request_id = 'abc-123'",
                "result": "✅ Pass to next"
            },
            "step_4_middleware_logging": {
                "component": "Logging Middleware",
                "action": "Log: [abc-123] POST /api/books",
                "result": "✅ Pass to next"
            },
            "step_5_middleware_auth": {
                "component": "Auth Middleware",
                "action": "Verify JWT token",
                "extract": {
                    "user_id": 42,
                    "username": "alice",
                    "role": "user"
                },
                "context": "context.user_id = 42 (TRUSTED!)",
                "result": "✅ Pass to handler"
            },
            "step_6_handler": {
                "component": "create_book() Handler",
                "validate": "Pydantic validates BookCreate schema",
                "security": "Use context.user_id (42) NOT body.owner_id",
                "call": "service.create_book(title, author, owner_id=42)"
            },
            "step_7_service": {
                "component": "BookService.create_book()",
                "business_logic": "Check if owner exists",
                "orchestrate": "Call user_repo.get_user_by_id(42)",
                "result": "Owner found",
                "call": "book_repo.create_book(title, author, 42)"
            },
            "step_8_repository": {
                "component": "BookRepository.create_book()",
                "sql": "INSERT INTO books (title, author, owner_id) VALUES (?, ?, ?)",
                "execute": "DB.execute('1984', 'Orwell', 42)",
                "result": "Book created with id=1"
            },
            "step_9_back_up": {
                "repository": "Return BookModel(id=1, ...)",
                "service": "Log: Book '1984' created by alice",
                "service_return": "BookModel",
                "handler": "Receive BookModel"
            },
            "step_10_handler_response": {
                "component": "Handler",
                "decide_status": "201 Created",
                "serialize": "BookModel → JSON",
                "return": {"id": 1, "title": "1984", "author": "Orwell", "owner_id": 42}
            },
            "step_11_response": {
                "status": 201,
                "headers": {"X-Request-ID": "abc-123"},
                "body": {"id": 1, "title": "1984", "author": "Orwell", "owner_id": 42}
            }
        },
        "key_security_pattern": {
            "attack_attempt": "Client sends owner_id=999 in body",
            "defense": "Handler ignores body, uses context.user_id=42",
            "result": "Book created with correct owner (42), not spoofed owner (999)"
        }
    }

# ============================================================================
# RUN INSTRUCTIONS
# ============================================================================
"""
SETUP & RUN:
1. pip install "fastapi[standard]" sqlalchemy passlib[bcrypt] python-jose[cryptography]
2. fastapi dev architecture_complete.py
3. Visit: http://127.0.0.1:8000/docs

COMPLETE TEST FLOW:

# 1. Register a user
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"SecurePass123!"}'

# 2. Login and get token
TOKEN=$(curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"SecurePass123!"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# 3. Get current user (uses context.user_id from token)
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN"

# 4. Create a book (owner_id from context, NOT body!)
curl -X POST http://localhost:8000/api/books \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"1984","author":"George Orwell"}'

# 5. Get my books
curl http://localhost:8000/api/books/my-books \
  -H "Authorization: Bearer $TOKEN"

# 6. Try to spoof owner_id (SHOULD FAIL / BE IGNORED)
# This demonstrates the security pattern!
curl -X POST http://localhost:8000/api/books \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Hacker Book","author":"Hacker","owner_id":999}'
# Book will be created with YOUR user_id, not 999!

# 7. Delete a book
curl -X DELETE http://localhost:8000/api/books/1 \
  -H "Authorization: Bearer $TOKEN"

# 8. View architecture explanation
curl http://localhost:8000/
curl http://localhost:8000/architecture/flow

ARCHITECTURE HIGHLIGHTS:

1. MIDDLEWARE ORDER:
   CORS → Request ID → Logging → Auth → Handler
   
2. SECURITY PATTERN:
   - Auth middleware verifies JWT
   - Extracts user_id → stores in context
   - Handler uses context.user_id (TRUSTED)
   - Handler ignores body.owner_id (UNTRUSTED)
   
3. SEPARATION OF CONCERNS:
   - Handler: HTTP in/out, no business logic
   - Service: Business logic, protocol-agnostic
   - Repository: Database only, no business logic
   
4. DEPENDENCY INJECTION:
   - FastAPI automatically creates services
   - Services automatically get repositories
   - Clean, testable code

5. REQUEST CONTEXT:
   - Shared state per request
   - Stores trusted metadata
   - Available to all layers
   - Destroyed after response
"""
