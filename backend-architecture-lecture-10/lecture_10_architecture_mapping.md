# Lecture 10: Backend Architecture Components - FastAPI Complete Mapping

## 📚 Lecture Overview

**Topic**: Backend Architecture - Controllers, Services, Repositories, Middleware, Request Context  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Key Concepts from Your Lecture

### **The Five Core Components**

**1. Handler/Controller** - "The Traffic Cop"
- Entry/exit point for HTTP requests
- Binds (deserializes) JSON → Python objects
- Validates & transforms input
- Calls Service Layer
- Decides HTTP status codes
- **Does NOT** contain business logic

**2. Service Layer** - "The Brain"
- Contains actual business logic
- Protocol-agnostic (no HTTP knowledge)
- Orchestrates operations (multiple repos, external APIs)
- "Just a function" - reusable in CLI, background jobs
- Takes native types, returns native types

**3. Repository Layer** - "The Database Worker"
- Single responsibility: Database queries
- One method = one purpose (granularity rule)
- No business logic, no HTTP knowledge
- Returns raw database entities

**4. Middleware** - "The Checkpoint Pipeline"
- Executes at boundaries (before handlers)
- Has `next()` to pass execution
- Can: Pass through, Modify, or Terminate
- Prevents code duplication
- **Order matters**: CORS → Auth → Rate Limit → Logging → Error Handling

**5. Request Context** - "The Shared State"
- Scoped to single request
- Key-value store for trusted metadata
- Stores User ID from auth (prevents spoofing)
- Request tracing, cancellation signals

---

## 🔄 Complete Request Life Cycle

```
HTTP Request
    ↓
[MIDDLEWARE PIPELINE]
├─ CORS (security - check origin)
├─ Rate Limit (prevent abuse)
├─ Logging (track request)
└─ Auth (verify token → set context)
    ↓
[HANDLER/CONTROLLER]
├─ Binding (JSON → Python object)
├─ Validation (Pydantic automatic)
├─ Transformation (set defaults)
└─ Call Service Layer
    ↓
[SERVICE LAYER]
├─ Business logic
├─ Orchestration
└─ Call Repository Layer(s)
    ↓
[REPOSITORY LAYER]
├─ Construct SQL query
├─ Execute against DB
└─ Return raw data
    ↓
[Back up the chain]
Service → Handler → Middleware → HTTP Response
```

---

## 💡 Key Design Principles

### **1. Separation of Concerns**

| Layer | Knows About | Doesn't Know About |
|-------|-------------|-------------------|
| Handler | HTTP, Validation, Status codes | Business logic, Database |
| Service | Business rules, Orchestration | HTTP, Status codes, SQL |
| Repository | SQL queries, Database | Business logic, HTTP |
| Middleware | Request/Response, Context | Business logic |

### **2. Protocol Agnostic Service**

```python
# ✅ CORRECT: Service doesn't know about HTTP
def create_user(username: str, email: str) -> User:
    # Business logic here
    return user

# ❌ WRONG: Service tied to HTTP
def create_user(request: Request) -> JSONResponse:
    # Can't reuse in CLI or background job
    return JSONResponse({})
```

### **3. Repository Granularity**

```python
# ✅ CORRECT: One method = one purpose
def get_user_by_id(user_id: int) -> User:
    return db.query(User).filter(User.id == user_id).first()

def get_all_users() -> List[User]:
    return db.query(User).all()

# ❌ WRONG: One method, multiple behaviors
def get_users(user_id: Optional[int] = None):
    if user_id:
        return db.query(User).filter(User.id == user_id).first()
    else:
        return db.query(User).all()
```

### **4. Trusted Context Pattern**

```python
# ❌ WRONG: Trust user_id from request body
@app.post("/books")
def create_book(book: BookCreate):
    user_id = book.user_id  # Attacker can spoof this!
    repo.save(book, user_id)

# ✅ CORRECT: Use user_id from trusted context
@app.post("/books")
def create_book(
    book: BookCreate,
    context: RequestContext = Depends(get_context)
):
    user_id = context.user_id  # From verified JWT token
    repo.save(book, user_id)
```

---

## 🏗️ Complete Architecture Implementation

The mapping document above contains extensive working code for:

**Database Models & Setup**
- SQLAlchemy models
- Session management
- Pydantic schemas

**Repository Layer**
- UserRepository with granular methods
- BookRepository
- One method = one query pattern

**Service Layer**
- UserService with business logic
- BookService with orchestration
- Protocol-agnostic design

**Request Context**
- Shared state implementation
- Dependency injection pattern

**Middleware**
- Auth middleware (JWT verification)
- Logging middleware (request tracking)
- Rate limiting middleware

**Handlers/Controllers**
- User handlers (register, get profile, promote)
- Book handlers (create, get, delete)
- Security pattern (context over body)

**Main App**
- Middleware ordering
- Router registration
- Complete assembly

---

## 🔑 Critical Patterns

### **Pattern 1: Dependency Injection**

```python
# FastAPI automatically injects dependencies
def get_service(db: Session = Depends(get_db)) -> Service:
    repo = Repository(db)
    return Service(repo)

@app.post("/items")
def create_item(
    item: ItemCreate,
    service: Service = Depends(get_service)
):
    return service.create(item)
```

### **Pattern 2: Context Security**

```python
# Middleware sets trusted data
async def auth_middleware(request, call_next):
    token = extract_token(request)
    user_id = verify_token(token)
    context = RequestContext.from_request(request)
    context.user_id = user_id  # TRUSTED
    return await call_next(request)

# Handler uses trusted data
@app.post("/resource")
def create(context: RequestContext = Depends(get_context)):
    # Use context.user_id, NOT request body user_id
    return service.create(context.user_id)
```

### **Pattern 3: Service Orchestration**

```python
class Service:
    def __init__(self, repo1, repo2, email_service):
        self.repo1 = repo1
        self.repo2 = repo2
        self.email = email_service
    
    def complex_operation(self, data):
        # Orchestrate multiple operations
        user = self.repo1.get_user(data.user_id)
        order = self.repo2.create_order(data)
        self.email.send_confirmation(user.email)
        return order
```

---

## 🎓 Mastery Checklist

- [ ] Can explain all 5 components?
- [ ] Understand request life cycle?
- [ ] Know separation of concerns?
- [ ] Implement protocol-agnostic service?
- [ ] Use repository granularity?
- [ ] Write middleware with next()?
- [ ] Use request context for security?
- [ ] Order middleware correctly?
- [ ] Prevent identity spoofing?
- [ ] Debug flow through layers?

---

**Last Updated**: 2026-01-29  
**Status**: ✅ Complete Mapping Provided  
**Next**: Build full application with architecture_complete.py
