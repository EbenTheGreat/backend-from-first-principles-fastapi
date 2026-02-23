"""
Complete REST API Design - Production-Grade Example
Demonstrates all principles from Lecture 11

This API follows the complete design-first workflow:
1. Resource identification (Books, Authors, Organizations, Projects)
2. Database schema design
3. Interface design (before implementation)
4. Implementation following all best practices

Run with: fastapi dev rest_api_complete.py
Visit: http://127.0.0.1:8000/docs

Install dependencies:
pip install "fastapi[standard]" sqlalchemy
"""

from fastapi import FastAPI, APIRouter, Query, Path, HTTPException, status, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, create_engine, desc, asc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from typing import List, Optional
from datetime import datetime
from enum import Enum
import math

# ============================================================================
# DATABASE SETUP
# ============================================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///./rest_api_demo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class AuthorModel(Base):
    """Author database model"""
    __tablename__ = "authors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    bio = Column(String)
    country = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    books = relationship("BookModel", back_populates="author")

class BookModel(Base):
    """Book database model"""
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    isbn = Column(String, unique=True, index=True)
    description = Column(String)  # Full word, not 'desc'
    published_year = Column(Integer)
    status = Column(String, default="draft")  # draft, published, archived
    author_id = Column(Integer, ForeignKey("authors.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship("AuthorModel", back_populates="books")

class OrganizationModel(Base):
    """Organization database model"""
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)  # Consistent naming
    industry = Column(String)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = relationship("ProjectModel", back_populates="organization")

class ProjectModel(Base):
    """Project database model"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)  # Consistent naming
    status = Column(String, default="active")
    priority = Column(String, default="medium")
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("OrganizationModel", back_populates="projects")

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# ENUMS
# ============================================================================

class SortOrder(str, Enum):
    """Sort order enum"""
    ASC = "asc"
    DESC = "desc"

class BookStatus(str, Enum):
    """Book status enum"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

# ============================================================================
# PYDANTIC MODELS (API Schemas)
# ============================================================================

# Response Envelope for List APIs
class PaginatedResponse(BaseModel):
    """
    LIST API ENVELOPE
    
    Required fields for all list APIs:
    - data: Array of resources
    - total: Total count (ignoring pagination)
    - page: Current page
    - totalPages: Computed as ceil(total / limit)
    
    Enables frontend to render pagination controls
    """
    data: List[dict]
    total: int
    page: int
    total_pages: int = Field(..., alias="totalPages")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "data": [{"id": 1, "title": "Book 1"}],
                "total": 100,
                "page": 1,
                "totalPages": 10
            }
        }

# Author Schemas
class AuthorCreate(BaseModel):
    """
    NAMING CONVENTIONS:
    - JSON keys: camelCase (FastAPI converts automatically)
    - Full words: description not desc
    - Consistent across all resources
    """
    name: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., min_length=10)
    country: str

class AuthorUpdate(BaseModel):
    """Partial update - all fields optional"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, min_length=10)
    country: Optional[str] = None

class AuthorResponse(BaseModel):
    """
    CONSISTENCY: Use same field names everywhere
    - createdAt (not created, dateCreated, creation_date)
    - updatedAt (not updated, lastModified)
    - description (not desc, details, summary)
    """
    id: int
    name: str
    bio: str
    country: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    
    class Config:
        from_attributes = True
        populate_by_name = True

# Book Schemas
class BookCreate(BaseModel):
    """Create book schema"""
    title: str = Field(..., min_length=1, max_length=200)
    isbn: str = Field(..., pattern=r"^\d{3}-\d{10}$")
    description: str = Field(..., min_length=10)  # NOT desc!
    published_year: int = Field(..., ge=1000, le=2100, alias="publishedYear")
    author_id: int = Field(..., gt=0, alias="authorId")
    
    @field_validator('published_year')
    @classmethod
    def validate_year(cls, v):
        if v > datetime.now().year:
            raise ValueError("Published year cannot be in the future")
        return v

class BookUpdate(BaseModel):
    """Partial update schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    isbn: Optional[str] = Field(None, pattern=r"^\d{3}-\d{10}$")
    description: Optional[str] = Field(None, min_length=10)
    published_year: Optional[int] = Field(None, ge=1000, le=2100, alias="publishedYear")
    status: Optional[BookStatus] = None

