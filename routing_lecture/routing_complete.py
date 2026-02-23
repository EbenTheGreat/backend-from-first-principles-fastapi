"""
Complete Routing Example - FastAPI
Demonstrates all routing concepts from your backend lecture

Run with: fastapi dev routing_complete.py
Then visit: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException, Query, Path
from typing import Optional, List
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(
    title="Backend Routing Complete Example",
    description="Demonstrates static routes, dynamic routes, nested routes, query params, and more",
    version="1.0.0"
)

# ============================================================================
# DATA MODELS (Simple in-memory databases)
# ============================================================================

books_db = {
    1: {"id": 1, "title": "1984", "author": "George Orwell", "year": 1949},
    2: {"id": 2, "title": "Brave New World", "author": "Aldous Huxley", "year": 1932},
    3: {"id": 3, "title": "Fahrenheit 451", "author": "Ray Bradbury", "year": 1953},
}

users_db = {
    1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
    2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
    3: {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
}

posts_db = {
    1: {"id": 1, "user_id": 1, "title": "First Post", "content": "Hello World"},
    2: {"id": 2, "user_id": 1, "title": "Second Post", "content": "Learning FastAPI"},
    3: {"id": 3, "user_id": 2, "title": "Bob's Post", "content": "Backend is cool"},
    4: {"id": 4, "user_id": 2, "title": "Another Post", "content": "More content"},
}

# ============================================================================
# SECTION 1: STATIC ROUTES
# ============================================================================

@app.get("/")
def root():
    """
    Static route - Always returns same structure
    The most basic route in any API
    """
    return {
        "message": "Welcome to the Routing API",
        "endpoints": {
            "docs": "/docs",
            "books": "/api/books",
            "users": "/api/users"
        }
    }

@app.get("/api/books")
def get_all_books():
    """
    Static route - GET /api/books
    Returns all books (no path parameters)
    """
    return {"books": list(books_db.values())}

@app.post("/api/books")
def create_book():
    """
    Static route - POST /api/books
    Same path as GET, but different METHOD = different handler
    This demonstrates that Method + Path = Unique route
    """
    new_id = max(books_db.keys()) + 1
    new_book = {
        "id": new_id,
        "title": "New Book",
        "author": "Unknown Author",
        "year": 2024
    }
    books_db[new_id] = new_book
    return {"message": "Book created", "book": new_book}

# ============================================================================
# SECTION 2: DYNAMIC ROUTES (PATH PARAMETERS)
# ============================================================================

@app.get("/api/books/{book_id}")
def get_book_by_id(book_id: int):
    """
    Dynamic route - Path parameter extracts book_id from URL
    Example: /api/books/1 extracts book_id=1
    FastAPI automatically validates that book_id is an integer
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    
    return {"book": books_db[book_id]}

@app.put("/api/books/{book_id}")
def update_book(book_id: int):
    """
    Dynamic route - PUT method for updates
    Same path pattern as GET, but different method
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    
    books_db[book_id]["title"] = f"Updated: {books_db[book_id]['title']}"
    return {"message": "Book updated", "book": books_db[book_id]}

@app.delete("/api/books/{book_id}")
def delete_book(book_id: int):
    """
    Dynamic route - DELETE method
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    
    deleted_book = books_db.pop(book_id)
    return {"message": "Book deleted", "book": deleted_book}

# ============================================================================
# SECTION 3: QUERY PARAMETERS (The Metadata)
# ============================================================================

