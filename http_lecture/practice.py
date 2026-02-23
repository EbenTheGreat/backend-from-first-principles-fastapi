"""
HTTP Fundamentals Practice - Lecture 1
======================================

This file demonstrates all key HTTP concepts from Lecture 1:
- HTTP Methods (GET, POST, PUT, PATCH, DELETE)
- Status Codes (2xx, 3xx, 4xx, 5xx)
- Headers (Request and Response)
- CORS
- Caching with ETags
- Error Handling

Run with: fastapi dev practice.py
Then visit: http://127.0.0.1:8000/docs for interactive API docs
"""

from fastapi import FastAPI, HTTPException, Header, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
import hashlib

# Initialize FastAPI app
app = FastAPI(
    title="HTTP Fundamentals Practice API",
    description="Demonstrating HTTP concepts for AI Agent backends",
    version="1.0.0"
)

# ==============================================================================
# CORS Configuration (Cross-Origin Resource Sharing)
# ==============================================================================
# This allows frontend applications to call your API from different domains

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins: ["https://myapp.com"]
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# ==============================================================================
# Pydantic Models (Data Validation)
# ==============================================================================

class Message(BaseModel):
    """Represents a single message in a conversation"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg_123",
                "role": "user",
                "content": "What's the weather today?",
                "timestamp": "2026-02-07T12:00:00"
            }
        }


class Conversation(BaseModel):
    """Represents a conversation (chat session)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime =  Field(default_factory=datetime.now)
    messages: List[Message] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "conv_123",
                "title": "Weather Conversation",
                "created_at": "2026-02-07T12:00:00",
                "updated_at": "2026-02-07T12:05:00",
                "messages": []
            }
        }


class CreateMessageRequest(BaseModel):
    """Request body for creating a new message"""
    content: str = Field(..., min_length=1, max_length=5000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Tell me about FastAPI"
            }
        }


class UpdateConversationRequest(BaseModel):
    """Request body for updating conversation metadata"""
    title: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "FastAPI Learning Session"
            }
        }


# ==============================================================================
# In-Memory Storage (Demonstrating HTTP Statelessness)
# ==============================================================================
# In production, this would be a database (PostgreSQL, MongoDB, etc.)

conversations_db = {}
request_count = {}  # For rate limiting demonstration

# ==============================================================================
# Middleware for Request Tracking
# ==============================================================================

