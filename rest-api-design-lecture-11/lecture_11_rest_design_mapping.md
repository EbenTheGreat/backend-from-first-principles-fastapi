# Lecture 11: Complete REST API Design - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Complete REST API Design - Design-First Methodology  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Key Concepts from Your Lecture

### **The Design-First Philosophy**

**NOT a coding task - It's an ARCHITECTURAL PHASE**

REST API design must happen **BEFORE** implementation.

### **1. The Design-First Workflow (6 Phases)**

**Phase 1: Requirement Analysis (UI First)**
- Start with UI/wireframes (Figma)
- Understand how users interact with data
- Map user needs to data needs

**Phase 2: Resource Identification (Nouns)**
- Extract high-level nouns from requirements
- Example: Organization, Project, Task, User
- These become your resources

**Phase 3: Database Schema**
- Design tables based on resources
- Define relationships
- Plan indexes and constraints

**Phase 4: Action Identification (Verbs)**
- CRUD operations (standard)
- Custom actions (clone, archive, send)
- Map to HTTP methods

**Phase 5: Interface Design (No-Code Phase)**
- Use Insomnia/Postman to design endpoints
- Define payloads and responses
- Set status codes
- **Do this BEFORE writing code!**

**Phase 6: Documentation**
- Swagger/OpenAPI from day 1
- Interactive, executable docs
- Formal contract between backend and frontend

### **2. URL and Route Structure Rules**

**Plural Nouns**
- Always use plural: `/books`, `/projects`
- Even for single item: `/books/{id}` (NOT `/book/{id}`)

**Hierarchy**
- Reflect relationships in path
- `/organizations/{org_id}/projects`
- `/projects/{project_id}/tasks`

**Formatting**
- URLs: kebab-case (lowercase with hyphens)
- JSON keys: camelCase
- No underscores, no capitals in paths

**Versioning**
- Always include version: `/api/v1/`
- Enables breaking changes without disrupting clients

### **3. HTTP Methods and Idempotency**

| Method | Purpose | Idempotent | Usage |
|--------|---------|------------|-------|
| GET | Fetch data | ✅ Yes | No side effects, safe to repeat |
| POST | Create resource | ❌ No | Creates new entry each time |
| PUT | Replace entire resource | ✅ Yes | Full replacement |
| PATCH | Update specific fields | ✅ Yes | Partial update (preferred) |
| DELETE | Remove resource | ✅ Yes | Same result if repeated |

**Custom Actions**
- Use POST for custom actions (clone, archive, send)
- Pattern: `POST /resource/{id}/action_name`
- Example: `POST /projects/123/clone`

### **4. Status Codes - Specific Meanings**

**Success Codes**
- `200 OK`: GET, PATCH, Custom Actions
- `201 Created`: POST (new resource created)
- `204 No Content`: DELETE (successful, nothing to return)

**Error Codes**
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Authenticated but no permission
- `404 Not Found`: Specific resource by ID doesn't exist
- `422 Unprocessable Entity`: Validation failed

**Critical Rule: Empty List ≠ 404**
- Empty list: `200 OK` with `data: []`
- 404 only for specific ID that doesn't exist

### **5. List API Requirements (First-Class Concern)**

**Pagination (Mandatory)**
- Parameters: `page`, `limit`
- Defaults: `page=1`, `limit=10`
- Prevents unbounded datasets

**Response Structure (Envelope)**
```json
{
  "data": [...],        // Array of resources
  "total": 100,         // Total count
  "page": 1,            // Current page
  "totalPages": 10      // Computed pages
}
```

**Sorting (Deterministic)**
- Parameters: `sortBy`, `sortOrder`
- Defaults: `sortBy=createdAt`, `sortOrder=desc`
- Database doesn't guarantee order without explicit sort

**Filtering (Query-Level)**
- Field-value pairs: `?status=active`
- Composes with pagination and sorting
- Avoids endpoint explosion

**Sane Defaults (Zero-Config)**
- API works without parameters
- Predictable behavior
- Prevents accidental full-table scans

### **6. Best Practices (The 5 Principles)**

**1. Interactive Documentation**
- Swagger/OpenAPI from day 1
- Executable, not static
- Formal contract

**2. Consistency Is King**
- Same field names across all resources
- If one uses `description`, all use `description`
- Never: `desc`, `details`, `summary` interchangeably

