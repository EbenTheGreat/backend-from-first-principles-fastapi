"""
Complete Caching Example - FastAPI + Redis
Demonstrates all caching concepts from Lecture 13:

1. Cache Aside (Lazy Caching)
2. Write Through
3. TTL (Time to Live)
4. LRU / LFU Eviction
5. Database Query Caching
6. Session Storage
7. Rate Limiting
8. External API Caching
9. HTTP Caching (ETags / 304)

Run with: fastapi dev caching_complete.py
Visit:    http://127.0.0.1:8000/docs

Install:
  pip install "fastapi[standard]" redis fakeredis sqlalchemy
  
NOTE: This file uses 'fakeredis' so you don't need a real Redis server.
      In production, replace FakeRedis() with redis.Redis(host="localhost")
"""

from fastapi import FastAPI, Request, Response, HTTPException, status, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional
import json
import time
import hashlib
import fakeredis  # Simulates Redis in-memory (no real Redis server needed)

# ============================================================================
# SETUP
# ============================================================================

# Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./caching_demo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis (fakeredis simulates real Redis for practice)
# In production: redis_client = redis.Redis(host="localhost", port=6379)
redis_client = fakeredis.FakeRedis(decode_responses=True)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class ProductModel(Base):
    """Product database model"""
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    price = Column(Integer)  # In cents
    category = Column(String)

class UserModel(Base):
    """User database model"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String)
    role = Column(String, default="user")

Base.metadata.create_all(bind=engine)

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    price: int
    category: str
    class Config:
        from_attributes = True

class ProductCreate(BaseModel):
    name: str
    description: str
    price: int
    category: str

# ============================================================================
# DATABASE DEPENDENCY
# ============================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# CACHE HELPER FUNCTIONS
# ============================================================================

def cache_get(key: str) -> Optional[dict]:
    """
    Get value from cache.
    Returns None on miss.
    """
    value = redis_client.get(key)
    if value:
        return json.loads(value)
    return None

def cache_set(key: str, value: dict, ttl_seconds: int = 300):
    """
    Store value in cache with TTL (Time to Live).
    
    TTL: Data auto-expires after this many seconds.
    Prevents stale data from living forever.
    
    TTL Examples:
    - Trending topics: 300s (5 min) - changes occasionally
    - Product details: 3600s (1 hr) - rarely changes
    - Session tokens: 1800s (30 min) - security requirement
    - Weather data: 600s (10 min) - changes slowly
    """
    redis_client.setex(key, ttl_seconds, json.dumps(value))

def cache_delete(key: str):
    """Remove a specific key from the cache"""
    redis_client.delete(key)

def cache_delete_pattern(pattern: str):
    """Remove all keys matching a pattern (e.g., 'products:*')"""
    for key in redis_client.scan_iter(pattern):
        redis_client.delete(key)

# ============================================================================
# SECTION 1: CACHE ASIDE (LAZY CACHING)
# ============================================================================

app = FastAPI(
    title="Caching Complete Example",
    description="All caching strategies from Lecture 13 with Redis",
    version="1.0.0"
)

@app.get("/cache-aside/products/{product_id}")
def get_product_cache_aside(product_id: int, db: Session = Depends(get_db)):
    """
    STRATEGY 1: CACHE ASIDE (Lazy Caching)

    The most common caching pattern. "Lazy" because we only cache
    data when it's actually requested.

    Flow:
    1. Check cache → HIT? Return instantly ✅
    2. Check cache → MISS? Fetch from DB
    3. Store result in cache for next time
    4. Return result

    Real-world analogy:
    - You look up a phone number in your address book (cache)
    - If it's there → use it (cache hit)
    - If not → look it up online (DB), write it in your book (set cache)
    """
    cache_key = f"product:{product_id}"

    # Step 1: Check cache first
    cached = cache_get(cache_key)
    if cached:
        # CACHE HIT → instant response, no DB query!
        return {
            "source": "🟢 CACHE HIT (Redis) - No database query!",
            "product": cached,
            "latency": "~0.1ms"
        }

    # Step 2: CACHE MISS → query database
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product_data = ProductResponse.from_orm(product).dict()

    # Step 3: Store in cache (TTL: 1 hour)
    cache_set(cache_key, product_data, ttl_seconds=3600)

    # Step 4: Return result
    return {
        "source": "🔴 CACHE MISS - Queried database, stored in cache",
        "product": product_data,
        "latency": "~50ms",
        "note": "Next request will be a CACHE HIT (0.1ms)"
    }

# ============================================================================
# SECTION 2: WRITE THROUGH
# ============================================================================

@app.post("/write-through/products", status_code=201)
def create_product_write_through(product: ProductCreate, db: Session = Depends(get_db)):
    """
    STRATEGY 2: WRITE THROUGH

    Update database AND cache simultaneously on every write.
    Cache is always "fresh" - never stale.

    Flow:
    1. Write to database
    2. Immediately write SAME data to cache
    3. Return result

    vs Cache Aside:
    - Cache Aside: Cache only updated on READ (lazy)
    - Write Through: Cache updated on WRITE (eager)

    When to use:
    - Data that's read very frequently after being written
    - When you can't tolerate any stale cache reads
    """
    # Step 1: Write to database
    db_product = ProductModel(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    product_data = ProductResponse.from_orm(db_product).dict()

    # Step 2: Write SAME data to cache immediately (Write Through!)
    cache_key = f"product:{db_product.id}"
    cache_set(cache_key, product_data, ttl_seconds=3600)

    # Invalidate the list cache (list is now stale)
    cache_delete_pattern("products:list:*")

    return {
        "strategy": "WRITE THROUGH",
        "product": product_data,
        "cache_updated": True,
        "note": "Database AND cache updated simultaneously"
    }

@app.patch("/write-through/products/{product_id}")
def update_product_write_through(
    product_id: int,
    updates: dict,
    db: Session = Depends(get_db)
):
    """
    WRITE THROUGH on update.

    Any update simultaneously updates both DB and cache.
    No stale reads possible.
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update database
    for key, value in updates.items():
        if hasattr(product, key):
            setattr(product, key, value)
    db.commit()
    db.refresh(product)

    product_data = ProductResponse.from_orm(product).dict()

    # Update cache immediately (Write Through)
    cache_set(f"product:{product_id}", product_data, ttl_seconds=3600)

    return {
        "strategy": "WRITE THROUGH",
        "product": product_data,
        "cache_updated": True
    }