@app.middleware("http")
async def add_request_id_header(request: Request, call_next):
    """Add unique request ID to all responses for tracing"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# ==============================================================================
# SECTION 1: Status Code Demonstrations
# ==============================================================================

@app.get("/", tags=["Status Codes"])
async def root():
    """
    Root endpoint - Demonstrates 200 OK
    
    Status Code: 200 OK (Success)
    """
    return {
        "message": "HTTP Fundamentals Practice API",
        "status": "OK",
        "documentation": "/docs"
    }


@app.get("/status/{code}", tags=["Status Codes"])
async def demonstrate_status_code(code: int):
    """
    Demonstrate different HTTP status codes
    
    Try these codes:
    - 200: OK (Success)
    - 201: Created
    - 204: No Content
    - 400: Bad Request
    - 401: Unauthorized
    - 403: Forbidden
    - 404: Not Found
    - 429: Too Many Requests
    - 500: Internal Server Error
    - 503: Service Unavailable
    """
    status_messages = {
        200: {"status": "OK", "message": "Request successful"},
        201: {"status": "Created", "message": "Resource created successfully"},
        204: {"status": "No Content", "message": "Success with no response body"},
        400: {"status": "Bad Request", "message": "Invalid request data"},
        401: {"status": "Unauthorized", "message": "Authentication required"},
        403: {"status": "Forbidden", "message": "You don't have permission"},
        404: {"status": "Not Found", "message": "Resource doesn't exist"},
        429: {"status": "Too Many Requests", "message": "Rate limit exceeded"},
        500: {"status": "Internal Server Error", "message": "Server encountered an error"},
        503: {"status": "Service Unavailable", "message": "Service temporarily down"}
    }
    
    if code not in status_messages:
        raise HTTPException(status_code=400, detail=f"Unsupported status code: {code}")
    
    # For 2xx codes, return success
    if 200 <= code < 300:
        return JSONResponse(
            status_code=code,
            content=status_messages[code]
        )
    
    # For error codes, raise HTTPException
    raise HTTPException(status_code=code, detail=status_messages[code]["message"])


# ==============================================================================
# SECTION 2: HTTP Methods (CRUD Operations)
# ==============================================================================

@app.post("/conversations", status_code=201, tags=["HTTP Methods"])
async def create_conversation(title: Optional[str] = None):
    """
    CREATE operation - Demonstrates POST method
    
    Status Code: 201 Created
    HTTP Method: POST (non-idempotent)
    
    Creates a new conversation and returns it with Location header.
    """
    conversation = Conversation(title=title)
    conversations_db[conversation.id] = conversation
    
    return JSONResponse(
        status_code=201,
        content=conversation.model_dump(mode='json'),
        headers={
            "Location": f"/conversations/{conversation.id}",
            "X-Resource-ID": conversation.id
        }
    )


@app.get("/conversations", tags=["HTTP Methods"])
async def list_conversations():
    """
    READ operation - Demonstrates GET method (list)
    
    Status Code: 200 OK
    HTTP Method: GET (idempotent, safe)
    
    Returns all conversations.
    """
    return {
        "total": len(conversations_db),
        "conversations": [conv.model_dump(mode='json') for conv in conversations_db.values()]
    }


@app.get("/conversations/{conversation_id}", tags=["HTTP Methods"])
async def get_conversation(conversation_id: str):
    """
    READ operation - Demonstrates GET method (single resource)
    
    Status Code: 200 OK or 404 Not Found
    HTTP Method: GET (idempotent, safe)
    
    Returns a specific conversation by ID.
    """
    if conversation_id not in conversations_db:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found"
        )
    
    return conversations_db[conversation_id]


@app.put("/conversations/{conversation_id}", tags=["HTTP Methods"])
async def replace_conversation(conversation_id: str, conversation: Conversation):
    """
    REPLACE operation - Demonstrates PUT method
    
    Status Code: 200 OK or 404 Not Found
    HTTP Method: PUT (idempotent)
    
    Completely replaces the conversation. If it doesn't exist, returns 404.
    PUT is idempotent: calling it multiple times with the same data produces the same result.
    """
    if conversation_id not in conversations_db:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found"
        )
    
    # Complete replacement
    conversation.id = conversation_id  # Ensure ID matches
    conversations_db[conversation_id] = conversation
    
    return conversation


@app.patch("/conversations/{conversation_id}", tags=["HTTP Methods"])
async def update_conversation(conversation_id: str, update: UpdateConversationRequest):
    """
    UPDATE operation - Demonstrates PATCH method
    
    Status Code: 200 OK or 404 Not Found
    HTTP Method: PATCH (idempotent for partial updates)
    
    Partially updates the conversation (only specified fields).
    """
    if conversation_id not in conversations_db:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found"
        )
    
    conversation = conversations_db[conversation_id]
    
    # Update only provided fields
    if update.title is not None:
        conversation.title = update.title
    
    conversation.updated_at = datetime.now()
    
    return conversation


@app.delete("/conversations/{conversation_id}", status_code=204, tags=["HTTP Methods"])
async def delete_conversation(conversation_id: str):
    """
    DELETE operation - Demonstrates DELETE method
    
    Status Code: 204 No Content or 404 Not Found
    HTTP Method: DELETE (idempotent)
    
    Deletes the conversation. Returns 204 with no body on success.
    """
    if conversation_id not in conversations_db:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found"
        )
    
    del conversations_db[conversation_id]
    
    # 204 No Content - return None (no response body)
    return None


# ==============================================================================
# SECTION 3: Headers (Request and Response)
# ==============================================================================

@app.get("/headers/demo", tags=["Headers"])
async def demonstrate_headers(
    user_agent: Optional[str] = Header(None),
    accept: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    accept_language: Optional[str] = Header(None)
):
    """
    Demonstrate reading request headers
    
    Headers are sent by the client to provide context about the request.
    Common headers:
    - User-Agent: Client information (browser, app)
    - Accept: Response format preferences
    - Authorization: Authentication credentials
    - X-API-Key: Custom API key
    - Accept-Language: Language preferences
    """
    return {
        "message": "Request headers received",
        "headers": {
            "user_agent": user_agent,
            "accept": accept,
            "has_authorization": authorization is not None,
            "has_api_key": x_api_key is not None,
            "accept_language": accept_language
        },
        "note": "Headers provide metadata about the request"
    }


@app.get("/headers/custom", tags=["Headers"])
async def custom_response_headers(response: Response):
    """
    Demonstrate setting custom response headers
    
    Response headers provide metadata about the response.
    """
    # Add custom headers
    response.headers["X-Custom-Header"] = "CustomValue"
    response.headers["X-API-Version"] = "1.0.0"
    response.headers["X-Server-Region"] = "us-east-1"
    
    # Cache control
    response.headers["Cache-Control"] = "public, max-age=3600"
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    
    return {
        "message": "Check the response headers!",
        "tip": "In browser DevTools, check Network tab > Response Headers"
    }


# ==============================================================================
# SECTION 4: Caching with ETags
# ==============================================================================

@app.get("/cached-data", tags=["Caching"])
async def get_cached_data(
    response: Response,
    if_none_match: Optional[str] = Header(None)
):
    """
    Demonstrate HTTP caching with ETags
    
    ETag (Entity Tag) is a hash of the resource that clients can use
    to check if the data has changed.
    
    Flow:
    1. Client requests resource
    2. Server responds with ETag header
    3. Client caches response with ETag
    4. Client sends If-None-Match header with cached ETag
    5. Server checks if data changed:
       - If unchanged: Return 304 Not Modified (no body)
       - If changed: Return 200 OK with new data and new ETag
    """
    # Simulated data (in production, this would be from database)
    data = {
        "message": "This is cached data",
        "timestamp": "2026-02-07T12:00:00",
        "version": 1
    }
    
    # Calculate ETag (hash of the data)
    data_str = str(data)
    etag = hashlib.md5(data_str.encode()).hexdigest()
    
    # Check if client has cached version
    if if_none_match == etag:
        # Data hasn't changed - return 304 Not Modified
        return Response(status_code=304)
    
    # Data changed or first request - return full response with ETag
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=300"  # Cache for 5 minutes
    
    return data


# ==============================================================================
# SECTION 5: Rate Limiting (429 Too Many Requests)
# ==============================================================================

def check_rate_limit(client_id: str, limit: int = 10) -> bool:
    """Check if client has exceeded rate limit"""
    if client_id not in request_count:
        request_count[client_id] = 0
    
    request_count[client_id] += 1
    return request_count[client_id] <= limit


@app.get("/rate-limited", tags=["Rate Limiting"])
async def rate_limited_endpoint(
    response: Response,
    x_api_key: str = Header(..., description="Your API key")
):
    """
    Demonstrate rate limiting
    
    Returns 429 Too Many Requests after 10 requests.
    In production, use Redis with sliding window or token bucket algorithm.
    
    Headers included:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Requests remaining
    - Retry-After: Seconds until rate limit resets
    """
    limit = 10
    
    if not check_rate_limit(x_api_key, limit):
        # Rate limit exceeded
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
            headers={
                "Retry-After": "60",  # Try again in 60 seconds
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0"
            }
        )
    
    # Add rate limit headers to successful response
    remaining = limit - request_count[x_api_key]
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    return {
        "message": "Request successful",
        "requests_remaining": remaining,
        "note": "You can make 10 requests before hitting rate limit"
    }


@app.post("/reset-rate-limit", tags=["Rate Limiting"])
async def reset_rate_limit(x_api_key: str = Header(...)):
    """Reset rate limit for testing purposes"""
    if x_api_key in request_count:
        del request_count[x_api_key]
    
    return {"message": "Rate limit reset", "api_key": x_api_key}


# ==============================================================================
# SECTION 6: Chat API (AI Agent Simulation)
# ==============================================================================

@app.post("/conversations/{conversation_id}/messages", status_code=201, tags=["Chat API"])
async def add_message(conversation_id: str, message_request: CreateMessageRequest):
    """
    Add a message to a conversation and get AI response
    
    This demonstrates a typical AI agent API flow:
    1. User sends message (POST)
    2. System stores user message
    3. AI generates response
    4. System stores AI response
    5. Returns AI response with 201 Created
    """
    if conversation_id not in conversations_db:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found"
        )
    
    conversation = conversations_db[conversation_id]
    
    # Add user message
    user_message = Message(
        role="user",
        content=message_request.content
    )
    conversation.messages.append(user_message)
    
    # Simulate AI response (in production, this would call Claude/GPT)
    ai_response_content = f"Echo: {message_request.content}"
    
    ai_message = Message(
        role="assistant",
        content=ai_response_content
    )
    conversation.messages.append(ai_message)
    
    conversation.updated_at = datetime.now()
    
    return JSONResponse(
        status_code=201,
        content=ai_message.model_dump(mode='json'),
        headers={
            "Location": f"/conversations/{conversation_id}/messages/{ai_message.id}",
            "X-Message-ID": ai_message.id
        }
    )


@app.get("/conversations/{conversation_id}/messages", tags=["Chat API"])
async def get_messages(conversation_id: str):
    """
    Get all messages in a conversation
    
    This is how you retrieve conversation history for AI context.
    """
    if conversation_id not in conversations_db:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation {conversation_id} not found"
        )
    
    conversation = conversations_db[conversation_id]
    
    return {
        "conversation_id": conversation_id,
        "total_messages": len(conversation.messages),
        "messages": [msg.model_dump(mode='json') for msg in conversation.messages]
    }


# ==============================================================================
# SECTION 7: Error Handling Examples
# ==============================================================================

@app.get("/error/validation", tags=["Error Handling"])
async def validation_error_demo(age: int):
    """
    Demonstrates 422 Validation Error
    
    Try: /error/validation?age=abc (non-integer)
    FastAPI automatically returns 422 with validation details
    """
    if age < 0:
        raise HTTPException(
            status_code=400,
            detail="Age must be positive"
        )
    
    return {"age": age, "valid": True}


@app.get("/error/unauthorized", tags=["Error Handling"])
async def unauthorized_demo(authorization: Optional[str] = Header(None)):
    """
    Demonstrates 401 Unauthorized
    
    Try without Authorization header to get 401 error
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return {"message": "Authorized", "token_received": True}


