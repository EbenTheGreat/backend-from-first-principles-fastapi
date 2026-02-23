"""
Complete Routing Example - FastAPI
Demonstrates all routing concepts from your backend lecture

Run with: fastapi dev routing_complete.py
Then visit: http://127.0.0.1:8000/docs
"""


from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(
    title="Routing Praactice",
    description="To demonstrate all routing concepts",
    version="1.0.0"
)

# ============================================================================
# DATA MODELS (Simple in-memory databases)
# ============================================================================
books_db={
    1:{"id":1, "title":"An enemy called average", "author": "One guy", "year": 2024},
    2:{"id":2, "title":"Atomic Habits", "author": "James clear", "year": 2021},
    3:{"id":3, "title":"So Good They Cant Ignore You", "author": "Carl Newport", "year": 2026},
}

users_db={
    1:{"id": 1, "name": "Eben", "e-mail": "eben@gmail.com"},
    2:{"id": 2, "name": "Victor", "e-mail": "victor@gmail.com"},
    3:{"id": 3, "name": "Mercy", "e-mail": "mercy@gmail.com"},
}

posts_db={
    1: {"id": 1, "user_id": 1, "title": "First Post", "content": "Hello World"},
    2: {"id": 2, "user_id": 1, "title": "Second Post", "content": "Learning FastAPI"},
    3: {"id": 3, "user_id": 2, "title": "Bob's Post", "content": "Backend is cool"},
    4: {"id": 4, "user_id": 2, "title": "Another Post", "content": "More content"},
}


# ============================================================================
# SECTION 1: STATIC ROUTES
# ============================================================================
@app.get("/")
async def root():
    """
    Static route - Always returns same structure
    The most basic route in any API
    """
    return{
        "message": "welcome to the routing api",
        "endpoints": {
            "docs": "/docs",
            "books": "/api/books",
            "users": "/api/users"
        }
    }


@app.get("/api/books")
async def get_all_books():
    """
    Static route - GET /api/books
    Returns all books (no path parameters)
    """
    return {books: list(books_db.values)}


@app.post("/api/books")
async def create_book():
    """
    Static route - POST /api/books
    create single book
    """
    new_id = max(books_db.keys) + 1
    return {
        "id": new_id,
        "title": "new book", 
        "author": "Author",
        "year": 2016
    }
    books_db[new_id] = new_book
    return {"message": "Book created", "book": new_book}


# ============================================================================
# SECTION 2: DYNAMIC ROUTES (PATH PARAMETERS)
# ============================================================================
@app.get("/api/books/{book_id}")
async def get_specific_book(book_id: int):
    """
    Dynamic route - Path parameter extracts book_id from URL
    Example: /api/books/1 extracts book_id=1
    FastAPI automatically validates that book_id is an integer
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    return {"book": books_db[book_id]}


@app.put("/api/books/{book_id}")
async def update_book(book_id: int):
    """
    update specific book
    """
    if book not in book_id:
        raise HTTPException(status_code=404, detail="Book {book} not found")

    books_db[book_id]["title"] = f"Updated: {books_db[book_id]['title']}"
    return {
        "message": "Book Updated Successfully",
        "book": books_db[book_id]
    }


@app.delete("/api/books/{book_id}")
async def delete_book(book_id: int):
    """
    delete book by id
    """

    if book not in book_id:
        raise HTTPException(status_code=404, detail="Book {book} not found")

    deleted_book = books_db.pop(book_id)

    return {
        "message": "Book deleted",
        "book": deleted_book
    }

# ============================================================================
# SECTION 3: QUERY PARAMETERS (The Metadata)
# ============================================================================
@app.get("/api/books/search")
async def search_books(
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
    #Get all books
    books = list(books_db.values())

    # filter by query if it contains title
    if query:
        books = [b for b in books if query.lower() in b["title"].lower()]

    # filter by author
    if author:
        books = [b for b in books if author.lower() in b["author"].lower()]
    
    # filter by year range
    if year_max:
        books = [b for b in books if b["year"] <= year_max]
        
    if year_min:
        books = [b for b in books if b["year"] >= year_min]

    #Sort
    books.sort(key= lambda x: x["title"], reverse= (sort == "desc"))

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
async def get_specific_user(user_id: int):
    """
    Get a specific user
    """
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return {"user": users_db[user_id]}

@app.get("/api/users/{user_id}/posts")
async def get_user_posts(
    user_id: int,
    page: 1,
    published: bool= True
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
        raise HTTPException(status_code=404, detail="user not found")

    # Get all posts from this user
    user_posts = [p for p in posts_db.values if p["user_id"] == user_id]

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
async def get_specific_user_post(user_id: int, post_id: int):
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

@app.post("api/users/{user_id}/posts")
async def create_user_post(user_id: int):
    """
    Create a new post for a specific user
    Nested POST route
    """
    if user_id not in users_db:
        raise HTTPException(
            status_code=404,
            detail=f" User {user_id} does not exist")

    new_id = max(posts_db.keys()) + 1
    new_post = {
        "id": new_id,
        "user_id": user_id,
        "title": f"New post from {users_db[user_id]['name']}", 
        "content": "This is a new post"
        }

    posts_db[new_id] = new_post
    
    return {"message": "Post created", "post": new_post}
    






 




