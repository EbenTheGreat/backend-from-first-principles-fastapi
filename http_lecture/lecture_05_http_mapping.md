# Lecture 5: HTTP Protocol - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: HTTP Protocol - The Language of Backend Communication  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Key Concepts from Your Lecture

### 1. **Core HTTP Characteristics**
- **Statelessness**: No memory of past interactions - every request is self-contained
- **Client-Server Model**: Client always initiates, server responds

### 2. **HTTP Methods (The Intent)**
- **GET**: Fetch data (idempotent)
- **POST**: Create new data (non-idempotent)
- **PUT**: Replace entire resource (idempotent)
- **PATCH**: Partial update (idempotent)
- **DELETE**: Remove resource (idempotent)
- **Idempotency**: Same call multiple times = same result

### 3. **HTTP Headers (The Metadata)**
- Request Headers: Client context (`Authorization`, `User-Agent`)
- Representation Headers: Data format (`Content-Type: application/json`)
- Security Headers: Attack prevention (`Strict-Transport-Security`)
- Content Negotiation: `Accept-Language`, `Accept-Encoding`

### 4. **Status Codes (The Result)**
- **2xx Success**: 200 OK, 201 Created, 204 No Content
- **3xx Redirection**: 301 Permanent, 304 Not Modified
- **4xx Client Error**: 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 429 Rate Limit
- **5xx Server Error**: 500 Internal Error, 502 Bad Gateway, 503 Unavailable

### 5. **Advanced Concepts**
- **CORS**: Cross-Origin Resource Sharing (browser security)
- **Caching**: `Cache-Control`, `ETag` for performance
- **Persistent Connections**: HTTP/1.1 Keep-Alive
- **Protocol Evolution**: HTTP/1.1 → HTTP/2 (multiplexing) → HTTP/3 (QUIC/UDP)
- **HTTPS**: HTTP over TLS encryption

---

## 🔗 FastAPI Documentation Mapping

| Your Lecture Concept | FastAPI Tutorial Section | FastAPI Docs URL |
|---------------------|--------------------------|------------------|
| **HTTP Methods** | First Steps | https://fastapi.tiangolo.com/tutorial/first-steps/ |
| **Status Codes** | Response Status Code | https://fastapi.tiangolo.com/tutorial/response-status-code/ |
| **Headers (Request)** | Header Parameters | https://fastapi.tiangolo.com/tutorial/header-params/ |
| **Headers (Response)** | Response Headers | https://fastapi.tiangolo.com/advanced/response-headers/ |
| **CORS** | CORS (Cross-Origin) | https://fastapi.tiangolo.com/tutorial/cors/ |
| **Error Handling** | Handling Errors | https://fastapi.tiangolo.com/tutorial/handling-errors/ |
| **Custom Responses** | Custom Response | https://fastapi.tiangolo.com/advanced/custom-response/ |
| **Status Codes (Advanced)** | Additional Status Codes | https://fastapi.tiangolo.com/advanced/additional-status-codes/ |
| **Request Object** | Using Request Directly | https://fastapi.tiangolo.com/advanced/using-request-directly/ |

---

## 💡 FastAPI's HTTP Implementation

### How FastAPI Handles HTTP

FastAPI is built on **Starlette** (ASGI framework) which handles the low-level HTTP protocol details. As a developer, you work at a higher level of abstraction, but understanding HTTP is crucial for:

1. **Choosing the right HTTP method** for each endpoint
2. **Setting appropriate status codes** for different outcomes
3. **Working with headers** for authentication, content types, etc.
4. **Handling CORS** for browser-based clients
5. **Implementing caching** strategies
6. **Managing errors** with proper status codes

---

## 🏗️ FastAPI Implementation Examples

### 1. HTTP Methods - The Complete Set

