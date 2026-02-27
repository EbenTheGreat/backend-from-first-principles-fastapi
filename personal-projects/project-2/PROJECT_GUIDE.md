# Project 2: Weather Bookmark API — Complete Build Guide

## 🎯 Use Case: "My Favourite Places, Live Weather"

You're building a **personal API to save your favourite locations and instantly check the weather** — things like:
- "What's the weather in London right now?"
- "Is it going to rain in Lagos today?"
- "Show me all my bookmarked cities sorted by temperature"

Each bookmark has a city name, country code, and optional notes. When you fetch the weather, your API calls an **external weather service** behind the scenes — and caches the result to avoid wasting API calls.

---

## 📋 Full Concept Map (Everything You've Learned)

| Concept | Lecture Source | How You'll Use It Here |
|---------|--------------|----------------------|
| HTTP Methods (GET, POST, PATCH, DELETE) | `http_complete.py` — Section 1 | CRUD operations on bookmarks |
| Status Codes (200, 201, 204, 404, 502) | `http_complete.py` — Section 2 | Correct response for each operation, **502 for external API failure** |
| HTTP Headers (custom headers) | `http_complete.py` — Section 3 | `X-Cache-Hit` header on weather responses |
| CORS middleware | `http_complete.py` — CORS setup | Allow frontend access |
| Static routes | `routing_complete.py` — Section 1 | `GET /bookmarks`, `POST /bookmarks` |
| Dynamic routes (path params) | `routing_complete.py` — Section 2 | `GET /bookmarks/{bookmark_id}` |
| Query parameters | `routing_complete.py` — Section 3 | `?country_code=NG&search=Lagos&page=1` |
| Nested routes | `routing_complete.py` — Section 4 | `GET /bookmarks/{bookmark_id}/weather` |
| Path parameter validation | `routing_complete.py` — Section 6 | Validate bookmark_id format |
| Type validation (Pydantic) | `validations_complete.py` — Section 1 | Bookmark model with correct types |
| Syntactic validation (format) | `validations_complete.py` — Section 2 | City name length, country code format |
| Semantic validation (logic) | `validations_complete.py` — Section 3 | Country code must be uppercase 2-letter |
| Cross-field validation | `validations_complete.py` — Section 4 | *(stretch goal: validate city exists in country)* |
| Enums | `rest_api_complete.py` — Enums | Temperature units: `metric`, `imperial` |
| Create/Update/Response pattern | `rest_api_complete.py` — Schemas | Same 3-model pattern for bookmarks |
| Design-first workflow | `rest_api_complete.py` — Root endpoint | Plan before you code |
| Sane defaults | `rest_api_complete.py` — List APIs | Default units=metric, page=1, limit=10 |
| List API with envelope | `rest_api_complete.py` — List API | `{data, total, page, totalPages}` |
| Consistent naming | `rest_api_complete.py` — All schemas | Same field names everywhere |
| Pagination + filtering + sorting | `rest_api_complete.py` — Lines 307-389 | List bookmarks with filters |
| Cache Aside (lazy caching) | `caching_complete.py` — Section 1 | Check cache → miss → call API → store → return |
| TTL (Time to Live) | `caching_complete.py` — Section 3 | Weather data expires after 10 minutes |
| External API caching | `caching_complete.py` — Section 3 (weather) | **Exact same pattern — weather API caching!** |
| Cache invalidation | `caching_complete.py` — Section 8 | Clear cache when bookmark is deleted |
| Rate limiting concept | `caching_complete.py` — Section 5 | Understand why caching saves API calls |
| Handler/Controller layer | `architecture_complete.py` — Component 1 | Routes handle HTTP, delegate to service |
| Service layer | `architecture_complete.py` — Component 2 | Business logic for weather fetching |
| Dependency injection (`Depends`) | `architecture_complete.py` — Helper funcs | Inject services into handlers |
| Password hashing concept | `authentication_complete.py` — Helpers | Understand why API keys are secrets |
| Environment variables | `.env` setup | Store API keys securely |

---

# PHASE 1: DESIGN (Do This on Paper — No Code Yet!)

> ⏱️ Time: 25-35 minutes  
> 🎯 Goal: Know EXACTLY what you're building before touching the keyboard  
> 📖 Ref: `rest_api_complete.py` — Design-first workflow

---

## Step 1: Identify Your Resources

**Think about this:** This API manages TWO things. What are they?

<details>
<summary>💡 Answer (try to think first!)</summary>

Your resources are:
1. **Bookmark** — a saved location (city + country)
2. **Weather** — live weather data for a location (fetched from an external API)

In REST API design (Lecture 11), remember:
- URLs use **plural nouns** → `/bookmarks` (not `/bookmark`)
- Weather isn't a standalone resource you create — it's **linked to a bookmark**
- So the URL becomes: `/bookmarks/{bookmark_id}/weather` — this is a **nested route**