# ============================================================================
# SECTION 3: TTL (TIME TO LIVE) DEMONSTRATION
# ============================================================================

@app.get("/ttl/trending-topics")
def get_trending_topics():
    """
    TTL DEMONSTRATION: Trending Topics

    Real-world: Twitter/X caches trending topics every few minutes.
    Computing trends from billions of tweets is EXPENSIVE.

    TTL Strategy:
    - Compute trends → cache for 5 minutes (300s)
    - All requests in those 5 minutes → cache hit
    - After 5 minutes → TTL expires → recompute

    This is exactly what Twitter does!
    """
    cache_key = "trending:topics"
    cached = cache_get(cache_key)

    if cached:
        ttl_remaining = redis_client.ttl(cache_key)
        return {
            "source": "🟢 CACHE HIT",
            "topics": cached["topics"],
            "ttl_remaining_seconds": ttl_remaining,
            "note": f"Cache expires in {ttl_remaining}s. No expensive computation!"
        }

    # Simulate EXPENSIVE computation (real: analyze billions of tweets)
    time.sleep(0.1)  # Simulating computation time
    trending = {
        "topics": ["#Python", "#FastAPI", "#Redis", "#Caching", "#Backend"],
        "computed_at": time.strftime("%H:%M:%S"),
        "computation_cost": "Very expensive! (simulated)"
    }

    # Cache for 5 minutes (300 seconds)
    cache_set(cache_key, trending, ttl_seconds=300)

    return {
        "source": "🔴 CACHE MISS - Computed trending topics",
        "topics": trending["topics"],
        "cached_for": "300 seconds",
        "note": "Next 300 seconds → instant responses from cache"
    }

