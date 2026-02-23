"""
Complete HTTP Protocol Example - FastAPI
Demonstrates all HTTP concepts from Lecture 5

Run with: fastapi dev http_complete.py
Visit: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException, Header, Response, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import hashlib
import json
import time

# ============================================================================
# APP INITIALIZATION with CORS
# ============================================================================

app = FastAPI(
    title="HTTP Protocol Complete Example",
    description="Demonstrates HTTP methods, status codes, headers, CORS, caching, and more",
    version="1.0.0"
)

# Configure CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React
        "http://localhost:5173",  # Vite
        "http://localhost:8080",  # Vue
    ],
    allow_credentials=True,  # Allow cookies/auth headers
    allow_methods=["*"],      # Allow all HTTP methods
    allow_headers=["*"],      # Allow all headers
)

# ============================================================================
# DATA MODELS & STORAGE
# ============================================================================

class Book(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    author: str
    year: int = Field(..., ge=1000, le=2100)
    isbn: Optional[str] = None

# In-memory databases
books_db = {
    1: {"id": 1, "title": "1984", "author": "George Orwell", "year": 1949},
    2: {"id": 2, "title": "Brave New World", "author": "Aldous Huxley", "year": 1932},
}

# Mock authentication tokens
valid_tokens = {
    "admin-token-123": {"user_id": 1, "username": "admin", "role": "admin"},
    "user-token-456": {"user_id": 2, "username": "john", "role": "user"},
}

# Rate limiting storage
rate_limit_storage = {}

# ============================================================================
# SECTION 1: HTTP METHODS - Complete CRUD Demonstrating Idempotency
# ============================================================================

@app.get("/")
def root():
    """Welcome endpoint with API overview"""
    return {
        "message": "HTTP Protocol API",
        "documentation": "/docs",
        "sections": {
            "methods": "Demonstrates all HTTP methods",
            "status_codes": "Shows different status code scenarios",
            "headers": "Request and response header handling",
            "cors": "Cross-origin resource sharing",
            "caching": "ETag-based caching",
            "auth": "Stateless authentication"
        }
    }

# GET - Idempotent (Safe, no side effects)
@app.get("/api/books")
def get_books():
    """
    GET /api/books - Fetch all books
    
    Characteristics:
    - IDEMPOTENT: Call 100 times = same result
    - SAFE: No side effects, doesn't modify server state
    - CACHEABLE: Response can be cached
    """
    return {
        "books": list(books_db.values()),
        "note": "This GET request is idempotent and safe"
    }

@app.get("/api/books/{book_id}")
def get_book(book_id: int):
    """
    GET /api/books/{id} - Fetch specific book
    
    Returns 200 OK if found, 404 Not Found if missing
    """
    if book_id not in books_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book {book_id} not found"
        )
    return {"book": books_db[book_id]}

# POST - Non-idempotent (Creates new resources)
@app.post("/api/books", status_code=status.HTTP_201_CREATED)
def create_book(book: Book):
    """
    POST /api/books - Create new book
    
    Characteristics:
    - NON-IDEMPOTENT: Each call creates a NEW resource
    - Returns 201 Created status code
    - Calling 3 times = 3 different books with different IDs
    """
    new_id = max(books_db.keys()) + 1 if books_db else 1
    new_book = {"id": new_id, **book.dict()}
    books_db[new_id] = new_book
    
    return {
        "book": new_book,
        "note": "POST is non-idempotent - each call creates a new resource"
    }

# PUT - Idempotent (Replaces entire resource)
@app.put("/api/books/{book_id}")
def replace_book(book_id: int, book: Book):
    """
    PUT /api/books/{id} - Replace entire book
    
    Characteristics:
    - IDEMPOTENT: Calling multiple times with same data = same result
    - REPLACES the entire resource
    - Creates if doesn't exist (upsert)
    """
    books_db[book_id] = {"id": book_id, **book.dict()}
    
    return {
        "book": books_db[book_id],
        "note": "PUT is idempotent - same call multiple times = same final state"
    }

# PATCH - Idempotent (Partial update)
@app.patch("/api/books/{book_id}")
def update_book(
    book_id: int,
    title: Optional[str] = None,
    author: Optional[str] = None,
    year: Optional[int] = None
):
    """
    PATCH /api/books/{id} - Partially update book
    
    Characteristics:
    - IDEMPOTENT: Same update = same final state
    - Updates ONLY provided fields
    - 404 if book doesn't exist
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Update only provided fields
    if title is not None:
        books_db[book_id]["title"] = title
    if author is not None:
        books_db[book_id]["author"] = author
    if year is not None:
        books_db[book_id]["year"] = year
    
    return {
        "book": books_db[book_id],
        "note": "PATCH is idempotent - updates only specified fields"
    }