📖 **Lecture Ref:** `routing_complete.py` Section 4 — Nested Routes  
The pattern `/users/{user_id}/posts` from your routing lecture is the SAME pattern here:  
`/bookmarks/{bookmark_id}/weather`

</details>

---

## Step 2: Define What a Bookmark Looks Like

**Think about this:** If you wrote a bookmark on a sticky note, what info would you include?

For each field, think about:
- What **type** is it? (string, integer, date?) — *Lecture 9, Section 1*
- Is it **required** or optional?
- Does it have a **default value**? — *Lecture 11: sane defaults*

<details>
<summary>💡 Answer (try first!)</summary>

A Bookmark has these fields:

| Field | Type | Required? | Default | Notes |
|-------|------|-----------|---------|-------|
| `id` | UUID | Auto-generated | `uuid4()` | Server creates this, not the client |
| `city` | string | ✅ Yes | — | "London", "Lagos", "Tokyo" |
| `country_code` | string | ✅ Yes | — | ISO 3166-1: "GB", "NG", "JP" (always 2 uppercase letters) |
| `notes` | string | ❌ No | `null` | Personal note: "Mom's city" |
| `units` | string (enum) | ❌ No | `"metric"` | metric (°C) or imperial (°F) |
| `created_at` | datetime | Auto-generated | `now()` | When it was bookmarked |
| `updated_at` | datetime | Auto-generated | `now()` | When it was last modified |

**Key decisions from your lectures:**
- `country_code` not `cc` (Lecture 11: no abbreviations!)
- `created_at` / `updated_at` consistent everywhere (Lecture 11: consistency!)
- `units` defaults to `"metric"` (Lecture 11: sane defaults!)
- `notes` is `Optional[str]` (Lecture 9: nullable fields pattern)

📖 **Lecture Refs:**
- `rest_api_complete.py` — AuthorCreate, BookCreate schemas for the naming pattern
- `validations_complete.py` Section 1 — how Pydantic enforces types automatically

</details>

---

## Step 3: Define What Weather Data Looks Like

**Think about this:** When you fetch weather for a bookmark, what info do you want back?

<details>
<summary>💡 Answer (try first!)</summary>

Weather data (from the external API):

| Field | Type | Notes |
|-------|------|-------|
| `city` | string | The city name |
| `country_code` | string | The country |
| `temperature` | float | Current temp |
| `feels_like` | float | "Feels like" temp |
| `description` | string | "clear sky", "light rain", etc. |
| `humidity` | integer | Percentage (0-100) |
| `wind_speed` | float | Wind speed |
| `units` | string | "metric" or "imperial" |
| `fetched_at` | datetime | When this data was retrieved |
| `cached` | boolean | Was this from cache or a fresh API call? |

**Key insight:** This is a **response-only model** — no one "creates" weather. It's built from data the external API sends you, then **transformed** into your own format.

📖 **Lecture Ref:** `caching_complete.py` Section 3 — the `/ttl/weather` endpoint does EXACTLY this pattern (fetch weather data, cache it, return it with TTL info)

</details>

---

## Step 4: Design Your Endpoints (Interface Design)

**Think about this:** What operations can a user perform? For each one, decide:
1. What **HTTP method**?  *(Lecture 5: idempotency rules)*
2. What **URL path**?  *(Lecture 7: routing patterns)*
3. What **status code** on success?  *(Lecture 5: status code families)*
4. What does the **response** look like?

<details>
<summary>💡 Answer (try first!)</summary>

### Bookmark CRUD Endpoints:

| Action | Method | URL | Status Code | Why This Code? |
|--------|--------|-----|------------|----------------|
| Create a bookmark | `POST` | `/bookmarks` | `201 Created` | New resource was created |
| List all bookmarks | `GET` | `/bookmarks` | `200 OK` | Even empty list = 200 |
| Get one bookmark | `GET` | `/bookmarks/{bookmark_id}` | `200 OK` / `404` | 404 only when specific ID not found |
| Update a bookmark | `PATCH` | `/bookmarks/{bookmark_id}` | `200 OK` | Partial update, return updated resource |
| Delete a bookmark | `DELETE` | `/bookmarks/{bookmark_id}` | `204 No Content` | Success, nothing to return |

### Weather Endpoints:

| Action | Method | URL | Status Code | Why? |
|--------|--------|-----|------------|------|
| Get weather for bookmark | `GET` | `/bookmarks/{bookmark_id}/weather` | `200 OK` / `404` / `502` | Nested route! |
| Quick weather lookup | `GET` | `/weather` | `200 OK` / `502` | No bookmark needed |

### Cache Management:

| Action | Method | URL | Status Code | Why? |
|--------|--------|-----|------------|------|
| View cache stats | `GET` | `/cache/stats` | `200 OK` | Monitoring endpoint |
| Clear all cache | `DELETE` | `/cache` | `204 No Content` | Admin action |