@app.get("/ttl/weather")
def get_weather(city: str = Query("London")):
    """
    TTL: External API Caching

    Real-world: Weather API has rate limits and costs money.
    Weather doesn't change every second → safe to cache!

    TTL = 10 minutes (600s)
    """
    cache_key = f"weather:{city.lower()}"
    cached = cache_get(cache_key)

    if cached:
        ttl_remaining = redis_client.ttl(cache_key)
        return {
            "source": "🟢 CACHE HIT - No external API call!",
            "city": city,
            "weather": cached,
            "ttl_remaining": ttl_remaining,
            "savings": "Saved 1 API call (rate limit + cost)"
        }

    # Simulate external API call (expensive, rate-limited, costs money)
    weather_data = {
        "city": city,
        "temperature": 18,
        "condition": "Partly cloudy",
        "humidity": 65,
        "fetched_at": time.strftime("%H:%M:%S")
    }

    # Cache for 10 minutes
    cache_set(cache_key, weather_data, ttl_seconds=600)

    return {
        "source": "🔴 CACHE MISS - Called external weather API",
        "city": city,
        "weather": weather_data,
        "cached_for": "600 seconds (10 minutes)"
    }

# ============================================================================
# SECTION 4: SESSION STORAGE
# ============================================================================

@app.post("/sessions/login")
def login_with_session(username: str, password: str):
    """
    SESSION STORAGE IN REDIS

    Why Redis instead of database for sessions?

    Database session lookup:
    - SQL query to sessions table
    - ~50ms per request
    - Heavy database load

    Redis session lookup:
    - In-memory key-value lookup
    - ~0.1ms per request
    - 500x faster!

    Pattern:
    1. Verify credentials (DB query - only once at login)
    2. Create session token
    3. Store in Redis with TTL
    4. Return token to client
    5. All subsequent requests: check Redis (fast!)
    """
    # Simulate credential verification (real: check hashed password)
    if username == "alice" and password == "password123":
        user_id = 1
        role = "user"
    elif username == "admin" and password == "admin123":
        user_id = 99
        role = "admin"
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create session token
    session_token = hashlib.sha256(
        f"{username}{time.time()}".encode()
    ).hexdigest()

    # Store session in Redis (30 minute TTL)
    session_data = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "created_at": time.strftime("%H:%M:%S")
    }
    redis_client.setex(f"session:{session_token}", 1800, json.dumps(session_data))

    return {
        "session_token": session_token,
        "expires_in": "30 minutes",
        "storage": "Redis (in-memory) - NOT database",
        "benefit": "All auth checks now ~0.1ms instead of ~50ms"
    }

@app.get("/sessions/me")
def get_session_user(session_token: str = Query(...)):
    """
    SESSION VERIFICATION FROM REDIS

    Every authenticated request:
    1. Client sends session_token
    2. Server looks up token in Redis (~0.1ms)
    3. Gets trusted user data
    4. No database query needed!

    If sessions were in DB:
    - Every request = SQL query
    - At 1000 req/s = 1000 queries/s on DB
    
    With Redis:
    - Every request = Redis lookup
    - At 1000 req/s = 1000 Redis lookups (100x cheaper)
    """
    session_data = redis_client.get(f"session:{session_token}")

    if not session_data:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid"
        )

    user = json.loads(session_data)
    ttl = redis_client.ttl(f"session:{session_token}")

    return {
        "user": user,
        "session_expires_in": f"{ttl} seconds",
        "source": "Redis (in-memory) - No DB query!",
        "latency": "~0.1ms"
    }

@app.post("/sessions/logout")
def logout_session(session_token: str = Query(...)):
    """
    INSTANT SESSION REVOCATION

    Key advantage of Redis sessions vs JWT:
    - JWT: Cannot revoke before expiry
    - Redis session: DELETE key = instant logout!
    """
    deleted = redis_client.delete(f"session:{session_token}")

    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "message": "Logged out successfully",
        "session_revoked": True,
        "note": "Session token is now invalid immediately"
    }

# ============================================================================
# SECTION 5: RATE LIMITING
# ============================================================================

