# Lecture 13: Caching - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Caching - High-Performance Data Access  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Key Concepts from Your Lecture

### **What is Caching?**

> Storing a **subset** of primary data in a location that is **faster and easier to access** to decrease the time and effort required to perform work.

Two scenarios that make caching essential:
1. **Heavy Computation** - Expensive algorithms you don't want to repeat
2. **Large Data Transfer** - Moving big data across long distances repeatedly

---

### **1. The Three Real-World Examples**

**Google Search**
- Problem: Ranking billions of pages is computationally expensive
- Solution: Distributed in-memory caching across globe
- Result: "weather today" → instant result from cache, not re-ranked

**Netflix**
- Problem: Streaming video from US servers to everyone = slow + crash
- Solution: CDN Edge locations cache regional content subsets
- Result: You stream from a server nearby, not the US origin

**Twitter/X**
- Problem: Trending topics = real-time ML analysis of billions of tweets
- Solution: Compute every few minutes, store in Redis
- Result: Users get instant trending data, servers don't crash

---

### **2. Levels of Caching**

```
Level 1: NETWORK
├── CDN (Content Delivery Network)
│   └── Edge nodes serve static assets from nearest server
└── DNS Caching
    └── Browser/OS/ISP cache IP addresses

Level 2: HARDWARE
├── CPU Caches (L1, L2, L3)
│   └── Nanosecond access to frequently used memory
└── RAM (Main Memory)
    ├── Faster than disk (electrical vs mechanical)
    ├── Volatile (lost on power-off)
    └── Limited capacity

Level 3: SOFTWARE
├── Redis (in-memory key-value store)
│   ├── ~0.1ms access time
│   └── Persistence options available
└── Memcached
    └── Simpler, pure in-memory
```

**Speed Reference:**

| Storage | Speed | Notes |
|---------|-------|-------|
| L1 CPU Cache | ~1ns | On-chip, electrical |
| L2/L3 CPU Cache | ~10ns | Near-chip |
| RAM | ~100ns | Volatile |
| **Redis** | **~0.1ms** | **In-memory, networked** |
| SSD | ~100µs | Flash storage |
| **Database** | **~50ms** | **Disk + query processing** |
| External API | ~200ms+ | Network roundtrip |

**Redis is 500x faster than a database query!**

---

### **3. Cache Terminology**

**Cache Hit**
- Data found in cache
- Instant response (~0.1ms)
- No database query needed

**Cache Miss**
- Data NOT in cache
- Must fetch from primary source (~50ms)
- Then store in cache for next time

---

### **4. Caching Strategies**

#### **Cache Aside (Lazy Caching)**
The most common pattern. Only caches what's actually requested.

```
Request arrives
    ↓
Check cache
    ↓
HIT? → Return instantly ✅
    ↓
MISS? → Query database
    ↓
Store result in cache
    ↓
Return result
```

**Pros:** Simple, only caches what's needed, cache failure doesn't break app
**Cons:** First request always slow, possible brief stale data
**Use when:** Most read-heavy operations

#### **Write Through**
Every write updates both database AND cache simultaneously.

```
Write request arrives
    ↓
Write to database
    ↓
Write SAME data to cache
    ↓
Return result
```

**Pros:** Cache always fresh, no stale reads
**Cons:** Write penalty (two writes), caches data that may never be read
**Use when:** Data read immediately after being written

---

### **5. Eviction Policies**

When cache is full, what gets removed?

**LRU (Least Recently Used)**
- Removes data not accessed for the longest time
- Analogy: Delete the oldest items in browser history

**LFU (Least Frequently Used)**
- Removes data accessed least often overall
- Analogy: Delete songs you almost never play

**TTL (Time to Live)**
- Auto-invalidates data after a set duration
- Analogy: Milk expiry date
- Examples:
  - Trending topics: 300s (5 min)
  - Product details: 3600s (1 hr)
  - Sessions: 1800s (30 min)
  - Weather: 600s (10 min)

---

### **6. Common Backend Use Cases**

