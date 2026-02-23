# Lecture: Backend Routing - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: The Fundamentals of Backend Routing and URL Mapping  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Key Concepts from Your Lecture

### 1. **Core Routing Mechanism**
- Routing = Mapping incoming requests → server-side logic
- Combination of **Method** (GET/POST) + **Route Path** (`/api/books`) = Unique handler
- Example: `GET /api/books` (fetch) vs `POST /api/books` (create)

### 2. **Types of Routes**
- **Static Routes**: Fixed paths like `/api/books`
- **Dynamic Routes**: Variable segments like `/api/users/:id`
- **Nested Routes**: Hierarchical like `/api/users/123/posts/456`

### 3. **Parameters**
- **Path Parameters**: Part of URL structure, identifies *which* resource
- **Query Parameters**: After `?`, defines *how* to view/filter data
  - Pagination: `?page=2`
  - Filtering: `?query=someValue`
  - Sorting: `?sort=desc`

### 4. **Advanced Concepts**
- **Route Versioning**: `/api/v1/` vs `/api/v2/`
- **Catch-All Routes**: `/*` for 404 handling

---

## 🔗 FastAPI Documentation Mapping

### Exact FastAPI Equivalents

| Your Lecture Concept | FastAPI Tutorial Section | FastAPI Docs URL |
|---------------------|--------------------------|------------------|
| **Static Routes** | First Steps | https://fastapi.tiangolo.com/tutorial/first-steps/ |
| **Dynamic Routes (Path Parameters)** | Path Parameters | https://fastapi.tiangolo.com/tutorial/path-params/ |
| **Query Parameters** | Query Parameters | https://fastapi.tiangolo.com/tutorial/query-params/ |
| **Path Parameter Validation** | Path Parameters and Numeric Validations | https://fastapi.tiangolo.com/tutorial/path-params-numeric-validations/ |
| **Query Parameter Validation** | Query Parameters and String Validations | https://fastapi.tiangolo.com/tutorial/query-params-str-validations/ |
| **HTTP Methods** | First Steps (includes all methods) | https://fastapi.tiangolo.com/tutorial/first-steps/ |
| **Route Versioning** | Sub Applications - Mounts | https://fastapi.tiangolo.com/advanced/sub-applications/ |
| **404 Handling** | Handling Errors | https://fastapi.tiangolo.com/tutorial/handling-errors/ |

---

## 💡 Key Differences: Your Course vs FastAPI

### Syntax Differences

**Your Course (General Backend, likely Express-style):**
```javascript
// Dynamic route with colon syntax
app.get('/api/users/:id', handler)
```

**FastAPI:**
```python
# Dynamic route with curly braces + type hints
@app.get("/api/users/{user_id}")
def handler(user_id: int):
    return {"user_id": user_id}
```

### Key FastAPI Advantages

1. **Automatic Type Validation**: FastAPI validates types automatically
   ```python
   @app.get("/users/{user_id}")
   def get_user(user_id: int):  # Automatically validates as integer
       return {"user_id": user_id}
   ```

2. **Automatic API Documentation**: Routes appear in Swagger UI automatically

3. **Type Hints**: Python type hints provide editor autocomplete and validation

---

## 🏗️ FastAPI Implementation Examples

### 1. Static Route
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/books")
def get_books():
    """Fetch all books - Static route"""
    return {"books": ["Book 1", "Book 2", "Book 3"]}

@app.post("/api/books")
def create_book():
    """Create a book - Same path, different method"""
    return {"message": "Book created"}
```

### 2. Dynamic Route (Path Parameters)
```python
@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    """
    Dynamic route - user_id is extracted from URL
    FastAPI automatically converts to int and validates
    """
    return {
        "user_id": user_id,
        "message": f"Fetching user {user_id}"
    }

# String path parameter
@app.get("/api/users/{username}")
def get_user_by_name(username: str):
    return {"username": username}
```

### 3. Nested Routes
```python
@app.get("/api/users/{user_id}/posts/{post_id}")
def get_user_post(user_id: int, post_id: int):
    """
    Nested route expressing relationship:
    Get a specific post belonging to a specific user
    """
    return {
        "user_id": user_id,
        "post_id": post_id,
        "message": f"Post {post_id} from User {user_id}"
    }
```

### 4. Query Parameters (Metadata)
```python
from typing import Optional