@app.get("/rate-limited/search")
def rate_limited_search(request: Request, query: str = Query(...)):
    """
    RATE LIMITING WITH REDIS

    Why Redis for rate limiting?
    - Need to count requests per IP per time window
    - Counter must be FAST (checked on every request)
    - Must be shared across multiple server instances
    - Redis atomic INCR + EXPIRE = perfect fit

    Pattern:
    1. Get client IP
    2. Build key: "rate:{ip}:{current_minute}"
    3. INCR counter (atomic operation)
    4. If first request in this minute → set TTL to 60s
    5. If count > limit → return 429 Too Many Requests
    """
    client_ip = request.client.host
    current_minute = int(time.time() / 60)  # Changes every minute
    rate_key = f"rate:{client_ip}:{current_minute}"

    # Atomic increment (thread-safe)
    request_count = redis_client.incr(rate_key)

    # Set TTL on first request of this minute
    if request_count == 1:
        redis_client.expire(rate_key, 60)  # Expires at end of minute

    # Rate limit: 10 requests per minute
    RATE_LIMIT = 10

    if request_count > RATE_LIMIT:
        ttl = redis_client.ttl(rate_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
            headers={"Retry-After": str(ttl)}
        )

    # Search logic (simplified)
    results = [{"result": f"Result for '{query}' #{i}"} for i in range(3)]

    return {
        "query": query,
        "results": results,
        "rate_limit_status": {
            "requests_this_minute": request_count,
            "limit": RATE_LIMIT,
            "remaining": RATE_LIMIT - request_count,
            "resets_in": f"{redis_client.ttl(rate_key)} seconds"
        }
    }

# ============================================================================
# SECTION 6: DATABASE QUERY CACHING
# ============================================================================