**3. Sane Defaults**
- List APIs work without parameters
- POST creates with logical defaults
- Reduces integration friction

**4. Avoid Abbreviations**
- Use full words: `description` not `desc`
- Clarity > brevity
- APIs are long-lived contracts

**5. Design-First Mindset**
- Design interface before implementation
- Use Insomnia/Postman
- Prevents implementation details leaking to API

---

## 🔗 FastAPI Documentation Mapping

| Your Lecture Concept | FastAPI Feature | Docs URL |
|---------------------|----------------|----------|
| **API Design** | Path Operations | https://fastapi.tiangolo.com/tutorial/first-steps/ |
| **Pagination** | Query Parameters | https://fastapi.tiangolo.com/tutorial/query-params/ |
| **Filtering** | Query Params Validation | https://fastapi.tiangolo.com/tutorial/query-params-str-validations/ |
| **Sorting** | Query with Enums | https://fastapi.tiangolo.com/tutorial/path-params/ |
| **Versioning** | Sub Applications | https://fastapi.tiangolo.com/advanced/sub-applications/ |
| **Documentation** | OpenAPI | https://fastapi.tiangolo.com/tutorial/metadata/ |
| **Response Models** | Response Model | https://fastapi.tiangolo.com/tutorial/response-model/ |

---

## 💡 FastAPI's Built-in Design Support

### **Automatic OpenAPI Documentation**

FastAPI generates interactive docs automatically!
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI spec: `/openapi.json`

**No extra work needed - design-first from day 1!**

### **Response Models Enforce Contract**

```python
@app.get("/books", response_model=List[BookResponse])
def get_books():
    # FastAPI enforces response shape
    # Returns only fields in BookResponse
    # Validates output automatically
```

### **Query Parameters with Defaults**

```python
@app.get("/books")
def get_books(
    page: int = Query(1, ge=1),        # Default: 1, min: 1
    limit: int = Query(10, ge=1, le=100),  # Default: 10, range: 1-100
    sort_by: str = Query("created_at"),    # Default: created_at
    sort_order: str = Query("desc")        # Default: desc
):
    # Sane defaults built-in!
```

---

## 🏗️ Complete REST API Design Examples

### PART 1: URL STRUCTURE & VERSIONING

```python
from fastapi import FastAPI, APIRouter

# Create versioned routers
v1_router = APIRouter(prefix="/api/v1")

@v1_router.get("/books")  # Good: plural noun
def get_books_v1():
    """
    URL STRUCTURE RULES:
    
    ✅ CORRECT:
    - /api/v1/books (plural)
    - /api/v1/books/{id} (plural, even for single)
    - /api/v1/organizations/{org_id}/projects (hierarchy)
    
    ❌ WRONG:
    - /api/v1/book (singular)
    - /api/v1/Book (capital)
    - /api/v1/books_list (underscore)
    - /books (no version)
    """
    return {"books": []}

@v1_router.get("/organizations/{org_id}/projects")
def get_org_projects(org_id: int):
    """
    HIERARCHY in URL
    
    Path reflects relationship:
    - Organization HAS MANY Projects
    - URL shows this: /organizations/{org_id}/projects
    """
    return {"projects": []}

# Later: v2 with breaking changes
v2_router = APIRouter(prefix="/api/v2")

@v2_router.get("/books")
def get_books_v2():
    """
    VERSIONING allows breaking changes
    
    v1 clients: still use /api/v1/books
    v2 clients: use /api/v2/books
    Both work simultaneously!
    """
    return {"items": []}  # Changed structure

app = FastAPI()
app.include_router(v1_router)
app.include_router(v2_router)
```

### PART 2: HTTP METHODS & IDEMPOTENCY