@app.get("/api/products")
def get_products(
    page: int = 1,
    limit: int = 10,
    sort: str = "asc",
    query: Optional[str] = None
):
    """
    Query parameters for filtering/pagination
    - page: which page of results
    - limit: how many items per page
    - sort: sorting order
    - query: search term (optional)
    """
    return {
        "page": page,
        "limit": limit,
        "sort": sort,
        "search": query,
        "products": [f"Product {i}" for i in range(limit)]
    }

# Example calls:
# GET /api/products                              → Uses defaults
# GET /api/products?page=2                       → Page 2, other defaults
# GET /api/products?page=2&limit=20&sort=desc    → Custom values
# GET /api/products?query=laptop                 → With search
```

### 5. Combining Path + Query Parameters
```python
@app.get("/api/users/{user_id}/posts")
def get_user_posts(
    user_id: int,           # Path parameter
    page: int = 1,          # Query parameter
    published: bool = True  # Query parameter
):
    """
    Path param identifies WHICH user
    Query params define HOW to filter their posts
    """
    return {
        "user_id": user_id,
        "page": page,
        "published_only": published,
        "posts": []
    }

# Example: GET /api/users/123/posts?page=2&published=false
```

### 6. Route Versioning
```python
from fastapi import FastAPI

app = FastAPI()

# Version 1 API
@app.get("/api/v1/products")
def get_products_v1():
    """Old structure with 'name' field"""
    return {
        "products": [
            {"id": 1, "name": "Product 1", "price": 10.0}
        ]
    }

# Version 2 API
@app.get("/api/v2/products")
def get_products_v2():
    """New structure with 'title' field"""
    return {
        "products": [
            {"id": 1, "title": "Product 1", "price": 10.0}
        ]
    }
```

### 7. 404 Handling (Catch-All)
```python
from fastapi import HTTPException

@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    # Simulate database lookup
    user_db = {1: "Alice", 2: "Bob"}
    
    if user_id not in user_db:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
    
    return {"user_id": user_id, "name": user_db[user_id]}
```

---

## 🎯 Practice Exercises

### Exercise 1: Basic Routes ✅
**Goal**: Create static routes with different HTTP methods

```python
from fastapi import FastAPI

app = FastAPI()

# TODO: Create these endpoints:
# 1. GET /api/books - Return list of books
# 2. POST /api/books - Create a book
# 3. GET /api/books/{book_id} - Get specific book
# 4. PUT /api/books/{book_id} - Update a book
# 5. DELETE /api/books/{book_id} - Delete a book
```

**Solution**:
```python
from fastapi import FastAPI

app = FastAPI()

# In-memory database
books_db = {
    1: {"id": 1, "title": "1984", "author": "George Orwell"},
    2: {"id": 2, "title": "Brave New World", "author": "Aldous Huxley"}
}

@app.get("/api/books")
def get_books():
    return {"books": list(books_db.values())}

@app.post("/api/books")
def create_book():
    new_id = max(books_db.keys()) + 1
    new_book = {"id": new_id, "title": "New Book", "author": "Unknown"}
    books_db[new_id] = new_book
    return new_book

@app.get("/api/books/{book_id}")
def get_book(book_id: int):
    return books_db.get(book_id, {"error": "Not found"})

@app.put("/api/books/{book_id}")
def update_book(book_id: int):
    if book_id in books_db:
        books_db[book_id]["title"] = "Updated Title"
        return books_db[book_id]
    return {"error": "Not found"}

@app.delete("/api/books/{book_id}")
def delete_book(book_id: int):
    if book_id in books_db:
        deleted = books_db.pop(book_id)
        return {"deleted": deleted}
    return {"error": "Not found"}
```

### Exercise 2: Query Parameters for Filtering ✅
**Goal**: Add pagination and filtering to GET /api/books

```python
# TODO: Modify get_books to accept:
# - page: int (default 1)
# - limit: int (default 10)
# - author: Optional[str] (filter by author)
# - sort: str (default "asc", can be "desc")
```

**Solution**:
```python
from typing import Optional

@app.get("/api/books")
def get_books(
    page: int = 1,
    limit: int = 10,
    author: Optional[str] = None,
    sort: str = "asc"
):
    # Get all books
    books = list(books_db.values())
    
    # Filter by author if provided
    if author:
        books = [b for b in books if author.lower() in b["author"].lower()]
    
    # Sort by title
    books.sort(key=lambda x: x["title"], reverse=(sort == "desc"))
    
    # Pagination
    start = (page - 1) * limit
    end = start + limit
    paginated_books = books[start:end]
    
    return {
        "page": page,
        "limit": limit,
        "total": len(books),
        "books": paginated_books
    }