@app.get("/db-cache/products")
def get_products_with_cache(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    DATABASE QUERY CACHING

    Expensive queries (JOINs, aggregations, large datasets)
    are perfect candidates for caching.

    Pattern: Cache the ENTIRE query result
    Key: Includes all query parameters for uniqueness
    
    Example (Amazon):
    - MacBook Pro page: queried millions of times during sales
    - Product details rarely change
    - Cache = massive DB load reduction
    """
    # Build cache key from ALL query parameters
    cache_key = f"products:list:{category or 'all'}:page{page}:limit{limit}"
    cached = cache_get(cache_key)

    if cached:
        return {
            "source": "🟢 CACHE HIT - No database query!",
            **cached
        }

    # Simulate EXPENSIVE query (real: multiple JOINs, aggregations)
    query = db.query(ProductModel)
    if category:
        query = query.filter(ProductModel.category == category)

    total = query.count()
    products = query.offset((page - 1) * limit).limit(limit).all()

    result = {
        "data": [ProductResponse.from_orm(p).dict() for p in products],
        "total": total,
        "page": page,
        "cached_at": time.strftime("%H:%M:%S")
    }

    # Cache for 5 minutes (product lists change less often)
    cache_set(cache_key, result, ttl_seconds=300)

    return {
        "source": "🔴 CACHE MISS - Queried database",
        **result
    }

# ============================================================================
# SECTION 7: HTTP CACHING (ETags)
# ============================================================================

@app.get("/http-cache/products/{product_id}")
def get_product_with_etag(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    HTTP CACHING WITH ETags

    ETags = hash of the resource content.
    
    How it works:
    1. First request:
       - Server returns product + ETag header (hash of content)
       - Browser stores both
    
    2. Second request:
       - Browser sends: If-None-Match: <etag>
       - Server checks: has content changed?
       - NO change → 304 Not Modified (no body!)
       - YES change → 200 OK + new content + new ETag
    
    Benefits:
    - 304 response has no body = saves bandwidth
    - Browser uses cached version
    - Server still processes request (lightweight)
    
    Real-world: CDNs use this heavily
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product_data = ProductResponse.from_orm(product).dict()

    # Generate ETag = MD5 hash of content
    content_str = json.dumps(product_data, sort_keys=True)
    etag = f'"{hashlib.md5(content_str.encode()).hexdigest()}"'

    # Check if client has current version
    client_etag = request.headers.get("If-None-Match")

    if client_etag == etag:
        # Content hasn't changed → 304 Not Modified
        # No body sent → saves bandwidth!
        return Response(
            status_code=304,
            headers={"ETag": etag}
        )

    # Content changed (or first request) → return full response
    return Response(
        content=json.dumps({
            "product": product_data,
            "caching_info": {
                "etag": etag,
                "instruction": "Send 'If-None-Match: " + etag + "' on next request",
                "benefit": "If unchanged, server returns 304 (no body = saves bandwidth)"
            }
        }),
        media_type="application/json",
        headers={
            "ETag": etag,
            "Cache-Control": "max-age=3600"
        }
    )

# ============================================================================
# SECTION 8: CACHE INVALIDATION
# ============================================================================

@app.delete("/invalidation/products/{product_id}")
def delete_product_with_cache_invalidation(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    CACHE INVALIDATION

    The hardest problem in caching! (Famous Phil Karlton quote:
    "There are only two hard things in Computer Science:
    cache invalidation and naming things.")

    When data changes, MUST invalidate related cache keys.
    Otherwise users see stale (outdated) data.

    Strategy:
    1. Delete from DB
    2. Delete specific cache key
    3. Delete all related list cache keys
    """
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    category = product.category

    # Delete from database
    db.delete(product)
    db.commit()

    # Invalidate cache keys
    invalidated = []

    # 1. Delete specific product cache
    cache_delete(f"product:{product_id}")
    invalidated.append(f"product:{product_id}")

    # 2. Delete all product list caches (they're now stale)
    count = 0
    for key in redis_client.scan_iter("products:list:*"):
        redis_client.delete(key)
        invalidated.append(key)
        count += 1

    return {
        "message": "Product deleted",
        "cache_invalidated": invalidated,
        "note": "All related cache keys cleared to prevent stale data"
    }

# ============================================================================
# SECTION 9: CACHE STRATEGIES COMPARISON
# ============================================================================

@app.get("/strategies/compare")
def compare_strategies():
    """Compare all caching strategies"""
    return {
        "caching_levels": {
            "1_network_level": {
                "examples": ["CDN", "DNS caching"],
                "what": "Cache content geographically close to users",
                "use_case": "Static files, video content (Netflix)",
                "speed": "Closest to user"
            },
            "2_hardware_level": {
                "examples": ["L1/L2/L3 CPU cache", "RAM"],
                "what": "CPU caches frequently used memory",
                "speed": "L1: ~1ns, RAM: ~100ns, SSD: ~100µs"
            },
            "3_software_level": {
                "examples": ["Redis", "Memcached"],
                "what": "In-memory key-value store",
                "use_case": "DB query caching, sessions, rate limiting",
                "speed": "~0.1ms (vs DB ~50ms)"
            }
        },
        "strategies": {
            "cache_aside_lazy": {
                "alias": "Lazy Caching",
                "flow": "Check cache → miss → query DB → store in cache → return",
                "pros": ["Simple", "Only caches what's needed", "Cache failure doesn't break app"],
                "cons": ["First request always slow", "Possible stale data"],
                "use_case": "Most read-heavy operations"
            },
            "write_through": {
                "flow": "Write DB + Write cache simultaneously",
                "pros": ["Always fresh", "No stale reads"],
                "cons": ["Write penalty", "Caches data that may never be read"],
                "use_case": "Data read immediately after write"
            }
        },
        "eviction_policies": {
            "LRU": {
                "name": "Least Recently Used",
                "removes": "Data not accessed for longest time",
                "analogy": "Delete the oldest item in your browser history"
            },
            "LFU": {
                "name": "Least Frequently Used",
                "removes": "Data accessed least often overall",
                "analogy": "Delete songs you almost never play"
            },
            "TTL": {
                "name": "Time To Live",
                "removes": "Data older than set duration",
                "analogy": "Milk expiry date"
            }
        },
        "use_cases": {
            "session_storage": {
                "why_redis": "~0.1ms vs ~50ms for DB lookup",
                "benefit": "500x faster auth on every request"
            },
            "rate_limiting": {
                "why_redis": "Atomic INCR, shared across servers, auto-expires",
                "benefit": "Consistent limits across multiple server instances"
            },
            "query_caching": {
                "why_cache": "Expensive JOINs/aggregations cost CPU",
                "benefit": "Serve millions of requests from one DB query"
            },
            "api_caching": {
                "why_cache": "Rate limits + cost of external API calls",
                "benefit": "Stay within limits, reduce costs"
            }
        },
        "real_world_examples": {
            "google": "Caches search results (expensive ranking algorithms)",
            "netflix": "CDN edge caches subset of content per region",
            "twitter": "Caches trending topics computed every few minutes",
            "amazon": "Caches product details during high-traffic sales"
        },
        "cache_hit_vs_miss": {
            "hit": "Data found in cache → instant response (~0.1ms)",
            "miss": "Data not in cache → query source → store → return (~50ms)"
        }
    }

# ============================================================================
# ROOT
# ============================================================================

@app.get("/")
def root():
    return {
        "message": "Caching Complete API - Lecture 13",
        "documentation": "/docs",
        "sections": {
            "1_cache_aside": "GET /cache-aside/products/{id}",
            "2_write_through": "POST /write-through/products",
            "3_ttl_trending": "GET /ttl/trending-topics",
            "3_ttl_weather": "GET /ttl/weather?city=London",
            "4_session_storage": {
                "login": "POST /sessions/login",
                "me": "GET /sessions/me?session_token=...",
                "logout": "POST /sessions/logout?session_token=..."
            },
            "5_rate_limiting": "GET /rate-limited/search?query=test",
            "6_db_query_cache": "GET /db-cache/products",
            "7_http_cache_etag": "GET /http-cache/products/{id}",
            "8_invalidation": "DELETE /invalidation/products/{id}",
            "9_compare": "GET /strategies/compare"
        },
        "key_concepts": {
            "what_is_caching": "Subset of primary data in faster location",
            "cache_hit": "Data found in cache → instant response",
            "cache_miss": "Data not found → fetch from source → store → return",
            "why_cache": "Avoid heavy computation OR large data transfer",
            "redis_speed": "~0.1ms vs database ~50ms (500x faster)"
        }
    }

# ============================================================================
# SEED DATA
# ============================================================================

@app.on_event("startup")
def seed():
    db = SessionLocal()
    if db.query(ProductModel).count() == 0:
        products = [
            ProductModel(name="MacBook Pro", description="Apple laptop", price=199900, category="electronics"),
            ProductModel(name="iPhone 15", description="Apple phone", price=99900, category="electronics"),
            ProductModel(name="Python Book", description="Learn Python", price=3999, category="books"),
            ProductModel(name="FastAPI Guide", description="Learn FastAPI", price=2999, category="books"),
        ]
        db.add_all(products)
        db.commit()
    db.close()

# ============================================================================
# TEST COMMANDS
# ============================================================================
"""
SETUP:
  pip install "fastapi[standard]" fakeredis sqlalchemy
  fastapi dev caching_complete.py
  Open: http://localhost:8000/docs

TEST CACHE ASIDE (hit vs miss):
  # First call → MISS (queries database, stores in cache)
  curl http://localhost:8000/cache-aside/products/1

  # Second call → HIT (instant from Redis!)
  curl http://localhost:8000/cache-aside/products/1

TEST SESSION STORAGE:
  # Login → get session token
  curl -X POST "http://localhost:8000/sessions/login?username=alice&password=password123"

  # Use token
  curl "http://localhost:8000/sessions/me?session_token=TOKEN_HERE"

  # Logout → instant revocation
  curl -X POST "http://localhost:8000/sessions/logout?session_token=TOKEN_HERE"

TEST RATE LIMITING:
  # Call 10+ times quickly to trigger 429
  for i in {1..12}; do
    curl "http://localhost:8000/rate-limited/search?query=test"
    echo ""
  done

TEST TTL (trending topics):
  # First call: MISS (computes)
  curl http://localhost:8000/ttl/trending-topics

  # Repeat: HIT (instant, shows TTL countdown)
  curl http://localhost:8000/ttl/trending-topics

TEST HTTP ETAG:
  # First call → get ETag value from response
  curl -v http://localhost:8000/http-cache/products/1

  # Second call with ETag → 304 Not Modified!
  curl -v -H 'If-None-Match: "ETAG_VALUE_HERE"' http://localhost:8000/http-cache/products/1

TEST WRITE THROUGH:
  # Create product → simultaneously caches
  curl -X POST http://localhost:8000/write-through/products \
    -H "Content-Type: application/json" \
    -d '{"name":"New Product","description":"Test","price":999,"category":"test"}'

KEY INSIGHT:
  First request: "🔴 CACHE MISS - Queried database"
  All subsequent requests: "🟢 CACHE HIT - No database query!"
  This is the entire point of caching!
"""