```python
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI()

class BookCreate(BaseModel):
    title: str
    author: str

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None

# GET - Idempotent (safe to repeat)
@app.get("/api/v1/books/{book_id}")
def get_book(book_id: int):
    """
    GET: Fetch data
    
    Idempotent: ✅ YES
    - Calling 100 times = same result
    - No side effects
    - Safe to cache
    """
    return {"id": book_id, "title": "1984"}

# POST - Non-idempotent (creates each time)
@app.post("/api/v1/books", status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate):
    """
    POST: Create resource
    
    Idempotent: ❌ NO
    - Calling 3 times = 3 books created
    - Each call creates new entry
    
    Status Code: 201 Created (not 200!)
    """
    book_id = 123  # From database
    return {"id": book_id, **book.dict()}

# PATCH - Idempotent (partial update)
@app.patch("/api/v1/books/{book_id}")
def update_book(book_id: int, updates: BookUpdate):
    """
    PATCH: Partial update
    
    Idempotent: ✅ YES
    - Calling 100 times with same data = same result
    - Only updates specified fields
    
    Preferred over PUT for JSON APIs
    """
    # Update only provided fields
    return {"id": book_id, "title": "Updated"}

# DELETE - Idempotent
@app.delete("/api/v1/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int):
    """
    DELETE: Remove resource
    
    Idempotent: ✅ YES
    - First call: deletes book
    - Second call: book already gone, same result
    
    Status Code: 204 No Content (nothing to return)
    """
    # Delete from database
    return  # No body for 204

# CUSTOM ACTION - Use POST
@app.post("/api/v1/projects/{project_id}/clone")
def clone_project(project_id: int):
    """
    CUSTOM ACTION: Clone a project
    
    Method: POST (open-ended in REST spec)
    Pattern: /resource/{id}/action_name
    
    Other examples:
    - POST /projects/{id}/archive
    - POST /emails/{id}/send
    - POST /tasks/{id}/complete
    """
    new_project_id = 456
    return {"cloned_project_id": new_project_id}
```

### PART 3: LIST API WITH ALL FEATURES

```python
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import math

app = FastAPI()

# Response envelope model
class PaginatedResponse(BaseModel):
    """
    LIST API ENVELOPE
    
    Not just an array - includes metadata!
    Enables frontend to render pagination controls
    """
    data: List[dict]
    total: int
    page: int
    totalPages: int = Field(..., alias="total_pages")
    
    class Config:
        populate_by_name = True

class SortOrder(str, Enum):
    """Enum for sort order"""
    ASC = "asc"
    DESC = "desc"

@app.get("/api/v1/books", response_model=PaginatedResponse)
def get_books(
    # PAGINATION (with sane defaults)
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    
    # SORTING (with sane defaults)
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort direction"),
    
    # FILTERING (optional)
    status: Optional[str] = Query(None, description="Filter by status"),
    author: Optional[str] = Query(None, description="Filter by author")
):
    """
    COMPLETE LIST API
    
    Features:
    1. PAGINATION - bounded results
    2. SORTING - deterministic order
    3. FILTERING - query-level narrowing
    4. SANE DEFAULTS - works without parameters
    5. ENVELOPE - includes metadata
    
    Sane Defaults:
    - page=1
    - limit=10
    - sort_by=created_at
    - sort_order=desc
    
    Examples:
    - /api/v1/books
      → Returns page 1, 10 items, sorted by created_at desc
    
    - /api/v1/books?page=2&limit=20
      → Returns page 2, 20 items
    
    - /api/v1/books?status=published&author=Orwell
      → Filtered results
    
    - /api/v1/books?sort_by=title&sort_order=asc
      → Sorted by title A-Z
    """
    # Simulated database query
    # In production: use SQL with LIMIT, OFFSET, ORDER BY, WHERE
    
    # Build query filters
    filters = {}
    if status:
        filters["status"] = status
    if author:
        filters["author"] = author
    
    # Simulated data
    all_books = [
        {"id": 1, "title": "1984", "author": "Orwell", "created_at": "2024-01-01"},
        {"id": 2, "title": "Brave New World", "author": "Huxley", "created_at": "2024-01-02"},
        # ... more books
    ]
    
    # Apply filters
    filtered_books = all_books  # Apply filters in real app
    
    # Get total count
    total = len(filtered_books)
    
    # Calculate pagination
    offset = (page - 1) * limit
    paginated_books = filtered_books[offset:offset + limit]
    
    # Calculate total pages
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    # CRITICAL: Empty list returns 200, NOT 404!
    return {
        "data": paginated_books,
        "total": total,
        "page": page,
        "total_pages": total_pages
    }

@app.get("/api/v1/books/{book_id}")
def get_book_by_id(book_id: int):
    """
    GET SINGLE RESOURCE
    
    Returns:
    - 200 OK: Book found
    - 404 Not Found: Specific ID doesn't exist
    
    Note: This is different from list API!
    - List with no results: 200 OK, data: []
    - Single resource not found: 404
    """
    # Simulated database lookup
    book = None  # Assume not found
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found"
        )
    
    return book
```