```python
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI()

# In-memory database
items_db = {
    1: {"id": 1, "name": "Item 1", "description": "First item"}
}

class Item(BaseModel):
    name: str
    description: str | None = None

# GET - Fetch data (Idempotent)
@app.get("/items/{item_id}")
def get_item(item_id: int):
    """
    GET is idempotent: Calling it 10 times returns the same result
    No side effects - just retrieves data
    """
    return items_db.get(item_id, {"error": "Not found"})

# POST - Create new resource (Non-idempotent)
@app.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(item: Item):
    """
    POST is non-idempotent: Calling it 10 times creates 10 resources
    Each call has side effects - creates new data
    Returns 201 Created status code
    """
    new_id = max(items_db.keys()) + 1 if items_db else 1
    new_item = {"id": new_id, **item.dict()}
    items_db[new_id] = new_item
    return new_item

# PUT - Replace entire resource (Idempotent)
@app.put("/items/{item_id}")
def replace_item(item_id: int, item: Item):
    """
    PUT is idempotent: Calling it 10 times with same data = same result
    Replaces the ENTIRE resource
    """
    items_db[item_id] = {"id": item_id, **item.dict()}
    return items_db[item_id]

# PATCH - Partial update (Idempotent)
@app.patch("/items/{item_id}")
def update_item(item_id: int, item: Item):
    """
    PATCH is idempotent: Updates only specified fields
    The resource ends up in the same state regardless of how many times you call it
    """
    if item_id in items_db:
        # Update only provided fields
        if item.name:
            items_db[item_id]["name"] = item.name
        if item.description:
            items_db[item_id]["description"] = item.description
    return items_db.get(item_id)

# DELETE - Remove resource (Idempotent)
@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    """
    DELETE is idempotent: After first call, resource is gone
    Calling it again results in the same state (resource doesn't exist)
    Returns 204 No Content (success but no body)
    """
    if item_id in items_db:
        del items_db[item_id]
    return None  # 204 returns no content

# OPTIONS - Pre-flight for CORS (handled automatically by FastAPI)
# HEAD - Like GET but only returns headers (handled automatically)
```

### 2. Status Codes - The Right Code for Every Situation

```python
from fastapi import FastAPI, HTTPException, status, Response

app = FastAPI()

# 2xx - Success Family
@app.get("/success/200")
def success_200():
    """200 OK - Standard success response"""
    return {"message": "Success"}

@app.post("/success/201", status_code=status.HTTP_201_CREATED)
def success_201():
    """201 Created - Resource successfully created"""
    return {"message": "Resource created"}

@app.delete("/success/204", status_code=status.HTTP_204_NO_CONTENT)
def success_204():
    """204 No Content - Success but no response body"""
    return None

# 3xx - Redirection Family
@app.get("/redirect/301", status_code=status.HTTP_301_MOVED_PERMANENTLY)
def redirect_301():
    """301 Moved Permanently - Resource moved to new URL"""
    return {"new_location": "/api/v2/resource"}

@app.get("/redirect/304")
def not_modified_304(response: Response):
    """304 Not Modified - Use cached version"""
    response.status_code = status.HTTP_304_NOT_MODIFIED
    return None

# 4xx - Client Error Family
@app.get("/error/400")
def bad_request_400():
    """400 Bad Request - Invalid data from client"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid request format"
    )

@app.get("/error/401")
def unauthorized_401():
    """401 Unauthorized - Missing or invalid authentication"""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"}
    )

@app.get("/error/403")
def forbidden_403():
    """403 Forbidden - Valid auth but insufficient permissions"""
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to access this resource"
    )

@app.get("/error/404")
def not_found_404():
    """404 Not Found - Resource doesn't exist"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Resource not found"
    )

@app.get("/error/429")
def rate_limit_429():
    """429 Too Many Requests - Rate limiting"""
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Try again in 60 seconds",
        headers={"Retry-After": "60"}
    )

# 5xx - Server Error Family
@app.get("/error/500")
def internal_error_500():
    """500 Internal Server Error - Unexpected server problem"""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred"
    )

@app.get("/error/503")
def unavailable_503():
    """503 Service Unavailable - Server temporarily down"""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Service temporarily unavailable"
    )
```

### 3. HTTP Headers - Request and Response

```python
from fastapi import FastAPI, Header, Response
from typing import Optional

app = FastAPI()

# Reading Request Headers
@app.get("/headers/request")
def read_headers(
    user_agent: Optional[str] = Header(None),
    accept_language: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    custom_header: Optional[str] = Header(None, alias="X-Custom-Header")
):
    """
    Reading headers from client request
    - user-agent: Browser/client info
    - accept-language: Preferred language
    - authorization: Auth token (usually Bearer token)
    - X-Custom-Header: Custom header (alias needed for hyphens)
    """
    return {
        "user_agent": user_agent,
        "language": accept_language,
        "auth": authorization,
        "custom": custom_header
    }

# Setting Response Headers
@app.get("/headers/response")
def set_headers(response: Response):
    """
    Setting custom headers in response
    """
    response.headers["X-Custom-Header"] = "CustomValue"
    response.headers["X-Process-Time"] = "0.5ms"
    response.headers["Cache-Control"] = "max-age=3600"
    return {"message": "Check the response headers!"}

# Content-Type Header (automatic in FastAPI)
@app.get("/headers/content-type")
def content_type():
    """
    FastAPI automatically sets Content-Type: application/json
    for dict/list returns
    """
    return {"message": "JSON response"}

# Security Headers
@app.get("/headers/security")
def security_headers(response: Response):
    """
    Common security headers for production
    """
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return {"message": "Secure response with security headers"}

# Content Negotiation - Accept-Language
@app.get("/headers/language")
def content_negotiation(accept_language: Optional[str] = Header(None)):
    """
    Server adapts response based on Accept-Language header
    Example: Accept-Language: en-US,es;q=0.9
    """
    if accept_language and "es" in accept_language.lower():
        return {"mensaje": "Hola Mundo"}
    elif accept_language and "fr" in accept_language.lower():
        return {"message": "Bonjour le monde"}
    else:
        return {"message": "Hello World"}
```