# DELETE - Idempotent
@app.delete("/api/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int):
    """
    DELETE /api/books/{id} - Delete book
    
    Characteristics:
    - IDEMPOTENT: After first call, resource is gone. Subsequent calls = same state
    - Returns 204 No Content (success with no body)
    - Even if already deleted, same end result (resource doesn't exist)
    """
    if book_id in books_db:
        del books_db[book_id]
    
    # Return None for 204 No Content
    return None

# ============================================================================
# SECTION 2: STATUS CODES - The Complete Family
# ============================================================================

@app.get("/status-codes/2xx/200")
def status_200():
    """200 OK - Standard success response"""
    return {"status": 200, "message": "OK - Request succeeded"}

@app.post("/status-codes/2xx/201", status_code=status.HTTP_201_CREATED)
def status_201():
    """201 Created - New resource created successfully"""
    return {"status": 201, "message": "Created - Resource created"}

@app.delete("/status-codes/2xx/204", status_code=status.HTTP_204_NO_CONTENT)
def status_204():
    """204 No Content - Success but no response body"""
    return None

@app.get("/status-codes/3xx/301")
def status_301(response: Response):
    """301 Moved Permanently - Resource permanently moved"""
    response.status_code = status.HTTP_301_MOVED_PERMANENTLY
    response.headers["Location"] = "/new-location"
    return {"status": 301, "message": "Moved Permanently", "new_url": "/new-location"}

@app.get("/status-codes/3xx/304")
def status_304(response: Response):
    """304 Not Modified - Cached version is still valid"""
    response.status_code = status.HTTP_304_NOT_MODIFIED
    return None

@app.get("/status-codes/4xx/400")
def status_400():
    """400 Bad Request - Invalid data from client"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Bad Request - Invalid data format"
    )

@app.get("/status-codes/4xx/401")
def status_401():
    """401 Unauthorized - Missing or invalid authentication"""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized - Authentication required",
        headers={"WWW-Authenticate": "Bearer"}
    )

@app.get("/status-codes/4xx/403")
def status_403():
    """403 Forbidden - Valid auth but insufficient permissions"""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden - You don't have permission"
    )

@app.get("/status-codes/4xx/404")
def status_404():
    """404 Not Found - Resource doesn't exist"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Not Found - Resource does not exist"
    )

@app.get("/status-codes/4xx/429")
def status_429():
    """429 Too Many Requests - Rate limit exceeded"""
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too Many Requests - Rate limit exceeded",
        headers={"Retry-After": "60"}
    )

@app.get("/status-codes/5xx/500")
def status_500():
    """500 Internal Server Error - Unexpected server error"""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal Server Error - Something went wrong"
    )

@app.get("/status-codes/5xx/503")
def status_503():
    """503 Service Unavailable - Server temporarily down"""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Service Unavailable - Try again later"
    )

# ============================================================================
# SECTION 3: HTTP HEADERS - Request and Response
# ============================================================================

@app.get("/headers/request")
def read_request_headers(
    user_agent: Optional[str] = Header(None),
    accept_language: Optional[str] = Header(None),
    accept_encoding: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    x_custom_header: Optional[str] = Header(None, alias="X-Custom-Header")
):
    """
    Read various request headers sent by client
    
    Common headers:
    - User-Agent: Browser/client information
    - Accept-Language: Preferred language (en-US, es, fr)
    - Accept-Encoding: Compression support (gzip, br)
    - Authorization: Auth token (Bearer token)
    - X-Request-ID: Request tracking ID
    - X-Custom-Header: Any custom header
    """
    return {
        "headers": {
            "user_agent": user_agent,
            "accept_language": accept_language,
            "accept_encoding": accept_encoding,
            "authorization": authorization,
            "request_id": x_request_id,
            "custom_header": x_custom_header
        },
        "note": "These are the headers your client sent"
    }

@app.get("/headers/response")
def set_response_headers(response: Response):
    """
    Set custom response headers
    
    Headers provide metadata about the response
    Client can read these headers
    """
    # Custom application headers
    response.headers["X-Custom-Header"] = "CustomValue"
    response.headers["X-Process-Time"] = "0.5ms"
    response.headers["X-Server-Version"] = "1.0.0"
    
    # Caching headers
    response.headers["Cache-Control"] = "max-age=3600, public"
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    
    return {
        "message": "Check the response headers in your browser's dev tools!",
        "headers_set": [
            "X-Custom-Header",
            "X-Process-Time",
            "Cache-Control",
            "X-Content-Type-Options",
            "X-Frame-Options"
        ]
    }