### PART 4: CONSISTENCY & NAMING

```python
from pydantic import BaseModel
from typing import Optional

# ✅ GOOD: Consistent naming across resources

class BookResponse(BaseModel):
    """
    CONSISTENCY RULES:
    
    1. JSON keys: camelCase
    2. Same field names across all resources
    3. No abbreviations
    4. Full, descriptive names
    """
    id: int
    title: str
    author: str
    description: str  # ✅ Full word
    createdAt: str    # ✅ camelCase
    updatedAt: str
    
    class Config:
        # FastAPI will convert snake_case to camelCase
        populate_by_name = True

class ProjectResponse(BaseModel):
    """
    CONSISTENCY: Use same field names
    
    If Book uses 'description', Project uses 'description'
    NOT: desc, details, summary
    """
    id: int
    name: str
    description: str  # ✅ Consistent with Book
    createdAt: str
    updatedAt: str

# ❌ BAD: Inconsistent naming

class BadBookResponse(BaseModel):
    id: int
    Title: str        # ❌ Capital letter
    author_name: str  # ❌ snake_case in JSON
    desc: str         # ❌ Abbreviation
    created: str      # ❌ Inconsistent with updatedAt

class BadProjectResponse(BaseModel):
    id: int
    name: str
    details: str      # ❌ Different from Book (description)
    dateCreated: str  # ❌ Different pattern

@app.get("/api/v1/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int):
    """
    CONSISTENCY IN PRACTICE:
    
    Frontend developer learns:
    - All timestamps: createdAt, updatedAt
    - All descriptions: description
    - All IDs: id (not book_id, bookId, ID)
    
    Predictable API = Happy developers!
    """
    return {
        "id": book_id,
        "title": "1984",
        "author": "George Orwell",
        "description": "Dystopian novel",  # ✅ Not desc
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z"
    }
```

### PART 5: DESIGN-FIRST WITH SWAGGER

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="Library Management API",
    description="Complete REST API following design-first principles",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "books",
            "description": "Operations with books"
        },
        {
            "name": "authors",
            "description": "Operations with authors"
        }
    ]
)

class BookCreate(BaseModel):
    """
    INTERACTIVE DOCUMENTATION:
    
    FastAPI generates Swagger UI automatically at /docs
    
    Benefits:
    1. Frontend can test API before backend is done
    2. Contract between teams
    3. Executable documentation
    4. No separate docs to maintain
    """
    title: str = Field(..., example="1984", description="Book title")
    author: str = Field(..., example="George Orwell")
    isbn: str = Field(..., example="978-0-452-28423-4", pattern=r"^\d{3}-\d-\d{3}-\d{5}-\d$")
    description: str = Field(
        ...,
        example="A dystopian social science fiction novel",
        min_length=10,
        max_length=500
    )

@app.post(
    "/api/v1/books",
    tags=["books"],
    summary="Create a new book",
    description="Add a new book to the library collection",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Book created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "title": "1984",
                        "author": "George Orwell",
                        "isbn": "978-0-452-28423-4",
                        "description": "A dystopian novel",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-01T00:00:00Z"
                    }
                }
            }
        },
        400: {"description": "Invalid input"},
        422: {"description": "Validation error"}
    }
)
def create_book(book: BookCreate):
    """
    DESIGN-FIRST IN ACTION:
    
    1. This endpoint was designed in Swagger/Insomnia FIRST
    2. Contract agreed upon with frontend
    3. Then implemented
    
    FastAPI makes this easy:
    - Auto-generated Swagger UI
    - Interactive testing
    - Examples in documentation
    - Clear error responses
    """
    # Implementation comes after design
    return {
        "id": 1,
        **book.dict(),
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z"
    }