### 4. CORS - Cross-Origin Resource Sharing

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "https://myapp.com"       # Production domain
    ],
    allow_credentials=True,  # Allow cookies/auth headers
    allow_methods=["*"],     # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],     # Allow all headers
)

# The OPTIONS pre-flight request is handled automatically by the middleware

@app.get("/api/data")
def get_data():
    """
    This endpoint is now accessible from the allowed origins
    Browser will automatically send OPTIONS pre-flight request
    FastAPI middleware responds with appropriate CORS headers
    """
    return {"data": "This can be accessed cross-origin"}

# For development, you might use:
# allow_origins=["*"]  # Allow all origins (NOT for production!)
```

### 5. Caching with ETags

```python
from fastapi import FastAPI, Request, Response, status
import hashlib
import json

app = FastAPI()

# Mock data
data = {"users": ["Alice", "Bob", "Charlie"]}

@app.get("/cached-data")
def get_cached_data(request: Request, response: Response):
    """
    Implements ETag caching
    1. Calculate hash (ETag) of current data
    2. If client sends If-None-Match with same ETag, return 304
    3. Otherwise return 200 with data and ETag header
    """
    # Calculate ETag (hash of data)
    data_str = json.dumps(data, sort_keys=True)
    etag = hashlib.md5(data_str.encode()).hexdigest()
    
    # Check if client has cached version
    client_etag = request.headers.get("If-None-Match")
    
    if client_etag == etag:
        # Data hasn't changed, return 304
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return None
    
    # Data changed or first request, return full response
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "max-age=3600"  # Cache for 1 hour
    return data
```

### 6. Statelessness - Every Request is Self-Contained

```python
from fastapi import FastAPI, Header, HTTPException, status
from typing import Optional

app = FastAPI()

# Simulated token storage (in real app, this would be JWT validation)
valid_tokens = {"secret-token-123": {"user_id": 1, "username": "alice"}}