#### **Database Query Caching**
- Cache results of expensive JOIN queries or aggregations
- Key includes all query parameters
- Amazon: MacBook Pro page cached during sales
- Pattern: Cache Aside

#### **Session Storage**
- Store auth tokens in Redis, not relational DB
- Why: ~0.1ms vs ~50ms per auth check
- At 1000 req/s: 1000 Redis lookups vs 1000 SQL queries
- Extra benefit: Instant revocation (just DELETE the key)

#### **Rate Limiting**
- Track request counts per IP per time window
- Redis atomic INCR is perfect for this
- Shared across multiple server instances
- Returns 429 Too Many Requests when exceeded

#### **External API Caching**
- Cache results from third-party APIs (weather, maps, payments)
- Why: Rate limits + financial cost
- TTL-based: cache until likely stale

#### **HTTP/Browser Caching (ETags)**
- Server sends ETag (hash of resource content)
- Client stores ETag
- Next request: client sends `If-None-Match: <etag>`
- Unchanged? → 304 Not Modified (no body = saves bandwidth)
- Changed? → 200 OK with new content + new ETag

---

## 🔗 FastAPI Documentation Mapping

| Your Lecture Concept | FastAPI/Python Feature | Notes |
|---------------------|----------------------|-------|
| **Cache Aside** | Custom logic + Redis | Manual implementation |
| **Write Through** | Custom logic + Redis | Manual implementation |
| **TTL** | `redis.setex(key, seconds, value)` | Built into Redis |
| **Session Storage** | Redis + custom dependency | See auth lecture |
| **Rate Limiting** | `redis.incr()` + middleware | Custom middleware |
| **ETags** | `Response` headers + `If-None-Match` | FastAPI Response object |
| **Cache Invalidation** | `redis.delete()` / `redis.scan_iter()` | Manual key management |
| **HTTP Cache Headers** | `Cache-Control` header | FastAPI Response headers |

---

## 💡 FastAPI Implementation Patterns

### **Pattern 1: Cache Aside**

```python
def get_product(product_id: int, db: Session = Depends(get_db)):
    cache_key = f"product:{product_id}"
    
    # 1. Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)  # Cache HIT
    
    # 2. Cache MISS → query DB
    product = db.query(ProductModel).filter(...).first()
    
    # 3. Store in cache with TTL
    redis_client.setex(cache_key, 3600, json.dumps(product.dict()))
    
    return product
```

### **Pattern 2: Write Through**

```python
def update_product(product_id: int, updates: dict, db: Session = Depends(get_db)):
    # 1. Write to DB
    product = db.query(...).first()
    for k, v in updates.items():
        setattr(product, k, v)
    db.commit()
    
    # 2. Write SAME data to cache immediately
    redis_client.setex(f"product:{product_id}", 3600, json.dumps(product.dict()))
    
    return product
```

### **Pattern 3: Session Storage**

```python
# Login: store session in Redis
session_token = generate_token()
redis_client.setex(f"session:{session_token}", 1800, json.dumps({
    "user_id": user.id,
    "role": user.role
}))

# Every request: check Redis (fast!)
session_data = redis_client.get(f"session:{session_token}")
# ~0.1ms vs ~50ms for DB query

# Logout: instant revocation
redis_client.delete(f"session:{session_token}")
```

### **Pattern 4: Rate Limiting**

```python
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host
    key = f"rate:{ip}:{int(time.time() / 60)}"  # Per-minute window
    
    count = redis_client.incr(key)          # Atomic increment
    if count == 1:
        redis_client.expire(key, 60)        # Set TTL on first hit
    
    if count > 100:  # Limit: 100 req/min
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    return await call_next(request)
```

### **Pattern 5: ETags**

```python
def get_resource(resource_id: int, request: Request):
    resource = fetch_from_db(resource_id)
    
    # Generate ETag from content
    etag = f'"{md5(json.dumps(resource).encode()).hexdigest()}"'
    
    # Check if client has current version
    if request.headers.get("If-None-Match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    
    # Full response with ETag
    return Response(
        content=json.dumps(resource),
        headers={"ETag": etag, "Cache-Control": "max-age=3600"}
    )
```