@app.get("/api/books/search")
def search_books(
    query: Optional[str] = None,
    author: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    page: int = 1,
    limit: int = 10,
    sort: str = "asc"
):
    """
    Query parameters for filtering, searching, pagination, and sorting
    
    Example URLs:
    - /api/books/search?query=1984
    - /api/books/search?author=Orwell
    - /api/books/search?year_min=1940&year_max=1960
    - /api/books/search?page=2&limit=5
    - /api/books/search?sort=desc
    - /api/books/search?query=brave&sort=desc&limit=20
    
    Query params define HOW to view the data, not WHICH resource
    """
    books = list(books_db.values())
    
    # Filter by search query (title contains)
    if query:
        books = [b for b in books if query.lower() in b["title"].lower()]
    
    # Filter by author
    if author:
        books = [b for b in books if author.lower() in b["author"].lower()]
    
    # Filter by year range
    if year_min:
        books = [b for b in books if b["year"] >= year_min]
    if year_max:
        books = [b for b in books if b["year"] <= year_max]
    
    # Sort
    books.sort(key=lambda x: x["title"], reverse=(sort == "desc"))
    
    # Pagination
    total = len(books)
    start = (page - 1) * limit
    end = start + limit
    paginated_books = books[start:end]
    
    return {
        "query": query,
        "filters": {"author": author, "year_min": year_min, "year_max": year_max},
        "page": page,
        "limit": limit,
        "total": total,
        "results": len(paginated_books),
        "books": paginated_books
    }

# ============================================================================
# SECTION 4: NESTED ROUTES (Resource Relationships)
# ============================================================================

@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    """
    Get a specific user
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    return {"user": users_db[user_id]}

@app.get("/api/users/{user_id}/posts")
def get_user_posts(
    user_id: int,
    published: bool = True,
    page: int = 1,
    limit: int = 10
):
    """
    Nested route - Get all posts belonging to a specific user
    
    Path parameter (user_id) identifies WHICH user
    Query parameters filter HOW to view their posts
    
    Example: /api/users/1/posts?page=2&published=true
    
    This route expresses the semantic relationship:
    "Posts belong to Users"
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    # Get all posts for this user
    user_posts = [p for p in posts_db.values() if p["user_id"] == user_id]
    
    # Pagination
    start = (page - 1) * limit
    end = start + limit
    paginated_posts = user_posts[start:end]
    
    return {
        "user_id": user_id,
        "user": users_db[user_id],
        "page": page,
        "limit": limit,
        "total_posts": len(user_posts),
        "posts": paginated_posts
    }

@app.get("/api/users/{user_id}/posts/{post_id}")
def get_user_post(user_id: int, post_id: int):
    """
    Deeply nested route - Get a SPECIFIC post from a SPECIFIC user
    
    Example: /api/users/1/posts/2
    
    This tells the server:
    1. Find User with ID 1
    2. Look at their posts
    3. Return Post with ID 2
    
    Both identifiers (user_id and post_id) must match
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
    
    post = posts_db[post_id]
    
    # Verify the post actually belongs to this user
    if post["user_id"] != user_id:
        raise HTTPException(
            status_code=404,
            detail=f"Post {post_id} does not belong to User {user_id}"
        )
    
    return {
        "user": users_db[user_id],
        "post": post
    }

@app.post("/api/users/{user_id}/posts")
def create_user_post(user_id: int):
    """
    Create a new post for a specific user
    Nested POST route
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    new_id = max(posts_db.keys()) + 1
    new_post = {
        "id": new_id,
        "user_id": user_id,
        "title": f"New post from {users_db[user_id]['name']}",
        "content": "This is a new post"
    }
    posts_db[new_id] = new_post
    
    return {"message": "Post created", "post": new_post}

# ============================================================================
# SECTION 5: ROUTE VERSIONING
# ============================================================================

@app.get("/api/v1/products")
def get_products_v1():
    """
    Version 1 API - Old structure
    Uses 'name' and 'cost' fields
    
    This version is maintained for backward compatibility
    while clients migrate to v2
    """
    return {
        "version": "v1",
        "products": [
            {"id": 1, "name": "Laptop", "cost": 999.99},
            {"id": 2, "name": "Mouse", "cost": 29.99},
            {"id": 3, "name": "Keyboard", "cost": 79.99}
        ]
    }

@app.get("/api/v2/products")
def get_products_v2():
    """
    Version 2 API - New structure
    Uses 'title' and 'price' fields instead
    
    Clients can migrate at their own pace
    When all clients are on v2, we can deprecate v1
    """
    return {
        "version": "v2",
        "products": [
            {"id": 1, "title": "Laptop", "price": 999.99, "category": "Electronics"},
            {"id": 2, "title": "Mouse", "price": 29.99, "category": "Accessories"},
            {"id": 3, "title": "Keyboard", "price": 79.99, "category": "Accessories"}
        ]
    }