### Query Parameters for List endpoint:

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `country_code` | string | `null` (show all) | Filter: `?country_code=NG` |
| `units` | enum | `null` (show all) | Filter: `?units=metric` |
| `search` | string | `null` | Search city name and notes |
| `sort_by` | string | `"created_at"` | Sort field |
| `sort_order` | enum | `"asc"` | Sort direction |
| `page` | integer | `1` | Pagination |
| `limit` | integer | `10` | Items per page (max 50) |

### 🆕 New Status Code: `502 Bad Gateway`

In your HTTP lecture (`http_complete.py` Section 2), you learned about 5xx error codes. Now you'll USE one:

- `500 Internal Server Error` = YOUR code broke
- **`502 Bad Gateway`** = an external service YOUR code depends on broke
- `503 Service Unavailable` = YOUR server is overloaded

Your API acts as a "gateway" to the weather service. If that service fails → you return **502**, telling the client: *"It's not your fault, and it's not my fault — the upstream service is down."*

📖 **Lecture Refs:**
- `http_complete.py` Section 2 — all status codes, especially `status_503()` pattern
- `routing_complete.py` Section 4 — nested routes (`/users/{user_id}/posts`)
- `rest_api_complete.py` — list API with pagination + filtering
- `rest_api_complete.py` — `PATCH` for partial updates, `204` for delete

</details>

---

## Step 5: Design Your Validation Rules

**Think about this:** Apply all 3 validation types from Lecture 9:

<details>
<summary>💡 Answer (try first!)</summary>

| Field | Validation Type | Rule | Error Message |
|-------|----------------|------|---------------|
| `city` | **Type** *(auto)* | Must be string | Automatic (Pydantic) |
| `city` | **Syntactic** | 1-85 characters | "City name must be 1-85 characters" |
| `country_code` | **Type** *(auto)* | Must be string | Automatic (Pydantic) |
| `country_code` | **Syntactic** | Exactly 2 characters | "Country code must be exactly 2 characters" |
| `country_code` | **Semantic** | Must be uppercase letters only | "Country code must be 2 uppercase letters (e.g. GB, NG)" |
| `notes` | **Syntactic** | Max 500 characters | "Notes must be under 500 characters" |
| `units` | **Type** *(enum)* | Must be one of: metric, imperial | "Invalid unit. Choose metric or imperial" |

📖 **Lecture Ref:** `validations_complete.py`
- Section 1 (Type): Pydantic auto-validates types
- Section 2 (Syntactic): `Field(min_length=1, max_length=85)` for city name — same as `UserRegistration` phone format
- Section 3 (Semantic): `@field_validator("country_code")` — same pattern as `PersonProfile.validate_age_realistic()`

</details>

---

## Step 6: Design Your Caching Strategy

📖 **This maps DIRECTLY to `caching_complete.py` Section 3 — the `/ttl/weather` endpoint!**

**Think about this:** Should you call the weather API every single time? In your caching lecture, you learned:
- Weather data doesn't change every second → safe to cache
- External APIs have **rate limits** and sometimes **cost money**
- Redis uses TTL (Time to Live) to auto-expire data

<details>
<summary>💡 Answer (try first!)</summary>

**Strategy: Cache Aside + TTL** (Lecture 13, Sections 1 & 3)

```
weather_cache = {}
# Key: "London:GB:metric"
# Value: {"data": {...weather data...}, "fetched_at": datetime}
```

**Flow** (this is EXACTLY the Cache Aside pattern from your lecture):
1. Client requests weather for London
2. Check cache: is `"London:GB:metric"` in `weather_cache`?
3. **CACHE HIT** → check if data is < 10 min old → return cached data ✅
4. **CACHE MISS** (or expired) → call OpenWeatherMap API → store in cache → return fresh data

**Optional: `?force_refresh=true`** query param to bypass cache

📖 **Lecture Refs:**
- `caching_complete.py` Sections 1-3:
  - `cache_get()` / `cache_set()` helper functions → same helpers you'll build
  - `get_weather()` endpoint → **this is the exact same use case!**
  - TTL of 600 seconds (10 min) for weather data
- `caching_complete.py` Section 8: Cache invalidation — when you DELETE a bookmark, clear its weather cache

**For this project, you'll use a simple Python dict instead of Redis.** The PATTERN is the same — you're just swapping `redis_client.get()` for `weather_cache.get()`. Later, you can upgrade to Redis when you learn databases.

</details>

---

## Step 7: Design Your Response Format

<details>
<summary>💡 Answer</summary>

**List endpoint** — envelope pattern (Lecture 11):

```json
{
  "data": [
    {
      "id": "a1b2c3d4-...",
      "city": "London",
      "country_code": "GB",
      "notes": "Where I want to visit",
      "units": "metric",
      "created_at": "2026-02-26T10:00:00Z",
      "updated_at": "2026-02-26T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "totalPages": 1
}
```