```

### Exercise 3: Nested Routes ✅
**Goal**: Create a nested resource structure

```python
# TODO: Create these endpoints for users and their posts:
# 1. GET /api/users/{user_id}/posts - Get all posts by user
# 2. GET /api/users/{user_id}/posts/{post_id} - Get specific post
# 3. POST /api/users/{user_id}/posts - Create post for user
```

**Solution**:
```python
# Database
users_db = {
    1: {"id": 1, "name": "Alice"},
    2: {"id": 2, "name": "Bob"}
}

posts_db = {
    1: {"id": 1, "user_id": 1, "title": "Alice's First Post"},
    2: {"id": 2, "user_id": 1, "title": "Alice's Second Post"},
    3: {"id": 3, "user_id": 2, "title": "Bob's Post"}
}

@app.get("/api/users/{user_id}/posts")
def get_user_posts(user_id: int):
    user_posts = [p for p in posts_db.values() if p["user_id"] == user_id]
    return {"user_id": user_id, "posts": user_posts}

@app.get("/api/users/{user_id}/posts/{post_id}")
def get_user_post(user_id: int, post_id: int):
    post = posts_db.get(post_id)
    if post and post["user_id"] == user_id:
        return post
    return {"error": "Post not found for this user"}

@app.post("/api/users/{user_id}/posts")
def create_user_post(user_id: int):
    new_id = max(posts_db.keys()) + 1
    new_post = {"id": new_id, "user_id": user_id, "title": "New Post"}
    posts_db[new_id] = new_post
    return new_post
```

### Exercise 4: Advanced - Route Versioning ✅
**Goal**: Create v1 and v2 of an API with different data structures

```python
# TODO: Create two versions of GET /api/products
# v1: Returns {"name": "Product", "cost": 10}
# v2: Returns {"title": "Product", "price": 10}
```

**Solution**:
```python
@app.get("/api/v1/products")
def get_products_v1():
    return {
        "products": [
            {"id": 1, "name": "Laptop", "cost": 999.99},
            {"id": 2, "name": "Mouse", "cost": 29.99}
        ]
    }

@app.get("/api/v2/products")
def get_products_v2():
    return {
        "products": [
            {"id": 1, "title": "Laptop", "price": 999.99},
            {"id": 2, "title": "Mouse", "price": 29.99}
        ]
    }
```

---

## 🧪 Testing Your Routes

Create `test_routing.py`:

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_books():
    response = client.get("/api/books")
    assert response.status_code == 200
    assert "books" in response.json()

def test_get_book_by_id():
    response = client.get("/api/books/1")
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_query_parameters():
    response = client.get("/api/books?page=2&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["limit"] == 5

def test_nested_route():
    response = client.get("/api/users/1/posts")
    assert response.status_code == 200
    assert "posts" in response.json()
```

Run tests:
```bash
pytest test_routing.py -v
```

---

## 🎓 Mastery Checklist

Before marking this as mastered, can you:

- [ ] Explain the difference between static and dynamic routes?
- [ ] Create routes with path parameters in FastAPI?
- [ ] Implement query parameters for pagination/filtering?
- [ ] Distinguish when to use path vs query parameters?
- [ ] Create nested routes that reflect resource relationships?
- [ ] Implement route versioning?
- [ ] Handle 404 errors properly?
- [ ] Write tests for all route types?
- [ ] Implement a complete CRUD API from scratch?
- [ ] Debug routing conflicts (e.g., overlapping patterns)?

---

## 💭 Reflection & Notes

### What I Learned
- [Your insights here]

### Challenges I Faced
- [Any difficulties]

### Questions for Further Study
1. How does FastAPI handle route precedence when patterns could match multiple routes?
2. What's the performance difference between path and query parameters?
3. How do you handle deeply nested routes (4+ levels)?

### Next Steps
- [ ] Complete all practice exercises
- [ ] Build mini-project: Blog API with users/posts/comments
- [ ] Review path parameter validation in depth
- [ ] Move to next lecture: Request Body/Pydantic Models

---

**Last Updated**: 2026-01-29  
**Time Invested**: [Track your hours]  
**Status**: 🟡 In Progress → 🟢 Mastered (when ready)