---

## 🎯 Choosing the Right Strategy

```
What are you caching?
│
├── SESSIONS / AUTH TOKENS
│   └── Redis with TTL → fast auth on every request
│
├── DATABASE QUERY RESULTS
│   └── Cache Aside → only cache what's actually requested
│
├── DATA THAT CHANGES OFTEN
│   └── Write Through + short TTL → always fresh
│
├── EXPENSIVE COMPUTATIONS (trending, ML results)
│   └── Cache Aside + long TTL → compute once, serve many
│
├── EXTERNAL API RESULTS
│   └── Cache Aside + TTL matching API freshness
│
├── REQUEST COUNTING
│   └── Redis INCR + EXPIRE → rate limiting
│
└── STATIC/RARELY CHANGING CONTENT
    └── CDN edge caching + long TTL
```

---

## ⚠️ Cache Invalidation

> "There are only two hard things in Computer Science: cache invalidation and naming things." — Phil Karlton

**When to invalidate:**
- Data is updated → delete specific key
- Data is deleted → delete specific key + list keys
- Related data changes → delete all affected keys

**Patterns:**

```python
# Delete specific key
redis_client.delete(f"product:{product_id}")

# Delete all keys matching pattern
for key in redis_client.scan_iter("products:list:*"):
    redis_client.delete(key)

# TTL-based invalidation (automatic)
redis_client.setex(key, 300, value)  # Auto-deletes after 300s
```

---

## 💭 Key Insights

### **Why Redis for sessions instead of DB?**

```
Per request:
- Database lookup: ~50ms
- Redis lookup:    ~0.1ms

At 1000 requests/second:
- Database: 1000 SQL queries/s (expensive!)
- Redis:    1000 in-memory lookups/s (cheap!)

Redis is 500x faster per lookup
```

### **Cache Aside vs Write Through**

```
Cache Aside (Lazy):
- Cache populated on READ
- First request: slow (cache miss)
- Good for: most read operations

Write Through (Eager):
- Cache populated on WRITE
- No cold start delay
- Good for: data read immediately after write
```

### **TTL is your safety net**

Even if you forget to invalidate a cache key, TTL ensures it eventually expires. Always set a TTL!

---

## 🎓 Mastery Checklist

- [ ] Explain cache hit vs cache miss?
- [ ] Implement Cache Aside pattern?
- [ ] Implement Write Through pattern?
- [ ] Set TTL on cached data?
- [ ] Use Redis for session storage?
- [ ] Build rate limiting with Redis?
- [ ] Implement ETag HTTP caching?
- [ ] Invalidate cache on data change?
- [ ] Choose LRU vs LFU vs TTL?
- [ ] Explain the 3 real-world examples (Google, Netflix, Twitter)?

---

## 📊 Quick Reference: Redis Commands

```python
# Set with TTL
redis_client.setex("key", 300, "value")  # 300 second TTL

# Get
value = redis_client.get("key")           # None if expired/missing

# Delete
redis_client.delete("key")

# Atomic increment (rate limiting)
count = redis_client.incr("counter")      # Thread-safe

# Set TTL on existing key
redis_client.expire("key", 60)

# Get remaining TTL
ttl = redis_client.ttl("key")             # -2 if gone, -1 if no TTL

# Scan for pattern (cache invalidation)
for key in redis_client.scan_iter("prefix:*"):
    redis_client.delete(key)
```

---

## 📍 Where Caching Fits in the Architecture

```
HTTP Request
    ↓
Middleware (rate limiting → Redis)
    ↓
Handler/Controller
    ↓
Service Layer
    ├── Check cache (Redis) → HIT? Return
    └── MISS? → Repository Layer
                    ↓
                Database
                    ↓
              Store in cache
                    ↓
               Return result
```

---

**Last Updated**: 2026-01-29  
**Status**: ✅ Mapping + Practice File Complete  
**Practice File**: caching_complete.py