**Weather endpoint** — return data + cache info:

```json
{
  "city": "London",
  "country_code": "GB",
  "temperature": 12.5,
  "feels_like": 10.2,
  "description": "light rain",
  "humidity": 82,
  "wind_speed": 5.1,
  "units": "metric",
  "fetched_at": "2026-02-26T10:05:00Z",
  "cached": true
}
```

The `cached` field tells the client whether data came from cache or a fresh API call — providing **transparency**, just like `caching_complete.py` returns `"source": "🟢 CACHE HIT"` vs `"🔴 CACHE MISS"`.

📖 **Lecture Ref:**  
- `rest_api_complete.py` — `PaginatedResponse` model with `data`, `total`, `page`, `totalPages`
- `caching_complete.py` — weather response includes cache source info

</details>

---

# ✅ DESIGN CHECKPOINT

Before moving to code, you should be able to answer:
- [ ] What are my resources? → **Bookmark** + **Weather**
- [ ] What fields does a bookmark have? → city, country_code, notes, units, timestamps
- [ ] What are my endpoints? → 5 CRUD + 2 weather + 2 cache = 9 endpoints
- [ ] What status codes do I use? → 200, 201, 204, 404, **502** (new!)
- [ ] What validations do I need? → Type (auto), Syntactic (lengths), Semantic (country code)
- [ ] How does caching work? → Cache Aside + TTL, same as `caching_complete.py`
- [ ] What does my response look like? → Envelope for lists, plain object for single/weather

**If you can answer all of these → you're ready to code!**

---

# PHASE 2: SETUP — Get the External API Ready

> ⏱️ Time: 15-20 minutes  
> 🎯 Goal: Set up your API key and understand the external API before coding

---

## Step 8: Get Your Weather API Key

You'll use the **OpenWeatherMap API** (free tier = 60 calls/min, more than enough).