@app.get("/headers/content-negotiation")
def content_negotiation(
    accept_language: Optional[str] = Header(None),
    accept: Optional[str] = Header(None)
):
    """
    Content Negotiation based on Accept headers
    
    Server adapts response based on client preferences
    - Accept-Language: Preferred language
    - Accept: Preferred content type
    """
    # Language negotiation
    message = "Hello World"
    if accept_language:
        if "es" in accept_language.lower():
            message = "Hola Mundo"
        elif "fr" in accept_language.lower():
            message = "Bonjour le monde"
        elif "de" in accept_language.lower():
            message = "Hallo Welt"
    
    return {
        "message": message,
        "detected_language": accept_language,
        "content_type": accept,
        "note": "Server negotiated content based on Accept headers"
    }

# ============================================================================
# SECTION 4: STATELESSNESS - Every Request is Self-Contained
# ============================================================================

def verify_token(authorization: Optional[str] = Header(None)):
    """
    Helper to verify authentication token
    Demonstrates statelessness - token checked on EVERY request
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use: Bearer <token>"
        )
    
    user = valid_tokens.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return user

@app.get("/auth/protected")
def protected_endpoint(user: dict = Header(default=None, include_in_schema=False)):
    """
    Protected endpoint demonstrating statelessness
    
    HTTP is stateless - server has NO memory of previous requests
    Client must send credentials (token) with EVERY request
    
    Try:
    curl -H "Authorization: Bearer admin-token-123" http://localhost:8000/auth/protected
    curl -H "Authorization: Bearer user-token-456" http://localhost:8000/auth/protected
    curl http://localhost:8000/auth/protected  (will fail - no token)
    """
    # Manual token verification for demonstration
    from fastapi import Header
    auth = Header(None)
    user = verify_token(auth)
    
    return {
        "message": "Access granted to protected resource",
        "user": user,
        "note": "Token was validated on THIS request. Server has no memory of past auth."
    }

@app.get("/auth/admin-only")
def admin_only_endpoint(authorization: Optional[str] = Header(None)):
    """
    Protected endpoint with role-based access
    
    Demonstrates:
    - 401 if no token (Unauthorized)
    - 403 if valid token but wrong role (Forbidden)
    - 200 if valid token with admin role
    """
    user = verify_token(authorization)
    
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Your role: " + user["role"]
        )
    
    return {
        "message": "Welcome admin!",
        "user": user,
        "note": "403 vs 401: 401 = no auth, 403 = wrong permissions"
    }

# ============================================================================
# SECTION 5: CACHING with ETags
# ============================================================================

@app.get("/cache/data")
def cached_data(request: Request, response: Response):
    """
    ETag-based caching
    
    How it works:
    1. Server calculates hash (ETag) of data
    2. Client caches response with ETag
    3. On next request, client sends: If-None-Match: <ETag>
    4. If data unchanged, server returns 304 Not Modified (no body)
    5. If data changed, server returns 200 OK with new data and ETag
    
    Benefits:
    - Saves bandwidth
    - Faster responses (304 has no body)
    - Reduces server load
    """
    # Current data
    data = {
        "users": ["Alice", "Bob", "Charlie"],
        "timestamp": int(time.time() / 60)  # Changes every minute
    }
    
    # Calculate ETag (MD5 hash of data)
    data_str = json.dumps(data, sort_keys=True)
    etag = hashlib.md5(data_str.encode()).hexdigest()
    
    # Check if client has cached version
    client_etag = request.headers.get("If-None-Match")
    
    if client_etag == etag:
        # Data unchanged - return 304 with no body
        response.status_code = status.HTTP_304_NOT_MODIFIED
        response.headers["ETag"] = etag
        return None
    
    # Data changed or first request - return full response
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "max-age=60"  # Cache for 60 seconds
    
    return {
        "data": data,
        "etag": etag,
        "note": "Next request: send 'If-None-Match: " + etag + "' for caching"
    }

# ============================================================================
# SECTION 6: RATE LIMITING (429 Too Many Requests)
# ============================================================================

def check_rate_limit(client_id: str, max_requests: int = 5, window_seconds: int = 60):
    """
    Simple rate limiting implementation
    """
    now = time.time()
    
    if client_id not in rate_limit_storage:
        rate_limit_storage[client_id] = []
    
    # Remove old requests outside the time window
    rate_limit_storage[client_id] = [
        req_time for req_time in rate_limit_storage[client_id]
        if now - req_time < window_seconds
    ]
    
    # Check if limit exceeded
    if len(rate_limit_storage[client_id]) >= max_requests:
        return False
    
    # Add current request
    rate_limit_storage[client_id].append(now)
    return True

@app.get("/rate-limited/endpoint")
def rate_limited_endpoint(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Rate-limited endpoint
    
    Limits: 5 requests per 60 seconds per client
    Returns 429 Too Many Requests if limit exceeded
    
    Try calling this endpoint 6 times quickly
    """
    # Use token as client ID, or IP as fallback
    if authorization:
        try:
            _, token = authorization.split()
            client_id = token
        except:
            client_id = request.client.host
    else:
        client_id = request.client.host
    
    if not check_rate_limit(client_id, max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 5 requests per minute.",
            headers={"Retry-After": "60"}
        )
    
    remaining = 5 - len(rate_limit_storage[client_id])
    
    return {
        "message": "Request successful",
        "rate_limit": {
            "limit": 5,
            "remaining": remaining,
            "window": "60 seconds",
            "client_id": client_id[:10] + "..."  # Truncate for privacy
        }
    }