# ============================================================================
# SECTION 6: PATH PARAMETER VALIDATION
# ============================================================================

@app.get("/api/items/{item_id}")
def get_item_with_validation(
    item_id: int = Path(
        ...,
        title="Item ID",
        description="The ID of the item to retrieve",
        ge=1,  # Greater than or equal to 1
        le=1000  # Less than or equal to 1000
    )
):
    """
    Path parameter with validation constraints
    - item_id must be between 1 and 1000
    - FastAPI automatically returns 422 error if validation fails
    
    Try: /api/items/0 (fails - too small)
    Try: /api/items/1001 (fails - too large)
    Try: /api/items/500 (succeeds)
    """
    return {
        "item_id": item_id,
        "message": f"Item {item_id} retrieved successfully"
    }

# ============================================================================
# SECTION 7: COMBINING EVERYTHING
# ============================================================================

@app.get("/api/users/{user_id}/posts/{post_id}/comments")
def get_post_comments(
    user_id: int = Path(..., ge=1),
    post_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Complex route combining:
    - Multiple path parameters (user_id, post_id)
    - Multiple query parameters (page, limit)
    - Validation on both types
    
    This represents a 3-level deep resource hierarchy:
    Users → Posts → Comments
    
    Example: /api/users/1/posts/2/comments?page=1&limit=20
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    if post_id not in posts_db:
        raise HTTPException(status_code=404, detail="Post not found")
    
    post = posts_db[post_id]
    if post["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Post doesn't belong to user")
    
    # Mock comments (in real app, would query from database)
    comments = [
        {"id": 1, "post_id": post_id, "text": "Great post!"},
        {"id": 2, "post_id": post_id, "text": "Very informative"},
    ]
    
    return {
        "user": users_db[user_id],
        "post": post,
        "page": page,
        "limit": limit,
        "comments": comments
    }

# ============================================================================
# SECTION 8: CATCH-ALL / 404 HANDLING
# ============================================================================

# Note: In FastAPI, unmatched routes automatically return 404
# But you can create custom 404 handlers like this:

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    """
    Custom 404 handler - Catch-all for undefined routes
    When no route matches, this returns a friendly message
    """
    return JSONResponse(
        status_code=404,
        content={
            "error": "Route not found",
            "message": f"The path '{request.url.path}' does not exist",
            "suggestion": "Visit /docs to see available endpoints"
        }
    )

# ============================================================================
# BONUS: HEALTH CHECK & INFO
# ============================================================================

@app.get("/health")
def health_check():
    """Standard health check endpoint"""
    return {"status": "healthy", "service": "routing-api"}

@app.get("/api/stats")
def get_stats():
    """
    Get API statistics
    Demonstrates how you might create utility endpoints
    """
    return {
        "total_books": len(books_db),
        "total_users": len(users_db),
        "total_posts": len(posts_db),
        "endpoints": {
            "books": 4,
            "users": 2,
            "posts": 3,
            "products": 2,
            "utility": 3
        }
    }

# ============================================================================
# RUN INSTRUCTIONS
# ============================================================================
"""
To run this file:

1. Save as 'routing_complete.py'

2. Run with FastAPI CLI:
   $ fastapi dev routing_complete.py

3. Visit the interactive docs:
   - Swagger UI: http://127.0.0.1:8000/docs
   - ReDoc: http://127.0.0.1:8000/redoc

4. Try these example requests:
   - GET  http://127.0.0.1:8000/
   - GET  http://127.0.0.1:8000/api/books
   - GET  http://127.0.0.1:8000/api/books/1
   - GET  http://127.0.0.1:8000/api/books/search?query=1984
   - GET  http://127.0.0.1:8000/api/users/1/posts
   - GET  http://127.0.0.1:8000/api/users/1/posts/1
   - GET  http://127.0.0.1:8000/api/v1/products
   - POST http://127.0.0.1:8000/api/books

5. Or use curl:
   $ curl http://127.0.0.1:8000/api/books
   $ curl http://127.0.0.1:8000/api/users/1/posts?page=1
"""