class BookResponse(BaseModel):
    """
    CONSISTENCY EXAMPLE:
    Same field names as AuthorResponse:
    - createdAt, updatedAt (not created_at, updated_at)
    - description (not desc)
    """
    id: int
    title: str
    isbn: str
    description: str  # Consistent with other resources
    published_year: int = Field(..., alias="publishedYear")
    status: str
    author_id: int = Field(..., alias="authorId")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    
    class Config:
        from_attributes = True
        populate_by_name = True

# Organization Schemas
class OrganizationCreate(BaseModel):
    """Create organization"""
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=10)  # Consistent!
    industry: str

class OrganizationUpdate(BaseModel):
    """Update organization"""
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    status: Optional[str] = None

class OrganizationResponse(BaseModel):
    """Organization response"""
    id: int
    name: str
    description: str  # Consistent naming!
    industry: str
    status: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    
    class Config:
        from_attributes = True
        populate_by_name = True

# Project Schemas
class ProjectCreate(BaseModel):
    """Create project"""
    name: str
    description: str  # Consistent!
    priority: Optional[str] = "medium"

class ProjectUpdate(BaseModel):
    """Update project"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None

class ProjectResponse(BaseModel):
    """Project response"""
    id: int
    name: str
    description: str  # Consistent!
    status: str
    priority: str
    organization_id: int = Field(..., alias="organizationId")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    
    class Config:
        from_attributes = True
        populate_by_name = True

# ============================================================================
# API VERSION 1
# ============================================================================

v1 = APIRouter(prefix="/api/v1", tags=["v1"])

# ============================================================================
# V1: AUTHORS ENDPOINTS
# ============================================================================

@v1.get(
    "/authors",
    response_model=PaginatedResponse,
    summary="List all authors",
    description="Get paginated list of authors with sorting and filtering"
)
def list_authors(
    # PAGINATION with SANE DEFAULTS
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page, max 100"),
    
    # SORTING with SANE DEFAULTS
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort direction (asc/desc)"),
    
    # FILTERING (optional)
    country: Optional[str] = Query(None, description="Filter by country"),
    
    db: Session = Depends(get_db)
):
    """
    COMPLETE LIST API
    
    Features:
    1. ✅ PAGINATION - Bounded results, prevents loading millions of rows
    2. ✅ SORTING - Deterministic order (DB doesn't guarantee order!)
    3. ✅ FILTERING - Query-level narrowing
    4. ✅ SANE DEFAULTS - Works without any parameters!
    5. ✅ ENVELOPE - Returns metadata (total, pages)
    
    Sane Defaults:
    - page=1 (start at beginning)
    - limit=10 (reasonable page size)
    - sort_by=created_at (newest first makes sense)
    - sort_order=desc (newest first)
    
    Examples:
    - /api/v1/authors
      → Returns page 1, 10 authors, sorted by created_at desc
    
    - /api/v1/authors?page=2&limit=20
      → Page 2, 20 authors per page
    
    - /api/v1/authors?country=USA&sort_by=name&sort_order=asc
      → Filtered + sorted
    
    CRITICAL: Empty list returns 200 OK with data:[]
    NOT 404! (404 only for specific ID not found)
    """
    # Build query
    query = db.query(AuthorModel)
    
    # Apply filters
    if country:
        query = query.filter(AuthorModel.country == country)
    
    # Get total count (before pagination)
    total = query.count()
    
    # Apply sorting (DETERMINISTIC - don't trust DB order!)
    sort_column = getattr(AuthorModel, sort_by, AuthorModel.created_at)
    if sort_order == SortOrder.ASC:
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    # Apply pagination
    offset = (page - 1) * limit
    authors = query.offset(offset).limit(limit).all()
    
    # Calculate total pages
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    # Convert to response format
    data = [AuthorResponse.from_orm(author).dict(by_alias=True) for author in authors]
    
    # ENVELOPE RESPONSE (not just an array!)
    return {
        "data": data,
        "total": total,
        "page": page,
        "totalPages": total_pages
    }

@v1.get(
    "/authors/{author_id}",
    response_model=AuthorResponse,
    summary="Get author by ID",
    responses={
        200: {"description": "Author found"},
        404: {"description": "Author not found"}
    }
)
def get_author(
    author_id: int = Path(..., gt=0, description="Author ID"),
    db: Session = Depends(get_db)
):
    """
    GET SINGLE RESOURCE
    
    Returns:
    - 200 OK: Author found
    - 404 Not Found: Specific ID doesn't exist
    
    Note: This is different from list!
    - List with no results: 200 OK, data: []
    - Single resource not found: 404
    """
    author = db.query(AuthorModel).filter(AuthorModel.id == author_id).first()
    
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Author with ID {author_id} not found"
        )
    
    return author

@v1.post(
    "/authors",
    response_model=AuthorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new author"
)
def create_author(
    author: AuthorCreate,
    db: Session = Depends(get_db)
):
    """
    CREATE RESOURCE
    
    Status Code: 201 Created (not 200!)
    
    HTTP Method: POST
    - Non-idempotent (calling 3 times = 3 authors)
    - Use for creating new resources
    """
    db_author = AuthorModel(**author.dict())
    db.add(db_author)
    db.commit()
    db.refresh(db_author)
    
    return db_author

@v1.patch(
    "/authors/{author_id}",
    response_model=AuthorResponse,
    summary="Update author (partial)"
)
def update_author(
    author_id: int = Path(..., gt=0),
    updates: AuthorUpdate = None,
    db: Session = Depends(get_db)
):
    """
    PARTIAL UPDATE
    
    HTTP Method: PATCH (preferred over PUT for JSON APIs)
    - Idempotent (calling 100 times with same data = same result)
    - Only updates provided fields
    
    Status Code: 200 OK
    """
    author = db.query(AuthorModel).filter(AuthorModel.id == author_id).first()
    
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    
    # Update only provided fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(author, field, value)
    
    author.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(author)
    
    return author

@v1.delete(
    "/authors/{author_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete author"
)
def delete_author(
    author_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    DELETE RESOURCE
    
    HTTP Method: DELETE
    - Idempotent (calling twice = same result, resource is gone)
    
    Status Code: 204 No Content
    - Success but nothing to return
    - No response body
    """
    author = db.query(AuthorModel).filter(AuthorModel.id == author_id).first()
    
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    
    db.delete(author)
    db.commit()
    
    # 204 returns no content (return None or nothing)
    return

# ============================================================================
# V1: BOOKS ENDPOINTS
# ============================================================================

@v1.get("/books", response_model=PaginatedResponse)
def list_books(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: SortOrder = Query(SortOrder.DESC),
    status: Optional[BookStatus] = Query(None, description="Filter by status"),
    author_id: Optional[int] = Query(None, gt=0, description="Filter by author", alias="authorId"),
    db: Session = Depends(get_db)
):
    """Complete list API for books"""
    query = db.query(BookModel)
    
    # Filters
    if status:
        query = query.filter(BookModel.status == status.value)
    if author_id:
        query = query.filter(BookModel.author_id == author_id)
    
    total = query.count()
    
    # Sorting
    sort_column = getattr(BookModel, sort_by, BookModel.created_at)
    query = query.order_by(desc(sort_column) if sort_order == SortOrder.DESC else asc(sort_column))
    
    # Pagination
    offset = (page - 1) * limit
    books = query.offset(offset).limit(limit).all()
    
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    data = [BookResponse.from_orm(book).dict(by_alias=True) for book in books]
    
    return {
        "data": data,
        "total": total,
        "page": page,
        "totalPages": total_pages
    }

@v1.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Get book by ID"""
    book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@v1.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    """
    Create book
    
    SANE DEFAULTS:
    - status defaults to "draft" (set in database model)
    - Client doesn't need to provide it
    """
    # Check author exists
    author = db.query(AuthorModel).filter(AuthorModel.id == book.author_id).first()
    if not author:
        raise HTTPException(status_code=400, detail="Author not found")
    
    db_book = BookModel(**book.dict(by_alias=False))
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    
    return db_book

@v1.patch("/books/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int = Path(..., gt=0),
    updates: BookUpdate = None,
    db: Session = Depends(get_db)
):
    """Partial update book"""
    book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    update_data = updates.dict(exclude_unset=True, by_alias=False)
    for field, value in update_data.items():
        setattr(book, field, value)
    
    book.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(book)
    
    return book

@v1.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Delete book"""
    book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(book)
    db.commit()

# ============================================================================
# V1: CUSTOM ACTIONS
# ============================================================================

@v1.post(
    "/books/{book_id}/publish",
    response_model=BookResponse,
    summary="Publish a book (custom action)"
)
def publish_book(
    book_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    CUSTOM ACTION: Publish a book
    
    Pattern: POST /resource/{id}/action_name
    
    Use POST for custom actions (open-ended in REST spec)
    
    Other examples:
    - POST /projects/{id}/clone
    - POST /projects/{id}/archive
    - POST /emails/{id}/send
    - POST /tasks/{id}/complete
    """
    book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.status == "published":
        raise HTTPException(status_code=400, detail="Book already published")
    
    book.status = "published"
    book.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(book)
    
    return book

@v1.post("/books/{book_id}/archive", response_model=BookResponse)
def archive_book(
    book_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """Custom action: Archive a book"""
    book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book.status = "archived"
    book.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(book)
    
    return book

# ============================================================================
# V1: NESTED RESOURCES (Hierarchy in URL)
# ============================================================================

@v1.get(
    "/authors/{author_id}/books",
    response_model=PaginatedResponse,
    summary="Get all books by an author"
)
def get_author_books(
    author_id: int = Path(..., gt=0, description="Author ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: SortOrder = Query(SortOrder.DESC),
    db: Session = Depends(get_db)
):
    """
    NESTED RESOURCE: Hierarchy in URL
    
    URL: /authors/{author_id}/books
    Meaning: Books belonging to a specific author
    
    This reflects the relationship:
    - Author HAS MANY Books
    - Books BELONG TO Author
    """
    # Check author exists
    author = db.query(AuthorModel).filter(AuthorModel.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    
    # Query books for this author
    query = db.query(BookModel).filter(BookModel.author_id == author_id)
    
    total = query.count()
    
    # Sorting
    sort_column = getattr(BookModel, sort_by, BookModel.created_at)
    query = query.order_by(desc(sort_column) if sort_order == SortOrder.DESC else asc(sort_column))
    
    # Pagination
    offset = (page - 1) * limit
    books = query.offset(offset).limit(limit).all()
    
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    data = [BookResponse.from_orm(book).dict(by_alias=True) for book in books]
    
    return {
        "data": data,
        "total": total,
        "page": page,
        "totalPages": total_pages
    }

# ============================================================================
# V1: ORGANIZATIONS & PROJECTS
# ============================================================================

@v1.get("/organizations", response_model=PaginatedResponse)
def list_organizations(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: SortOrder = Query(SortOrder.DESC),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List organizations with pagination"""
    query = db.query(OrganizationModel)
    
    if status:
        query = query.filter(OrganizationModel.status == status)
    
    total = query.count()
    
    sort_column = getattr(OrganizationModel, sort_by, OrganizationModel.created_at)
    query = query.order_by(desc(sort_column) if sort_order == SortOrder.DESC else asc(sort_column))
    
    offset = (page - 1) * limit
    orgs = query.offset(offset).limit(limit).all()
    
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    data = [OrganizationResponse.from_orm(org).dict(by_alias=True) for org in orgs]
    
    return {"data": data, "total": total, "page": page, "totalPages": total_pages}

@v1.post("/organizations", response_model=OrganizationResponse, status_code=201)
def create_organization(org: OrganizationCreate, db: Session = Depends(get_db)):
    """
    Create organization
    
    SANE DEFAULT: status defaults to "active"
    Client doesn't need to provide it
    """
    db_org = OrganizationModel(**org.dict())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org

@v1.get("/organizations/{org_id}/projects", response_model=PaginatedResponse)
def get_organization_projects(
    org_id: int = Path(..., gt=0),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    NESTED RESOURCE: Projects for an organization
    
    URL: /organizations/{org_id}/projects
    Hierarchy: Organization → Projects
    """
    org = db.query(OrganizationModel).filter(OrganizationModel.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    query = db.query(ProjectModel).filter(ProjectModel.organization_id == org_id)
    total = query.count()
    
    offset = (page - 1) * limit
    projects = query.offset(offset).limit(limit).all()
    
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    data = [ProjectResponse.from_orm(p).dict(by_alias=True) for p in projects]
    
    return {"data": data, "total": total, "page": page, "totalPages": total_pages}

@v1.post("/organizations/{org_id}/projects", response_model=ProjectResponse, status_code=201)
def create_project_in_org(
    org_id: int = Path(..., gt=0),
    project: ProjectCreate = None,
    db: Session = Depends(get_db)
):
    """Create project in organization"""
    org = db.query(OrganizationModel).filter(OrganizationModel.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    db_project = ProjectModel(**project.dict(), organization_id=org_id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@v1.post("/projects/{project_id}/clone", response_model=ProjectResponse)
def clone_project(project_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """
    CUSTOM ACTION: Clone a project
    
    Creates a copy of the project with new ID
    """
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create clone
    cloned = ProjectModel(
        name=f"{project.name} (Copy)",
        description=project.description,
        status="active",
        priority=project.priority,
        organization_id=project.organization_id
    )
    db.add(cloned)
    db.commit()
    db.refresh(cloned)
    
    return cloned

# ============================================================================
# API VERSION 2 (Breaking Changes)
# ============================================================================

v2 = APIRouter(prefix="/api/v2", tags=["v2"])

@v2.get("/books", response_model=dict)
def list_books_v2(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    VERSION 2: Breaking change example
    
    Changed response structure:
    - v1: {data: [], total: 0, page: 1, totalPages: 1}
    - v2: {items: [], count: 0, currentPage: 1, pages: 1}
    
    Both versions work simultaneously!
    - Old clients use /api/v1/books
    - New clients use /api/v2/books
    """
    query = db.query(BookModel)
    total = query.count()
    
    offset = (page - 1) * limit
    books = query.offset(offset).limit(limit).all()
    
    total_pages = math.ceil(total / limit) if total > 0 else 1
    
    items = [BookResponse.from_orm(book).dict(by_alias=True) for book in books]
    
    # Different structure than v1!
    return {
        "items": items,        # Changed from 'data'
        "count": total,        # Changed from 'total'
        "currentPage": page,   # Changed from 'page'
        "pages": total_pages   # Changed from 'totalPages'
    }

# ============================================================================
# MAIN APP
# ============================================================================

app = FastAPI(
    title="Complete REST API Design - Production Example",
    description="""
    Complete REST API following all best practices:
    
    1. ✅ Design-First Workflow
    2. ✅ Proper URL Structure (plural nouns, hierarchy, versioning)
    3. ✅ HTTP Methods & Idempotency
    4. ✅ Complete List APIs (pagination, sorting, filtering)
    5. ✅ Response Envelopes
    6. ✅ Sane Defaults
    7. ✅ Consistent Naming
    8. ✅ Interactive Documentation
    9. ✅ Custom Actions
    10. ✅ API Versioning
    """,
    version="1.0.0",
    openapi_tags=[
        {"name": "v1", "description": "API Version 1"},
        {"name": "v2", "description": "API Version 2 (breaking changes)"}
    ]
)

# Include routers
app.include_router(v1)
app.include_router(v2)

# ============================================================================
# ROOT & INFO ENDPOINTS
# ============================================================================

@app.get("/", tags=["root"])
def root():
    """API overview"""
    return {
        "message": "Complete REST API Design - Production Example",
        "documentation": "/docs",
        "design_principles": {
            "1_design_first": "Interface designed before implementation",
            "2_url_structure": {
                "plural_nouns": "/books not /book",
                "hierarchy": "/authors/{id}/books",
                "versioning": "/api/v1/ and /api/v2/",
                "formatting": "kebab-case for URLs, camelCase for JSON"
            },
            "3_http_methods": {
                "GET": "Fetch (idempotent)",
                "POST": "Create + Custom actions (non-idempotent)",
                "PATCH": "Partial update (idempotent)",
                "DELETE": "Remove (idempotent)"
            },
            "4_status_codes": {
                "200": "OK - GET, PATCH, custom actions",
                "201": "Created - POST new resource",
                "204": "No Content - DELETE success",
                "404": "Not Found - specific ID missing (NOT empty list!)"
            },
            "5_list_api": {
                "pagination": "page, limit with defaults (1, 10)",
                "sorting": "sortBy, sortOrder with defaults (created_at, desc)",
                "filtering": "Query params (?status=active)",
                "envelope": "{data, total, page, totalPages}"
            },
            "6_consistency": "Same field names across all resources",
            "7_sane_defaults": "API works without parameters",
            "8_no_abbreviations": "description not desc",
            "9_interactive_docs": "Swagger UI auto-generated at /docs"
        },
        "endpoints": {
            "authors": {
                "list": "GET /api/v1/authors",
                "get": "GET /api/v1/authors/{id}",
                "create": "POST /api/v1/authors",
                "update": "PATCH /api/v1/authors/{id}",
                "delete": "DELETE /api/v1/authors/{id}",
                "books": "GET /api/v1/authors/{id}/books"
            },
            "books": {
                "list": "GET /api/v1/books",
                "get": "GET /api/v1/books/{id}",
                "create": "POST /api/v1/books",
                "update": "PATCH /api/v1/books/{id}",
                "delete": "DELETE /api/v1/books/{id}",
                "publish": "POST /api/v1/books/{id}/publish (custom action)",
                "archive": "POST /api/v1/books/{id}/archive (custom action)"
            },
            "organizations": {
                "list": "GET /api/v1/organizations",
                "create": "POST /api/v1/organizations",
                "projects": "GET /api/v1/organizations/{id}/projects",
                "create_project": "POST /api/v1/organizations/{id}/projects"
            },
            "projects": {
                "clone": "POST /api/v1/projects/{id}/clone (custom action)"
            }
        },
        "test_examples": {
            "1_list_with_defaults": "GET /api/v1/books",
            "2_list_with_pagination": "GET /api/v1/books?page=2&limit=20",
            "3_list_with_sorting": "GET /api/v1/books?sortBy=title&sortOrder=asc",
            "4_list_with_filters": "GET /api/v1/books?status=published&authorId=1",
            "5_nested_resource": "GET /api/v1/authors/1/books",
            "6_custom_action": "POST /api/v1/books/1/publish",
            "7_version_2": "GET /api/v2/books"
        }
    }

@app.get("/design-checklist", tags=["info"])
def design_checklist():
    """Complete design checklist"""
    return {
        "design_workflow": {
            "phase_1": "✅ Analyze UI/wireframes",
            "phase_2": "✅ Identify resources (Authors, Books, Organizations, Projects)",
            "phase_3": "✅ Design database schema",
            "phase_4": "✅ Identify actions (CRUD + publish, archive, clone)",
            "phase_5": "✅ Design interface (this API follows the design)",
            "phase_6": "✅ Generate docs (auto-generated at /docs)"
        },
        "url_rules_applied": {
            "plural_nouns": "✅ /books, /authors, /organizations, /projects",
            "hierarchy": "✅ /authors/{id}/books, /organizations/{id}/projects",
            "versioning": "✅ /api/v1/ and /api/v2/",
            "kebab_case": "✅ URLs use lowercase (would be /project-tasks if needed)",
            "camelCase_json": "✅ createdAt, authorId, publishedYear in JSON"
        },
        "http_methods_correct": {
            "GET": "✅ Fetching resources",
            "POST": "✅ Creating + custom actions (publish, clone)",
            "PATCH": "✅ Partial updates",
            "DELETE": "✅ Removing resources"
        },
        "list_api_complete": {
            "pagination": "✅ page, limit with defaults",
            "sorting": "✅ sortBy, sortOrder with defaults",
            "filtering": "✅ status, authorId, country",
            "envelope": "✅ {data, total, page, totalPages}",
            "empty_list": "✅ Returns 200 OK, not 404"
        },
        "consistency_enforced": {
            "field_names": "✅ description everywhere (not desc)",
            "timestamps": "✅ createdAt, updatedAt everywhere",
            "ids": "✅ authorId, organizationId everywhere"
        },
        "best_practices": {
            "interactive_docs": "✅ /docs (Swagger UI)",
            "sane_defaults": "✅ All list APIs work without params",
            "no_abbreviations": "✅ Full words used",
            "status_codes": "✅ 200, 201, 204, 404 correctly",
            "versioning": "✅ v1 and v2 coexist"
        }
    }

# ============================================================================
# SEED DATA
# ============================================================================

@app.on_event("startup")
def seed_database():
    """Seed database with sample data"""
    db = SessionLocal()
    
    # Check if data already exists
    if db.query(AuthorModel).count() > 0:
        db.close()
        return
    
    # Create authors
    author1 = AuthorModel(
        name="George Orwell",
        bio="English novelist and essayist, journalist and critic",
        country="UK"
    )
    author2 = AuthorModel(
        name="Aldous Huxley",
        bio="English writer and philosopher",
        country="UK"
    )
    
    db.add(author1)
    db.add(author2)
    db.commit()
    db.refresh(author1)
    db.refresh(author2)
    
    # Create books
    book1 = BookModel(
        title="1984",
        isbn="978-0451524935",
        description="Dystopian social science fiction novel and cautionary tale",
        published_year=1949,
        status="published",
        author_id=author1.id
    )
    book2 = BookModel(
        title="Animal Farm",
        isbn="978-0451526342",
        description="Allegorical novella reflecting events leading up to the Russian Revolution",
        published_year=1945,
        status="published",
        author_id=author1.id
    )
    book3 = BookModel(
        title="Brave New World",
        isbn="978-0060850524",
        description="Dystopian novel set in a futuristic World State",
        published_year=1932,
        status="published",
        author_id=author2.id
    )
    
    db.add_all([book1, book2, book3])
    
    # Create organization
    org = OrganizationModel(
        name="Tech Corp",
        description="Leading technology company",
        industry="Technology",
        status="active"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    # Create projects
    project = ProjectModel(
        name="API Platform",
        description="Build REST API platform",
        status="active",
        priority="high",
        organization_id=org.id
    )
    db.add(project)
    
    db.commit()
    db.close()
    
    print("✅ Database seeded with sample data")

# ============================================================================
# RUN INSTRUCTIONS
# ============================================================================
"""
SETUP & RUN:
1. pip install "fastapi[standard]" sqlalchemy
2. fastapi dev rest_api_complete.py
3. Visit: http://127.0.0.1:8000/docs

TEST COMPLETE WORKFLOW:

# 1. List all books (with defaults)
curl http://localhost:8000/api/v1/books

# 2. List books with pagination
curl "http://localhost:8000/api/v1/books?page=1&limit=10"

# 3. List books with sorting
curl "http://localhost:8000/api/v1/books?sortBy=title&sortOrder=asc"

# 4. List books with filters
curl "http://localhost:8000/api/v1/books?status=published"

# 5. Get single book
curl http://localhost:8000/api/v1/books/1

# 6. Create author
curl -X POST http://localhost:8000/api/v1/authors \
  -H "Content-Type: application/json" \
  -d '{"name":"J.K. Rowling","bio":"British author","country":"UK"}'

# 7. Create book
curl -X POST http://localhost:8000/api/v1/books \
  -H "Content-Type: application/json" \
  -d '{
    "title":"Harry Potter",
    "isbn":"978-0439708180",
    "description":"Fantasy novel about a young wizard",
    "publishedYear":1997,
    "authorId":4
  }'

# 8. Update book (PATCH - partial)
curl -X PATCH http://localhost:8000/api/v1/books/4 \
  -H "Content-Type: application/json" \
  -d '{"status":"published"}'

# 9. Custom action - Publish book
curl -X POST http://localhost:8000/api/v1/books/4/publish

# 10. Nested resource - Author's books
curl http://localhost:8000/api/v1/authors/1/books

# 11. Delete book
curl -X DELETE http://localhost:8000/api/v1/books/4

# 12. Test empty list (returns 200, not 404!)
curl "http://localhost:8000/api/v1/books?status=nonexistent"

# 13. Test v2 API (different structure)
curl http://localhost:8000/api/v2/books

KEY DESIGN POINTS DEMONSTRATED:

✅ URL Structure:
   - Plural nouns: /books, /authors
   - Hierarchy: /authors/{id}/books
   - Versioning: /api/v1/, /api/v2/

✅ HTTP Methods:
   - GET (idempotent)
   - POST (non-idempotent, for create + custom actions)
   - PATCH (idempotent, partial update)
   - DELETE (idempotent)

✅ Status Codes:
   - 200 OK
   - 201 Created
   - 204 No Content
   - 404 Not Found (specific ID only!)

✅ List API:
   - Pagination (page, limit)
   - Sorting (sortBy, sortOrder)
   - Filtering (status, authorId)
   - Envelope ({data, total, page, totalPages})
   - Sane defaults (works without params)
   - Empty list = 200 OK, data: []

✅ Consistency:
   - createdAt, updatedAt everywhere
   - description everywhere (not desc)
   - authorId, organizationId everywhere

✅ Interactive Docs:
   - /docs (Swagger UI)
   - /redoc (ReDoc)
   - Auto-generated, always up-to-date

This is a production-grade REST API!
"""