@app.get("/error/forbidden", tags=["Error Handling"])
async def forbidden_demo(authorization: str = Header(...)):
    """
    Demonstrates 403 Forbidden
    
    401 = No credentials or invalid credentials
    403 = Valid credentials but insufficient permissions
    """
    # Assume token is valid but user doesn't have permission
    if "admin" not in authorization.lower():
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this resource. Admin role required."
        )
    
    return {"message": "Access granted", "role": "admin"}


@app.get("/error/server", tags=["Error Handling"])
async def server_error_demo():
    """
    Demonstrates 500 Internal Server Error
    
    In production, use proper error handling and logging
    """
    # Simulate unexpected error
    raise Exception("Simulated server error - in production, this would be logged and handled")


# ==============================================================================
# SECTION 8: Health Check & Monitoring
# ==============================================================================

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """
    Health check endpoint for monitoring
    
    Status Code: 200 OK if healthy, 503 Service Unavailable if unhealthy
    
    This endpoint is called by:
    - Load balancers
    - Monitoring systems (Prometheus, Datadog)
    - Kubernetes health probes
    """
    # In production, check database connections, external services, etc.
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "database": "connected",  # Check actual DB connection
        "conversations_count": len(conversations_db)
    }
    
    return health_status


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """
    Basic metrics endpoint
    
    In production, use Prometheus client library for proper metrics
    """
    return {
        "total_conversations": len(conversations_db),
        "total_messages": sum(len(conv.messages) for conv in conversations_db.values()),
        "active_rate_limits": len(request_count)
    }