1. Go to [openweathermap.org](https://openweathermap.org/api) and create a free account
2. Go to your API keys page and **copy your API key**
3. Create a `.env` file in your `project-2` folder:

```env
WEATHER_API_KEY=your_api_key_here
CACHE_DURATION_MINUTES=10
```

**How to load `.env` in Python:**
```python
import os
from dotenv import load_dotenv

load_dotenv()  # Reads .env file
API_KEY = os.getenv("WEATHER_API_KEY")
CACHE_MINUTES = int(os.getenv("CACHE_DURATION_MINUTES", "10"))
```

📖 **Why `.env`?** Your authentication lecture (`authentication_complete.py`) hardcoded the `SECRET_KEY` directly in the file — that's fine for practice, but in real projects, secrets go in `.env` files that are NEVER committed to git (add `.env` to `.gitignore`!).

---

## Step 9: Understand the External API You'll Call

Before writing code, understand what the OpenWeatherMap API looks like:

**The URL you'll call:**
```
https://api.openweathermap.org/data/2.5/weather?q={city},{country_code}&units={units}&appid={API_KEY}
```

**What it returns (simplified):**
```json
{
  "main": {
    "temp": 12.5,
    "feels_like": 10.2,
    "humidity": 82
  },
  "weather": [
    { "description": "light rain" }
  ],
  "wind": {
    "speed": 5.1
  },
  "name": "London"
}
```

**Think about this:** The external API returns data in ITS format. You need to **transform** it into YOUR `WeatherResponse` format. This is a very common backend pattern — receive data in one shape, reshape it, return it to your client.

📖 **Lecture Ref:** `caching_complete.py` Section 3 — the simulated `weather_data` dict shows this exact transformation pattern.

---

# PHASE 3: BUILD — Start Coding!

> ⏱️ Time: 90-120 minutes  
> 🎯 Goal: Get all endpoints running and tested

---

## Step 10: Set Up the Project Structure

**Your challenge:** Create the project files:

```
project-2/
├── main.py              # FastAPI app instance
├── routes.py            # All endpoint logic
├── models.py            # Pydantic models
├── db.py                # In-memory storage + cache
├── weather_service.py   # External API calls + caching logic
├── .env                 # API key (add to .gitignore!)
└── requirements.txt     # Dependencies
```

**New file: `weather_service.py`** — In your architecture lecture (`architecture_complete.py`), you learned about the **Service Layer** (Component 2). The weather service follows this pattern:
- `routes.py` = **Handler/Controller** (receives HTTP requests, returns HTTP responses)
- `weather_service.py` = **Service Layer** (business logic — calling external API, caching, transforming data)
- `db.py` = **Data layer** (where your data lives)

This separation keeps your code clean. Your routes don't need to know HOW weather is fetched — they just call the service.

📖 **Lecture Ref:** `architecture_complete.py` — Components 1, 2, 3 (Handler → Service → Repository)

<details>
<summary>🔑 Hints for main.py and db.py (peek ONLY if stuck)</summary>

```python
# main.py — same pattern as your architecture lecture
# Import FastAPI
# Import router from routes
# Create app = FastAPI(title="...", description="...", version="...")
# app.include_router(router)

# db.py
bookmarks_db = {}       # Same pattern as books_db from http_complete.py
weather_cache = {}       # Same pattern! But with TTL expiry
```

📖 Ref: `http_complete.py` lines 52-55 (books_db pattern)

</details>

---

## Step 11: Create Your Pydantic Models

**Your challenge:** Create these models in `models.py`:

1. **`Units`** enum — `metric`, `imperial`
2. **`BookmarkCreate`** — what the client sends when creating
3. **`BookmarkUpdate`** — all fields optional for PATCH
4. **`BookmarkResponse`** — what the server sends back
5. **`BookmarkListResponse`** — envelope for lists
6. **`WeatherResponse`** — weather data returned to client (response-only!)

**Concepts you're applying:**

| What To Do | Lecture Ref |
|-----------|-------------|
| Create enum class | `rest_api_complete.py` — `BookStatus` enum (line 120) |
| `Field(..., min_length=1, max_length=85)` for city | `validations_complete.py` Section 2 — `UserRegistration` |
| `@field_validator("country_code")` | `validations_complete.py` Section 3 — `PersonProfile.validate_age_realistic()` |
| `Optional[str] = None` for nullable fields | `rest_api_complete.py` — `AuthorUpdate` model |
| `List[BookmarkResponse]` in list model | `rest_api_complete.py` — `PaginatedResponse` |
| `model_config` with `json_schema_extra` | `rest_api_complete.py` — example configs |

<details>
<summary>🔑 Structure hint (peek ONLY if stuck)</summary>

```python
# Units enum
class Units(str, Enum):
    metric = "metric"
    imperial = "imperial"

# BookmarkCreate — client sends this
class BookmarkCreate(BaseModel):
    city: str = Field(..., min_length=1, max_length=85)
    country_code: str = Field(..., min_length=2, max_length=2)
    notes: Optional[str] = Field(None, max_length=500)
    units: Optional[Units] = Units.metric  # Sane default!
    
    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v):
        if not v.isalpha() or not v.isupper():
            raise ValueError("Country code must be 2 uppercase letters (e.g. GB, NG)")
        return v

# BookmarkUpdate — ALL fields Optional (PATCH pattern)
# BookmarkResponse — all fields + id, created_at, updated_at
# BookmarkListResponse — envelope: data, total, page, totalPages
# WeatherResponse — temperature, feels_like, description, humidity, etc.
```

📖 Ref: `validations_complete.py` Section 3 lines 325-431 for the `@field_validator` pattern

</details>

---

## Step 12: Build the Bookmark CRUD Endpoints

**Your challenge:** Build all 5 CRUD endpoints in `routes.py`:

1. `POST /bookmarks` → `201 Created`
2. `GET /bookmarks` → `200 OK` with envelope
3. `GET /bookmarks/{bookmark_id}` → `200 OK` or `404`
4. `PATCH /bookmarks/{bookmark_id}` → `200 OK`
5. `DELETE /bookmarks/{bookmark_id}` → `204 No Content`

**Use `APIRouter` with a prefix** — just like your routing lecture:

```python
from fastapi import APIRouter
router = APIRouter(prefix="/v1", tags=["bookmarks"])
```

📖 **Lecture Ref:** `routing_complete.py` Section 5 — Route Versioning (`/v1/...`, `/v2/...`)

**For each endpoint, refer to these lecture sections:**

| Endpoint | Lecture Reference |
|----------|------------------|
| POST (create) | `http_complete.py` `create_book()` — returns 201, auto-generates ID |
| GET (list) | `rest_api_complete.py` lines 307-389 — pagination, filtering, sorting |
| GET (by ID) | `routing_complete.py` `get_book_by_id()` — dynamic path param, 404 |
| PATCH (update) | `rest_api_complete.py` lines 451-484 — `exclude_unset=True` |
| DELETE | `http_complete.py` `delete_book()` — 204 No Content |

**For the list endpoint query params**, use `Query()` with defaults:

```python
from fastapi import Query

@router.get("/bookmarks")
async def list_bookmarks(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    country_code: Optional[str] = Query(None, description="Filter by country"),
    search: Optional[str] = Query(None, description="Search in city and notes"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: Sort = Query(Sort.asc, description="Sort direction")
):
```

📖 **Lecture Ref:** `routing_complete.py` `search_books()` — query params with defaults, filtering, pagination

<details>
<summary>🔑 Logic hint for the list endpoint (peek ONLY if stuck)</summary>

```
GET /bookmarks:
    1. Get all bookmarks as list: list(bookmarks_db.values())
    2. If country_code filter → keep only matching
    3. If search → filter where search in city or notes (case-insensitive)
    4. Sort by sort_by field
    5. Count total (after filtering, BEFORE pagination)
    6. Calculate offset = (page - 1) * limit
    7. Slice: bookmarks[offset : offset + limit]
    8. Calculate total_pages = ceil(total / limit)
    9. Return envelope: {data, total, page, totalPages}
```

📖 Ref: `rest_api_complete.py` list API pattern

</details>

---

## Step 13: Build the Weather Service (The New Skill!)

**Your challenge:** Create `weather_service.py` — this is where you learn something new!

This file acts as your **Service Layer** (`architecture_complete.py` Component 2). It:
1. Checks the cache (Cache Aside pattern — `caching_complete.py` Section 1)
2. On miss: calls the external API using `httpx`
3. Transforms the response into your format
4. Stores in cache with TTL (`caching_complete.py` Section 3)
5. Returns the weather data

### New Tool: `httpx` (Async HTTP Client)

FastAPI is **async** — you write `async def` for all your routes. So your HTTP calls should be async too:

```python
import httpx

async def fetch_weather_from_api(city: str, country_code: str, units: str) -> dict:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": f"{city},{country_code}",
        "units": units,
        "appid": API_KEY
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10.0)
        response.raise_for_status()  # Raises if status >= 400
        return response.json()
```

### Handling External API Errors (New Pattern!)

In your HTTP lecture, you raised `HTTPException` for YOUR errors (404, 400). Now you need to catch errors from ANOTHER service and translate them:

```python
from fastapi import HTTPException, status

try:
    response = await client.get(url, timeout=10.0)
    response.raise_for_status()
except httpx.TimeoutException:
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Weather service timed out — try again later"
    )
except httpx.HTTPStatusError as e:
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Weather service error: {e.response.status_code}"
    )
```

📖 **Lecture Ref:** `http_complete.py` Section 2 — `status_503()` shows a similar "external dependency failed" pattern

### The Caching Logic

Apply **Cache Aside + TTL** directly from your caching lecture:

```python
from datetime import datetime, UTC, timedelta

CACHE_DURATION = timedelta(minutes=10)  # TTL from .env

def get_from_cache(cache_key: str) -> Optional[dict]:
    """Same concept as cache_get() in caching_complete.py"""
    if cache_key in weather_cache:
        entry = weather_cache[cache_key]
        age = datetime.now(UTC) - entry["fetched_at"]
        if age < CACHE_DURATION:
            return entry["data"]  # CACHE HIT!
    return None  # CACHE MISS

def store_in_cache(cache_key: str, data: dict):
    """Same concept as cache_set() in caching_complete.py"""
    weather_cache[cache_key] = {
        "data": data,
        "fetched_at": datetime.now(UTC)
    }
```

📖 **Lecture Refs:**
- `caching_complete.py` lines 107-130 — `cache_get()` and `cache_set()` helpers
- `caching_complete.py` lines 330-370 — `/ttl/weather` endpoint (EXACT same use case!)

<details>
<summary>🔑 Full logic hint for the weather service (peek ONLY if stuck)</summary>

```python
async def get_weather(city: str, country_code: str, units: str = "metric",
                      force_refresh: bool = False) -> dict:
    """
    Service Layer function — follows architecture_complete.py Component 2
    """
    # 1. Build cache key
    cache_key = f"{city.lower()}:{country_code.upper()}:{units}"
    
    # 2. Check cache (Cache Aside — caching_complete.py Section 1)
    if not force_refresh:
        cached_data = get_from_cache(cache_key)
        if cached_data:
            return {**cached_data, "cached": True}
    
    # 3. CACHE MISS — call external API
    raw_data = await fetch_weather_from_api(city, country_code, units)
    
    # 4. Transform external format → your format
    weather_data = {
        "city": raw_data["name"],
        "country_code": country_code.upper(),
        "temperature": raw_data["main"]["temp"],
        "feels_like": raw_data["main"]["feels_like"],
        "description": raw_data["weather"][0]["description"],
        "humidity": raw_data["main"]["humidity"],
        "wind_speed": raw_data["wind"]["speed"],
        "units": units,
        "fetched_at": datetime.now(UTC).isoformat(),
        "cached": False
    }
    
    # 5. Store in cache (TTL — caching_complete.py Section 3)
    store_in_cache(cache_key, weather_data)
    
    # 6. Return
    return weather_data
```

</details>

---

## Step 14: Build the Weather Endpoints

**Your challenge:** Build two weather endpoints in `routes.py`:

### 1. `GET /bookmarks/{bookmark_id}/weather` — Nested Route

This is the nested route pattern from `routing_complete.py` Section 4:

```python
@router.get("/bookmarks/{bookmark_id}/weather")
async def get_bookmark_weather(
    bookmark_id: str,
    force_refresh: bool = Query(False, description="Bypass cache")
):
    # 1. Find bookmark (404 if not found) — same pattern as http_complete.py
    # 2. Call weather_service.get_weather(city, country_code, units)
    # 3. Return weather data
```

📖 **Lecture Ref:** `routing_complete.py` `get_user_posts()` — same nested route pattern

### 2. `GET /weather` — Quick Lookup (No Bookmark)

```python
@router.get("/weather")
async def quick_weather_lookup(
    city: str = Query(..., min_length=1, description="City name"),
    country_code: str = Query(..., min_length=2, max_length=2, description="Country code"),
    units: Units = Query(Units.metric, description="Temperature units"),
    force_refresh: bool = Query(False, description="Bypass cache")
):
    # 1. Call weather_service.get_weather(city, country_code, units, force_refresh)
    # 2. Return weather data
```

📖 **Lecture Ref:** `caching_complete.py` `/ttl/weather` — query param for city, cached response

---

## Step 15: Build Cache Management Endpoints

**Your challenge:** Create monitoring and admin endpoints for the cache:

```python
@router.get("/cache/stats")
async def get_cache_stats():
    """
    Same concept as caching_complete.py Section 9 — cache monitoring
    """
    # Return: total entries, list of cached cities, oldest/newest entry

@router.delete("/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache():
    """
    Cache invalidation — caching_complete.py Section 8
    """
    weather_cache.clear()
    return
```

📖 **Lecture Ref:** `caching_complete.py` Section 8 — Cache invalidation (clearing stale data)

---

# PHASE 4: TEST & POLISH

> ⏱️ Time: 30-45 minutes  
> 🎯 Goal: Make sure everything works correctly

---

## Step 16: Test Every Endpoint

Run your server and test in the Swagger UI (`/docs`):

```
Test Checklist:

BOOKMARK CRUD:
□ POST /bookmarks — Create bookmarks for London/GB, Lagos/NG, Tokyo/JP
□ GET /bookmarks — See all bookmarks (envelope format)
□ GET /bookmarks?country_code=GB — Filter works
□ GET /bookmarks?search=London — Search works
□ GET /bookmarks?page=1&limit=2 — Pagination works
□ GET /bookmarks/{id} — Get specific bookmark
□ GET /bookmarks/fake-uuid — Should return 404
□ PATCH /bookmarks/{id} — Update notes only (others unchanged)
□ DELETE /bookmarks/{id} — Returns 204
□ DELETE /bookmarks/{id} — Again → 404
□ GET /bookmarks — Confirm bookmark is gone

VALIDATION:
□ POST /bookmarks with city="" — Reject (min_length)
□ POST /bookmarks with country_code="abc" — Reject (not 2 chars)
□ POST /bookmarks with country_code="gb" — Reject (not uppercase)
□ POST /bookmarks with units="kelvin" — Reject (not in enum)

WEATHER (The New Part!):
□ GET /bookmarks/{id}/weather — Returns weather! 🎉
□ GET /bookmarks/{id}/weather — Again (should show cached=true)
□ GET /bookmarks/{id}/weather?force_refresh=true — Fresh data
□ GET /weather?city=London&country_code=GB — Quick lookup works
□ GET /weather?city=FakeCity&country_code=XX — Should return 502

CACHE:
□ GET /cache/stats — See cache entries
□ DELETE /cache — Clear cache (204)
□ GET /bookmarks/{id}/weather — Should be uncached now
```

---

## Step 17: Check Your Design Principles

Review against what you learned in ALL lectures:

```
HTTP (Lecture 5):
□ Correct methods? (GET=safe, POST=create, PATCH=partial update, DELETE=remove)
□ Correct status codes? (200, 201, 204, 404, 502)
□ Idempotency correct? (GET/DELETE idempotent, POST non-idempotent)

Routing (Lecture 7):
□ Static routes for collections? (/bookmarks)
□ Dynamic routes for specific resources? (/bookmarks/{id})
□ Nested routes for relationships? (/bookmarks/{id}/weather)
□ Query params for filtering/sorting/pagination?

Validation (Lecture 9):
□ Type validation automatic? (Pydantic catches wrong types)
□ Syntactic validation present? (min_length, max_length, regex)
□ Semantic validation present? (country_code must be uppercase letters)

REST API Design (Lecture 11):
□ URLs use plural nouns? (/bookmarks not /bookmark)
□ Sane defaults? (units=metric, page=1, limit=10)
□ List API has envelope? ({data, total, page, totalPages})
□ Empty list returns 200, not 404?
□ No abbreviations? (country_code not cc)
□ Field names consistent everywhere?

Caching (Lecture 13):
□ Cache Aside pattern implemented? (check cache → miss → fetch → store)
□ TTL configured? (weather data expires after 10 min)
□ Cache invalidation on delete?
□ force_refresh option available?

Architecture (Lecture 10):
□ Handler layer clean? (routes.py only handles HTTP)
□ Service layer separated? (weather_service.py has business logic)
□ Concerns separated? (routes don't know about httpx/cache)
```

---

# PHASE 5: STRETCH GOALS (Only After Phases 1-4 Are Done!)

1. **Weather history** — Store each fetch in a list, add `GET /bookmarks/{id}/weather/history`
2. **Temperature alerts** — Set a threshold, show bookmarks above/below it
3. **Bulk weather fetch** — `POST /bookmarks/weather/bulk` fetches weather for ALL bookmarks
4. **Favorites flag** — Mark bookmarks as favorites, filter `?favorite=true`
5. **Weather comparison** — `GET /weather/compare?ids=id1,id2,id3` side by side
6. **HTTP caching with ETags** — Apply `caching_complete.py` Section 7 (304 Not Modified) to bookmark responses
7. **Rate limiting** — Apply `caching_complete.py` Section 5 to the weather endpoint

---

# 📚 Quick Reference: Which Lecture File to Look At

| When you're stuck on... | Look at this file | Specific section |
|--------------------------|-------------------|-----------------| 
| App/router setup | `http_complete.py` | Lines 1-70 |
| HTTP methods (GET/POST/PATCH/DELETE) | `http_complete.py` | Section 1 |
| Status codes (200, 201, 204, 404, 502) | `http_complete.py` | Section 2 |
| Custom response headers | `http_complete.py` | Section 3 |
| CORS setup | `http_complete.py` | Lines 30-45 |
| Path parameters (`/bookmarks/{id}`) | `routing_complete.py` | Section 2 |
| Query parameters (`?country_code=GB`) | `routing_complete.py` | Section 3 |
| Nested routes (`/bookmarks/{id}/weather`) | `routing_complete.py` | Section 4 |
| Route versioning (`/v1/...`) | `routing_complete.py` | Section 5 |
| Path param validation | `routing_complete.py` | Section 6 |
| Pydantic models (BaseModel) | `validations_complete.py` | Section 1 |
| Field validation (min_length, max) | `validations_complete.py` | Section 2 |
| Custom validators (@field_validator) | `validations_complete.py` | Section 3 |
| Enums | `rest_api_complete.py` | Lines 115-124 |
| Create/Update/Response models | `rest_api_complete.py` | Lines 160-295 |
| List API (pagination, filtering) | `rest_api_complete.py` | Lines 307-389 |
| PATCH (partial update) | `rest_api_complete.py` | Lines 451-484 |
| DELETE (204 No Content) | `rest_api_complete.py` | Lines 486-514 |
| Cache Aside pattern | `caching_complete.py` | Section 1 |
| TTL strategy | `caching_complete.py` | Section 3 |
| Weather API caching (EXACT use case!) | `caching_complete.py` | `/ttl/weather` endpoint |
| Cache invalidation | `caching_complete.py` | Section 8 |
| Handler/Controller layer | `architecture_complete.py` | Component 1 |
| Service layer (business logic) | `architecture_complete.py` | Component 2 |
| Dependency injection (`Depends`) | `architecture_complete.py` | Helper functions |
| Environment variables | `.env` + `python-dotenv` | — |

---

# ⏱️ Suggested Time Breakdown

| Phase | What | Time |
|-------|------|------|
| Phase 1 | Design on paper (Steps 1-7) | 25-35 min |
| Phase 2 | Setup: API key + understand external API (Steps 8-9) | 15-20 min |
| Phase 3a | Project structure + models (Steps 10-11) | 25-35 min |
| Phase 3b | Bookmark CRUD endpoints (Step 12) | 30-40 min |
| Phase 3c | Weather service + weather endpoints (Steps 13-14) | 40-50 min |
| Phase 3d | Cache management (Step 15) | 10-15 min |
| Phase 4 | Testing + design review (Steps 16-17) | 30-45 min |
| **Total** | | **~4-5 hours** |

**Split it across 3 days:**
- **Day 1**: Phase 1 (design) + Phase 2 (setup) + Steps 10-12 (CRUD — should be smooth since you've done this before)
- **Day 2**: Steps 13-14 (weather service — the real new learning!)
- **Day 3**: Step 15 (cache management) + Phase 4 (testing + polish)

---

# 🧠 The Learning Mindset

Remember:
1. **The CRUD endpoints should flow naturally** — you've built this pattern before, and if you can do it from memory, that's a sign of real understanding
2. **The weather service is where the real learning happens** — external API calls, error handling for things you don't control, caching strategies
3. **Your caching lecture already gave you the answer** — `caching_complete.py` Section 3 has EXACTLY the weather caching use case. Use it as direct reference
4. **Run your code after every endpoint** — test in `/docs` constantly
5. **External API errors are different from your errors** — they're things you need to handle gracefully, not bugs to fix

> *"The best backend developers don't just build features — they build features that handle failure gracefully. That's what this project teaches you."*

---

**Ready? Start with Phase 1, Step 1. Open a blank piece of paper and answer: What are your TWO resources?** 🚀