# ============================================================================
# SECTION 7: CORS Demonstration
# ============================================================================

@app.get("/cors/test")
def cors_test():
    """
    CORS-enabled endpoint
    
    The CORS middleware at the top allows:
    - Origins: localhost:3000, localhost:5173, localhost:8080
    - Methods: All (GET, POST, PUT, DELETE, etc.)
    - Headers: All
    - Credentials: Yes (cookies/auth)
    
    When accessed from browser at different origin:
    1. Browser sends OPTIONS pre-flight request (automatic)
    2. Middleware responds with CORS headers
    3. Browser sends actual request (if CORS allows it)
    4. You get the data
    
    Try from browser console at http://localhost:3000:
    fetch('http://localhost:8000/cors/test')
      .then(r => r.json())
      .then(console.log)
    """
    return {
        "message": "CORS is configured!",
        "allowed_origins": [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080"
        ],
        "note": "Check Network tab for OPTIONS pre-flight request"
    }

# ============================================================================
# SECTION 8: Protocol Information
# ============================================================================

@app.get("/protocol/info")
def protocol_info(request: Request):
    """
    Information about HTTP protocol
    """
    return {
        "http_version": "HTTP/1.1",  # FastAPI/Uvicorn default
        "supported_versions": ["HTTP/1.1", "HTTP/2"],
        "characteristics": {
            "stateless": "No memory between requests",
            "client_server": "Client initiates, server responds",
            "reliable": "Built on TCP (connection-based)"
        },
        "evolution": {
            "http1.1": {
                "features": ["Persistent connections", "Chunked transfer", "Host header"],
                "year": 1999
            },
            "http2": {
                "features": ["Multiplexing", "Header compression", "Server push"],
                "year": 2015
            },
            "http3": {
                "features": ["QUIC protocol", "UDP-based", "Faster handshake"],
                "year": 2022
            }
        },
        "security": {
            "https": "HTTP over TLS/SSL",
            "port": "443 (HTTPS) vs 80 (HTTP)",
            "encryption": "Protects against eavesdropping"
        }
    }

# ============================================================================
# HEALTH CHECK & STATISTICS
# ============================================================================

@app.get("/health")
def health_check():
    """Standard health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "http-protocol-api"
    }

@app.get("/stats")
def get_stats():
    """API statistics"""
    return {
        "total_books": len(books_db),
        "total_users": len(valid_tokens),
        "endpoints": {
            "methods": 6,
            "status_codes": 11,
            "headers": 3,
            "auth": 2,
            "caching": 1,
            "cors": 1,
            "rate_limiting": 1
        }
    }

# ============================================================================
# RUN INSTRUCTIONS
# ============================================================================
"""
SETUP & RUN:
1. Save as 'http_complete.py'
2. Install: pip install "fastapi[standard]"
3. Run: fastapi dev http_complete.py
4. Visit: http://127.0.0.1:8000/docs

TESTING EXAMPLES:

# Basic GET
curl http://localhost:8000/api/books

# POST (creates new resource each time - non-idempotent)
curl -X POST http://localhost:8000/api/books \
  -H "Content-Type: application/json" \
  -d '{"title":"New Book","author":"Author","year":2024}'

# GET with headers
curl http://localhost:8000/headers/request \
  -H "User-Agent: MyApp/1.0" \
  -H "Accept-Language: es" \
  -H "X-Custom-Header: test"

# Protected endpoint (with auth)
curl http://localhost:8000/auth/protected \
  -H "Authorization: Bearer admin-token-123"

# Protected endpoint (without auth - gets 401)
curl http://localhost:8000/auth/protected

# Admin-only (with user token - gets 403)
curl http://localhost:8000/auth/admin-only \
  -H "Authorization: Bearer user-token-456"

# ETag caching
curl -i http://localhost:8000/cache/data
# Note the ETag header, then:
curl -i http://localhost:8000/cache/data \
  -H "If-None-Match: <etag-from-previous-response>"

# Rate limiting (call 6 times quickly)
for i in {1..6}; do
  curl http://localhost:8000/rate-limited/endpoint
  echo ""
done

# CORS (from browser console at localhost:3000)
fetch('http://localhost:8000/cors/test')
  .then(r => r.json())
  .then(console.log)
"""