# ==============================================================================
# SECTION 9: Content Negotiation
# ==============================================================================

@app.get("/content-negotiation", tags=["Advanced"])
async def content_negotiation(
    accept: Optional[str] = Header(None),
    accept_language: Optional[str] = Header(None)
):
    """
    Demonstrate content negotiation
    
    Server adapts response based on client preferences:
    - Accept header: Response format (JSON, XML, HTML)
    - Accept-Language: Language preference
    """
    # Check Accept header for format preference
    format_preference = "json"
    if accept and "xml" in accept.lower():
        format_preference = "xml"
    
    # Check Accept-Language for language preference
    language = "en"
    if accept_language:
        if "es" in accept_language.lower():
            language = "es"
        elif "fr" in accept_language.lower():
            language = "fr"
    
    messages = {
        "en": "Hello, World!",
        "es": "¡Hola, Mundo!",
        "fr": "Bonjour, le monde!"
    }
    
    return {
        "message": messages.get(language, messages["en"]),
        "language": language,
        "format": format_preference,
        "note": "Server adapted response based on Accept headers"
    }


# ==============================================================================
# SECTION 10: Summary & Quick Reference
# ==============================================================================

@app.get("/quick-reference", tags=["Reference"])
async def quick_reference():
    """
    Quick reference guide for HTTP concepts
    """
    return {
        "http_methods": {
            "GET": "Fetch data (safe, idempotent)",
            "POST": "Create resource (non-idempotent)",
            "PUT": "Replace resource (idempotent)",
            "PATCH": "Partial update (idempotent)",
            "DELETE": "Remove resource (idempotent)"
        },
        "status_codes": {
            "2xx_success": {
                "200": "OK - Standard success",
                "201": "Created - Resource created",
                "204": "No Content - Success, empty body"
            },
            "3xx_redirect": {
                "301": "Moved Permanently",
                "304": "Not Modified - Use cached version"
            },
            "4xx_client_error": {
                "400": "Bad Request - Invalid data",
                "401": "Unauthorized - Auth required",
                "403": "Forbidden - No permission",
                "404": "Not Found - Resource doesn't exist",
                "422": "Validation Error",
                "429": "Too Many Requests - Rate limited"
            },
            "5xx_server_error": {
                "500": "Internal Server Error",
                "502": "Bad Gateway",
                "503": "Service Unavailable"
            }
        },
        "important_headers": {
            "request": [
                "Authorization - Auth credentials",
                "Content-Type - Request body format",
                "Accept - Preferred response format",
                "User-Agent - Client information",
                "If-None-Match - ETag for caching"
            ],
            "response": [
                "Content-Type - Response format",
                "Cache-Control - Caching rules",
                "ETag - Resource version hash",
                "Location - Created resource URL",
                "X-Request-ID - Request tracking"
            ]
        },
        "key_concepts": {
            "statelessness": "Server has no memory between requests",
            "idempotency": "Same request = same result (GET, PUT, DELETE)",
            "caching": "Reduce bandwidth with ETag + If-None-Match",
            "cors": "Allow cross-origin requests from browser",
            "rate_limiting": "Prevent abuse with 429 status code"
        }
    }


# ==============================================================================
# Application Startup Message
# ==============================================================================

@app.on_event("startup")
async def startup_event():
    """Print helpful information on startup"""
    print("\n" + "="*70)
    print("HTTP Fundamentals Practice API - Running!")
    print("="*70)
    print("\n📚 Interactive Documentation:")
    print("   Swagger UI: http://127.0.0.1:8000/docs")
    print("   ReDoc:      http://127.0.0.1:8000/redoc")
    print("\n🎯 Quick Start Endpoints:")
    print("   GET  /                     - Welcome message")
    print("   GET  /quick-reference      - HTTP cheat sheet")
    print("   POST /conversations        - Create conversation")
    print("   GET  /status/404           - Try different status codes")
    print("   GET  /headers/demo         - See request headers")
    print("   GET  /cached-data          - Test caching with ETags")
    print("\n💡 Tips:")
    print("   - Visit /docs for interactive testing")
    print("   - All endpoints include examples in Swagger UI")
    print("   - Check response headers in browser DevTools")
    print("="*70 + "\n")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