```

### PART 6: COMPLETE DESIGN CHECKLIST

```python
@app.get("/design-checklist")
def design_checklist():
    """Complete REST API Design Checklist"""
    return {
        "design_workflow": {
            "phase_1": "Analyze UI/wireframes (understand user needs)",
            "phase_2": "Identify resources (extract nouns)",
            "phase_3": "Design database schema",
            "phase_4": "Identify actions (CRUD + custom)",
            "phase_5": "Design interface in Postman/Insomnia (NO CODE YET)",
            "phase_6": "Generate OpenAPI documentation"
        },
        "url_structure": {
            "plural_nouns": "/books not /book",
            "hierarchy": "/organizations/{id}/projects",
            "formatting": "kebab-case for URLs",
            "versioning": "/api/v1/ always",
            "examples": {
                "good": [
                    "/api/v1/books",
                    "/api/v1/books/{id}",
                    "/api/v1/organizations/{org_id}/projects"
                ],
                "bad": [
                    "/book",
                    "/Books",
                    "/api/books_list",
                    "/books"
                ]
            }
        },
        "http_methods": {
            "GET": "Fetch (idempotent, no side effects)",
            "POST": "Create (non-idempotent) + Custom actions",
            "PATCH": "Partial update (preferred over PUT)",
            "DELETE": "Remove (idempotent)",
            "custom_actions": "POST /resource/{id}/action_name"
        },
        "status_codes": {
            "200": "OK - GET, PATCH, custom actions",
            "201": "Created - POST new resource",
            "204": "No Content - DELETE success",
            "400": "Bad Request - invalid input",
            "401": "Unauthorized - not authenticated",
            "403": "Forbidden - no permission",
            "404": "Not Found - specific ID missing",
            "422": "Unprocessable Entity - validation failed",
            "important": "Empty list = 200 with data:[], NOT 404"
        },
        "list_api_requirements": {
            "pagination": {
                "params": ["page", "limit"],
                "defaults": {"page": 1, "limit": 10},
                "mandatory": "Prevents unbounded datasets"
            },
            "sorting": {
                "params": ["sortBy", "sortOrder"],
                "defaults": {"sortBy": "createdAt", "sortOrder": "desc"},
                "reason": "Database doesn't guarantee order"
            },
            "filtering": {
                "method": "Query parameters (?status=active)",
                "composable": "Works with pagination and sorting"
            },
            "response_envelope": {
                "required_fields": ["data", "total", "page", "totalPages"],
                "enables": "Frontend pagination UI"
            }
        },
        "best_practices": {
            "1_interactive_docs": "Swagger/OpenAPI from day 1",
            "2_consistency": "Same field names across all resources",
            "3_sane_defaults": "API works without parameters",
            "4_no_abbreviations": "description not desc",
            "5_design_first": "Design interface before implementation"
        },
        "naming_conventions": {
            "json_keys": "camelCase",
            "urls": "kebab-case",
            "path_segments": "plural nouns",
            "consistency_rule": "If one resource uses 'description', all use 'description'"
        }
    }
```

---

## 🎯 Practice Exercises

### Exercise 1: Design Book API ✅
```python
# TODO:
# 1. Design complete CRUD for books
# 2. Add list endpoint with pagination, sorting, filtering
# 3. Add custom action: POST /books/{id}/publish
# 4. Test in Swagger UI (/docs)
```

### Exercise 2: Nested Resources ✅
```python
# TODO:
# 1. Design: /authors/{id}/books
# 2. Implement list with pagination
# 3. Ensure consistent naming with /books
```

### Exercise 3: Versioning ✅
```python
# TODO:
# 1. Create /api/v1/users
# 2. Create /api/v2/users with different structure
# 3. Both versions work simultaneously
```

---

## 🎓 Mastery Checklist

- [ ] Understand design-first workflow?
- [ ] Can identify resources (nouns)?
- [ ] Know URL structure rules?
- [ ] Understand HTTP method idempotency?
- [ ] Implement complete list API?
- [ ] Create response envelopes?
- [ ] Apply sane defaults?
- [ ] Maintain consistency?
- [ ] Avoid abbreviations?
- [ ] Generate interactive documentation?

---

## 💭 Key Principles Summary

### **Design Philosophy**

**APIs are products, not just implementations**

1. Design interface before code
2. Use tools (Postman/Insomnia) to design
3. Generate OpenAPI docs automatically
4. Formal contract between teams

### **The 5 Pillars**

1. **Interactive Documentation** - Executable, not static
2. **Consistency** - Same patterns everywhere
3. **Sane Defaults** - Zero-config usability
4. **Clarity** - No abbreviations
5. **Design-First** - Interface before implementation

---

**Last Updated**: 2026-01-29  
**Status**: 🟡 In Progress  
**Next**: Build complete REST API following all principles