@app.get("/stateless/protected")
def protected_endpoint(authorization: Optional[str] = Header(None)):
    """
    Demonstrates statelessness:
    - Server has NO memory of previous requests
    - Client must send auth token with EVERY request
    - Server validates token each time (self-contained request)
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    # Extract token (format: "Bearer <token>")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    # Validate token
    user = valid_tokens.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Each request is independent - no session memory
    return {
        "message": "Protected data",
        "user": user,
        "note": "Token validated on THIS request only"
    }
```

### 7. Idempotency in Practice

```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()

items_db = {}
request_log = {}  # Track requests for demonstration

class Item(BaseModel):
    name: str
    price: float

# Non-idempotent: POST
@app.post("/items/non-idempotent")
def create_item_non_idempotent(item: Item):
    """
    POST is non-idempotent
    Calling 3 times = 3 different resources created
    """
    new_id = len(items_db) + 1
    items_db[new_id] = item.dict()
    return {"id": new_id, **item.dict(), "note": "Each call creates new resource"}

# Idempotent: PUT
@app.put("/items/{item_id}/idempotent")
def update_item_idempotent(item_id: int, item: Item):
    """
    PUT is idempotent
    Calling 3 times with same data = same final state
    """
    items_db[item_id] = item.dict()
    return {"id": item_id, **item.dict(), "note": "Same result every time"}

# Idempotent: GET
@app.get("/items/{item_id}/idempotent")
def get_item_idempotent(item_id: int):
    """
    GET is idempotent
    Calling 100 times = same result, no side effects
    """
    return items_db.get(item_id, {"error": "Not found"})

# Idempotent: DELETE
@app.delete("/items/{item_id}/idempotent")
def delete_item_idempotent(item_id: int):
    """
    DELETE is idempotent
    First call: deletes item
    Subsequent calls: item already gone, same end state
    """
    if item_id in items_db:
        del items_db[item_id]
    # Even if already deleted, returns success (idempotent)
    return {"message": "Item deleted (or already gone)"}
```

### 8. HTTP Protocol Evolution

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/protocol/info")
def protocol_info():
    """
    FastAPI/Uvicorn supports HTTP/1.1 and HTTP/2
    
    HTTP/1.1: Default, text-based, persistent connections
    HTTP/2: Binary, multiplexing, header compression
    HTTP/3: QUIC (UDP-based), faster connection
    
    Uvicorn automatically negotiates the highest supported version
    """
    return {
        "supported_protocols": ["HTTP/1.1", "HTTP/2"],
        "features": {
            "http1.1": ["persistent connections", "chunked transfer"],
            "http2": ["multiplexing", "header compression", "server push"],
            "http3": ["QUIC", "UDP-based", "faster handshake"]
        },
        "note": "Client and server negotiate the protocol during connection"
    }
```

---

## 🎯 Practice Exercises

### Exercise 1: HTTP Methods ✅
**Goal**: Implement a complete CRUD API demonstrating idempotency

```python
# TODO: Create a /books API with:
# - GET /books (list all - idempotent)
# - POST /books (create - non-idempotent)
# - GET /books/{id} (get one - idempotent)
# - PUT /books/{id} (replace - idempotent)
# - PATCH /books/{id} (update - idempotent)
# - DELETE /books/{id} (delete - idempotent)

# Test idempotency:
# - Call GET /books/1 ten times - same result?
# - Call POST /books ten times - 10 different books?
# - Call PUT /books/1 ten times - same final state?
```

### Exercise 2: Status Codes ✅
**Goal**: Return appropriate status codes for different scenarios

```python
# TODO: Create an endpoint that:
# 1. Returns 200 when user exists
# 2. Returns 404 when user not found
# 3. Returns 201 when creating new user
# 4. Returns 400 when invalid data
# 5. Returns 401 when missing auth
# 6. Returns 403 when valid auth but wrong permissions
```

### Exercise 3: Headers ✅
**Goal**: Work with request and response headers

```python
# TODO: Create endpoints that:
# 1. Read Authorization header and validate token
# 2. Read Accept-Language and return localized response
# 3. Set custom response headers (X-Request-ID, X-Process-Time)
# 4. Implement basic caching with Cache-Control header
```

### Exercise 4: CORS ✅
**Goal**: Configure CORS for a frontend application

```python
# TODO: 
# 1. Add CORS middleware for localhost:3000
# 2. Create an endpoint that returns user data
# 3. Test from a browser at different origin
# 4. Observe the OPTIONS pre-flight request
```

### Exercise 5: Advanced - Rate Limiting ✅
**Goal**: Implement simple rate limiting with 429 status

```python
# TODO: Create an endpoint that:
# 1. Tracks requests per client (use IP or token)
# 2. Returns 429 after 10 requests per minute
# 3. Includes Retry-After header
```

---

## 🧪 Testing HTTP Concepts

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_http_methods():
    # Test GET (idempotent)
    response1 = client.get("/items/1")
    response2 = client.get("/items/1")
    assert response1.json() == response2.json()
    
    # Test POST (non-idempotent)
    response1 = client.post("/items", json={"name": "Item"})
    response2 = client.post("/items", json={"name": "Item"})
    assert response1.json()["id"] != response2.json()["id"]

def test_status_codes():
    # Test 200 OK
    response = client.get("/items/1")
    assert response.status_code == 200
    
    # Test 404 Not Found
    response = client.get("/items/999")
    assert response.status_code == 404
    
    # Test 201 Created
    response = client.post("/items", json={"name": "New"})
    assert response.status_code == 201

def test_headers():
    # Send custom header
    response = client.get(
        "/data",
        headers={"Authorization": "Bearer token123"}
    )
    assert response.status_code == 200
    
    # Check response headers
    assert "X-Custom-Header" in response.headers

def test_cors():
    # Test CORS headers in response
    response = client.options("/api/data")
    assert "access-control-allow-origin" in response.headers
```

---

## 🎓 Mastery Checklist

Can you:
- [ ] Explain the difference between idempotent and non-idempotent methods?
- [ ] Choose the appropriate HTTP method for each operation?
- [ ] Return correct status codes for success, client errors, and server errors?
- [ ] Read request headers (Authorization, Accept-Language)?
- [ ] Set response headers (Cache-Control, custom headers)?
- [ ] Configure CORS for browser clients?
- [ ] Explain why HTTP is stateless and its implications?
- [ ] Implement caching with ETags?
- [ ] Handle authentication in stateless manner?
- [ ] Distinguish between 401 (Unauthorized) and 403 (Forbidden)?

---

## 💭 Key Insights

### FastAPI Makes HTTP Easy
- **Automatic validation**: Status codes returned automatically on errors
- **Type safety**: Pydantic ensures correct data types
- **Documentation**: All methods and responses documented in OpenAPI
- **CORS middleware**: Simple one-block configuration

### Production Considerations
- Always use HTTPS (TLS) in production
- Set appropriate security headers
- Implement rate limiting (429 status)
- Use proper status codes consistently
- Cache aggressively with ETags/Cache-Control
- Configure CORS carefully (not `allow_origins=["*"]` in prod!)

---

**Last Updated**: 2026-01-29  
**Status**: 🟡 In Progress  
**Next**: Complete exercises, then move to Request Body/Pydantic Models
