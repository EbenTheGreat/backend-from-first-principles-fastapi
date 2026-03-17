"""
Complete Elasticsearch & Full-Text Search Example - FastAPI
Demonstrates all concepts from Lecture 15:

1. Inverted Index
2. Relevance Scoring (BM25)
3. Field Boosting
4. Fuzzy Search (Typo Tolerance)
5. Autocomplete (Type-Ahead)
6. SQL vs Elasticsearch Performance
7. ELK Stack basics
8. Dual-write pattern

Run with: fastapi dev elasticsearch_complete.py
Visit: http://127.0.0.1:8000/docs

Prerequisites:
  # Install packages
  pip install "fastapi[standard]" elasticsearch sqlalchemy

  # Run Elasticsearch with Docker
  docker run -d --name elasticsearch \
    -p 9200:9200 \
    -e "discovery.type=single-node" \
    -e "xpack.security.enabled=false" \
    elasticsearch:8.11.0

  # Verify Elasticsearch is running
  curl http://localhost:9200

NOTE: If you don't have Docker, comment out the Elasticsearch sections
      and just read the code examples.
"""

from fastapi import FastAPI, Query, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from elasticsearch import Elasticsearch, NotFoundError
from sqlalchemy import Column, Integer, String, Text, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional
import time
import json

# ============================================================================
# SETUP
# ============================================================================

# PostgreSQL Database (for comparison)
SQLALCHEMY_DATABASE_URL = "sqlite:///./search_demo.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Elasticsearch Client
# NOTE: Set this to None if you don't have Elasticsearch running
try:
    es = Elasticsearch(
        ["http://localhost:9200"],
        request_timeout=30,
        max_retries=3,
        retry_on_timeout=True
    )
    # Test connection
    es_available = es.ping()
    if es_available:
        print("✅ Elasticsearch connected successfully")
    else:
        print("⚠️  Elasticsearch not available - some features disabled")
        es = None
except Exception as e:
    print(f"⚠️  Elasticsearch connection failed: {e}")
    print("   Some features will be disabled. Run Elasticsearch with Docker to enable.")
    es = None

# ============================================================================
# DATABASE MODELS
# ============================================================================

class ProductModel(Base):
    """Product in PostgreSQL"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), index=True)
    description = Column(Text)
    category = Column(String(100), index=True)
    price = Column(Integer)  # In cents

class ReviewModel(Base):
    """Review in PostgreSQL (for performance comparison)"""
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(200))
    review_text = Column(Text)
    rating = Column(Integer)

Base.metadata.create_all(bind=engine)

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class Product(BaseModel):
    name: str
    description: str
    category: str
    price: int

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    price: int
    
    class Config:
        from_attributes = True

class SearchResult(BaseModel):
    id: int
    name: str
    description: str
    score: float  # Relevance score
    matched_field: Optional[str] = None

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
# ELASTICSEARCH HELPER FUNCTIONS
# ============================================================================

def ensure_index():
    """
    Create Elasticsearch index with proper mappings
    
    Mappings define how fields are analyzed:
    - text: Full-text search (inverted index)
    - keyword: Exact match, aggregations
    """
    if not es:
        return
    
    if not es.indices.exists(index="products"):
        es.indices.create(
            index="products",
            body={
                "mappings": {
                    "properties": {
                        "name": {
                            "type": "text",  # Full-text search
                            "fields": {
                                "keyword": {"type": "keyword"}  # Exact match
                            }
                        },
                        "description": {"type": "text"},
                        "category": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "price": {"type": "integer"}
                    }
                }
            }
        )
        print("✅ Created Elasticsearch 'products' index")

def index_product_in_es(product_id: int, product_dict: dict):
    """
    INDEX a product in Elasticsearch
    
    This is when the INVERTED INDEX is built!
    """
    if not es:
        return
    
    es.index(
        index="products",
        id=product_id,
        document=product_dict
    )

def delete_product_from_es(product_id: int):
    """Delete product from Elasticsearch index"""
    if not es:
        return
    
    try:
        es.delete(index="products", id=product_id)
    except NotFoundError:
        pass

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Elasticsearch & Full-Text Search Complete Example",
    description="All concepts from Lecture 15 with working code",
    version="1.0.0"
)

@app.on_event("startup")
def startup():
    """Initialize Elasticsearch index"""
    ensure_index()

# ============================================================================
# SECTION 1: THE PROBLEM - SQL SEARCH IS SLOW
# ============================================================================

@app.get("/sql/search-slow")
def sql_search_slow(
    query: str = Query(..., description="Search term"),
    db: Session = Depends(get_db)
):
    """
    TRADITIONAL SQL SEARCH - The Problem
    
    Uses LIKE operator with wildcards.
    
    Problems:
    1. FULL TABLE SCAN (checks every row)
    2. No relevance scoring (random order)
    3. No typo tolerance
    4. Slow at scale (50ms → 30s as data grows)
    
    This is the "librarian looking through every book" problem.
    """
    start_time = time.time()
    
    # SQL: %query% means "contains this substring anywhere"
    # This requires scanning EVERY row!
    products = db.query(ProductModel).filter(
        ProductModel.name.ilike(f"%{query}%")  # ilike = case-insensitive LIKE
    ).all()
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    return {
        "method": "SQL LIKE query",
        "query": query,
        "results": [ProductResponse.from_orm(p).dict() for p in products],
        "count": len(products),
        "time_ms": round(elapsed_ms, 2),
        "problems": [
            "Full table scan (checks every row)",
            "No relevance scoring (random order)",
            "Slow at scale (imagine 5 million products)",
            "No typo tolerance"
        ],
        "note": "With 5M products, this could take 30 seconds!"
    }

# ============================================================================
# SECTION 2: INVERTED INDEX - THE SOLUTION
# ============================================================================

@app.post("/products", status_code=201)
def create_product(
    product: Product,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    CREATE PRODUCT - Dual Write Pattern
    
    1. Write to PostgreSQL (source of truth)
    2. Index in Elasticsearch (searchable copy)
    
    When indexing in Elasticsearch, the INVERTED INDEX is built:
    
    Example:
    Product: "MacBook Pro 16-inch laptop"
    
    Inverted Index created:
    "macbook" → [product_id]
    "pro"     → [product_id]
    "16"      → [product_id]
    "inch"    → [product_id]
    "laptop"  → [product_id]
    
    Now searching "laptop" is instant lookup, not table scan!
    """
    # 1. Save to PostgreSQL (source of truth)
    db_product = ProductModel(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    # 2. Index in Elasticsearch (async in background)
    if es:
        background_tasks.add_task(
            index_product_in_es,
            db_product.id,
            product.dict()
        )
    
    return {
        "message": "Product created and indexed",
        "product": ProductResponse.from_orm(db_product),
        "indexing": "Building inverted index in Elasticsearch",
        "inverted_index_example": {
            "term": "Each word → [document IDs]",
            "benefit": "Instant lookup instead of table scan"
        }
    }

# ============================================================================
# SECTION 3: ELASTICSEARCH SEARCH - FAST & SMART
# ============================================================================

@app.get("/elasticsearch/search")
def elasticsearch_search(
    q: str = Query(..., min_length=1, description="Search query")
):
    """
    ELASTICSEARCH FULL-TEXT SEARCH
    
    Uses the INVERTED INDEX for instant results.
    
    Flow:
    1. User searches "laptop"
    2. Elasticsearch looks up "laptop" in inverted index
    3. Finds all document IDs containing "laptop"
    4. Returns results in milliseconds (not seconds!)
    
    Advantages over SQL LIKE:
    - No table scan (direct index lookup)
    - Relevance scoring (BM25 algorithm)
    - Typo tolerance
    - 10-100x faster at scale
    """
    if not es:
        raise HTTPException(
            status_code=503,
            detail="Elasticsearch not available. Start it with Docker."
        )
    
    start_time = time.time()
    
    # Elasticsearch query (JSON DSL)
    query = {
        "query": {
            "multi_match": {
                "query": q,
                "fields": ["name", "description"],
                "fuzziness": "AUTO"  # Typo tolerance!
            }
        }
    }
    
    result = es.search(index="products", body=query)
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    hits = []
    for hit in result['hits']['hits']:
        hits.append({
            "id": hit['_id'],
            "score": hit['_score'],  # Relevance score (BM25)
            "product": hit['_source']
        })
    
    return {
        "method": "Elasticsearch (Inverted Index)",
        "query": q,
        "results": hits,
        "total": result['hits']['total']['value'],
        "time_ms": round(elapsed_ms, 2),
        "advantages": [
            "No table scan (index lookup)",
            "Relevance scored (BM25 algorithm)",
            "Typo tolerance enabled",
            "10-100x faster than SQL at scale"
        ],
        "note": "With 5M products, still returns in ~100-500ms!"
    }

# ============================================================================
# SECTION 4: RELEVANCE SCORING (BM25)
# ============================================================================

@app.get("/elasticsearch/relevance-demo")
def relevance_scoring_demo():
    """
    BM25 RELEVANCE SCORING DEMO
    
    BM25 Algorithm considers:
    1. Term Frequency (TF): How often term appears in document
    2. Document Frequency (DF): How common/rare term is overall
    3. Document Length: Normalizes for size
    
    Example:
    Search: "laptop"
    
    Doc A: Title="MacBook Pro Laptop", body mentions "laptop" 5x
           → High TF, rare in title → Score: 15.3
    
    Doc B: Body mentions "laptop" once in long document
           → Low TF, long doc → Score: 3.2
    
    Doc C: Title="Laptop Bag"
           → High TF in title → Score: 8.1
    
    Results ranked: [A, C, B]  ← Most relevant first!
    """
    if not es:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    # Index sample documents for demo
    docs = [
        {"id": "A", "name": "MacBook Pro Laptop Computer", "description": "Best laptop for developers. This laptop has great performance. Buy this laptop today. Laptop laptop laptop."},
        {"id": "B", "name": "Computer Desk", "description": "A very long description about a desk where you might use a laptop but this is primarily about the desk itself and all its features and benefits and the wood it's made from and the company that makes it."},
        {"id": "C", "name": "Laptop Bag Premium", "description": "Carry your devices safely"}
    ]
    
    for doc in docs:
        es.index(index="demo", id=doc["id"], document=doc)
    
    time.sleep(1)  # Wait for indexing
    
    # Search "laptop"
    result = es.search(
        index="demo",
        body={
            "query": {
                "multi_match": {
                    "query": "laptop",
                    "fields": ["name", "description"]
                }
            }
        }
    )
    
    ranked_results = []
    for hit in result['hits']['hits']:
        ranked_results.append({
            "id": hit['_id'],
            "name": hit['_source']['name'],
            "relevance_score": hit['_score'],
            "explanation": "Higher score = more relevant"
        })
    
    # Cleanup
    es.indices.delete(index="demo")
    
    return {
        "search_term": "laptop",
        "results_ranked_by_relevance": ranked_results,
        "bm25_factors": {
            "term_frequency": "How often 'laptop' appears in document",
            "inverse_document_frequency": "How rare 'laptop' is across all docs",
            "field_length": "Normalizes for document size"
        },
        "note": "Results automatically sorted by relevance score (highest first)"
    }

# ============================================================================
# SECTION 5: FIELD BOOSTING
# ============================================================================

@app.get("/elasticsearch/field-boosting")
def field_boosting_demo(
    q: str = Query("machine learning", description="Search term")
):
    """
    FIELD BOOSTING
    
    Prioritize matches in certain fields.
    
    Configuration:
    - Title match: 3x weight
    - Description match: 2x weight
    - Content match: 1x weight (default)
    
    Example:
    Doc A: "machine learning" in title → Score: 45
    Doc B: "machine learning" in description → Score: 20
    Doc C: "machine learning" in content → Score: 10
    
    Results: [A, B, C]  ← Title matches rank highest!
    """
    if not es:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    query = {
        "query": {
            "multi_match": {
                "query": q,
                "fields": [
                    "name^3",        # Boost title 3x
                    "description^2", # Boost description 2x
                    "category"       # Default weight (1x)
                ],
                "type": "best_fields"
            }
        }
    }
    
    result = es.search(index="products", body=query)
    
    return {
        "search_term": q,
        "field_weights": {
            "name": "3x (highest priority)",
            "description": "2x (medium priority)",
            "category": "1x (default)"
        },
        "results": [
            {
                "name": hit['_source']['name'],
                "score": hit['_score'],
                "note": "Higher score likely means match in title"
            }
            for hit in result['hits']['hits']
        ],
        "benefit": "Most relevant field matches appear first"
    }

# ============================================================================
# SECTION 6: FUZZY SEARCH (TYPO TOLERANCE)
# ============================================================================

@app.get("/elasticsearch/fuzzy")
def fuzzy_search(
    q: str = Query("laptob", description="Search with typo")
):
    """
    FUZZY MATCHING - Typo Tolerance
    
    Uses Levenshtein distance (edit distance).
    
    Examples:
    - "laptob" → finds "laptop" (1 character swap)
    - "machien" → finds "machine" (2 character transposition)
    - "compter" → finds "computer" (1 character missing)
    
    How it works:
    - Calculates edit distance (insertions, deletions, substitutions)
    - Accepts matches within threshold
    - AUTO fuzziness: 0 edits for 1-2 chars, 1 edit for 3-5 chars, 2 edits for 6+ chars
    
    This is why you can typo on Amazon and still get results!
    """
    if not es:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    query = {
        "query": {
            "multi_match": {
                "query": q,
                "fields": ["name", "description"],
                "fuzziness": "AUTO",  # Auto-determines edit distance allowed
                "prefix_length": 0,   # Allow fuzzy from first character
                "max_expansions": 50  # Max terms to match
            }
        }
    }
    
    result = es.search(index="products", body=query)
    
    return {
        "query_with_typo": q,
        "fuzziness": "AUTO (Levenshtein distance)",
        "results": [
            {
                "name": hit['_source']['name'],
                "score": hit['_score'],
                "note": "Found despite typo!"
            }
            for hit in result['hits']['hits']
        ],
        "how_it_works": {
            "algorithm": "Levenshtein distance (edit distance)",
            "auto_fuzziness": "0 edits (1-2 chars), 1 edit (3-5 chars), 2 edits (6+ chars)"
        },
        "examples": [
            "laptob → laptop (1 swap)",
            "machien → machine (transposition)",
            "compter → computer (1 deletion)"
        ]
    }

# ============================================================================
# SECTION 7: AUTOCOMPLETE (TYPE-AHEAD)
# ============================================================================

@app.get("/elasticsearch/autocomplete")
def autocomplete(
    prefix: str = Query(..., min_length=1, description="Prefix to autocomplete")
):
    """
    AUTOCOMPLETE / TYPE-AHEAD
    
    Real-time suggestions as user types.
    
    User types:  "ma"    → Shows: MacBook, Machine Learning
    User types:  "mac"   → Shows: MacBook Pro, MacBook Air
    User types:  "macb"  → Shows: MacBook Pro
    
    How it works:
    - match_phrase_prefix: Matches terms starting with prefix
    - Updates in real-time (< 100ms)
    
    This is what powers:
    - Google search suggestions
    - Amazon product autocomplete
    - Every modern search box
    """
    if not es:
        raise HTTPException(status_code=503, detail="Elasticsearch not available")
    
    query = {
        "query": {
            "match_phrase_prefix": {
                "name": {
                    "query": prefix,
                    "max_expansions": 10  # Max suggestions
                }
            }
        },
        "size": 5  # Top 5 suggestions only
    }
    
    result = es.search(index="products", body=query)
    
    suggestions = [
        hit['_source']['name']
        for hit in result['hits']['hits']
    ]
    
    return {
        "prefix": prefix,
        "suggestions": suggestions,
        "count": len(suggestions),
        "use_case": "Search-as-you-type interface",
        "examples": [
            "Google search suggestions",
            "Amazon product autocomplete",
            "Any modern search box"
        ]
    }

# ============================================================================
# SECTION 8: PERFORMANCE COMPARISON
# ============================================================================

@app.get("/performance/compare")
def performance_comparison(
    query: str = Query("laptop", description="Search term"),
    db: Session = Depends(get_db)
):
    """
    PERFORMANCE COMPARISON: SQL vs Elasticsearch
    
    Your lecture's benchmark (50,000 records):
    - PostgreSQL ILIKE: 3.5-7.5 seconds
    - Elasticsearch: 500 milliseconds
    
    Elasticsearch is 7-15x faster!
    
    At 5 million records:
    - SQL: 30+ seconds (unusable)
    - Elasticsearch: 100-500ms (still fast)
    """
    # 1. SQL Performance
    sql_start = time.time()
    sql_results = db.query(ProductModel).filter(
        ProductModel.name.ilike(f"%{query}%")
    ).limit(10).all()
    sql_time = (time.time() - sql_start) * 1000
    
    # 2. Elasticsearch Performance
    if es:
        es_start = time.time()
        es_result = es.search(
            index="products",
            body={
                "query": {
                    "match": {
                        "name": query
                    }
                },
                "size": 10
            }
        )
        es_time = (time.time() - es_start) * 1000
        speedup = sql_time / es_time if es_time > 0 else 0
    else:
        es_time = None
        speedup = None
    
    return {
        "query": query,
        "sql_performance": {
            "method": "LIKE query",
            "time_ms": round(sql_time, 2),
            "count": len(sql_results),
            "note": "Full table scan - slow at scale"
        },
        "elasticsearch_performance": {
            "method": "Inverted index lookup",
            "time_ms": round(es_time, 2) if es_time else "N/A (ES not running)",
            "speedup": f"{speedup:.1f}x faster" if speedup else "N/A"
        },
        "lecture_benchmark_50k_records": {
            "postgres": "3.5-7.5 seconds",
            "elasticsearch": "500 milliseconds",
            "speedup": "7-15x faster"
        },
        "at_5_million_records": {
            "sql": "30+ seconds (unusable)",
            "elasticsearch": "100-500ms (still fast)"
        }
    }

# ============================================================================
# SECTION 9: ELK STACK BASICS
# ============================================================================

@app.get("/elk/demo")
def elk_stack_demo():
    """
    ELK STACK - Log Management
    
    E - Elasticsearch: Storage & search
    L - Logstash: Data ingestion pipeline
    K - Kibana: Visualization dashboard
    
    Use case: Search billions of logs in milliseconds
    
    Example log search:
    - "Show all ERROR logs from last hour"
    - "Find logs containing 'database timeout'"
    - "Count requests per endpoint"
    
    Why Elasticsearch?
    - Handles massive volume (billions of logs)
    - Sub-second search
    - Aggregations for analytics
    """
    if not es:
        return {
            "note": "ELK stack requires Elasticsearch running",
            "components": {
                "elasticsearch": "Storage & search engine",
                "logstash": "Data ingestion (parse, transform, load)",
                "kibana": "Visualization dashboard"
            }
        }
    
    # Example: Index a log entry
    log_entry = {
        "timestamp": "2024-02-23T10:30:00Z",
        "level": "ERROR",
        "service": "api-gateway",
        "message": "Database connection timeout",
        "request_id": "abc123"
    }
    
    es.index(index="logs", document=log_entry)
    
    # Example: Search logs
    result = es.search(
        index="logs",
        body={
            "query": {
                "match": {
                    "message": "database timeout"
                }
            }
        }
    )
    
    return {
        "elk_stack": {
            "E": "Elasticsearch - Storage & search",
            "L": "Logstash - Data ingestion",
            "K": "Kibana - Visualization"
        },
        "use_case": "Search billions of logs in milliseconds",
        "example_searches": [
            "All ERROR logs from last hour",
            "Logs containing 'timeout'",
            "Requests per endpoint (aggregation)"
        ],
        "sample_log_indexed": log_entry,
        "search_result_count": result['hits']['total']['value']
    }

# ============================================================================
# ROOT & INFO
# ============================================================================

@app.get("/")
def root():
    return {
        "message": "Elasticsearch & Full-Text Search Complete API",
        "documentation": "/docs",
        "elasticsearch_status": "Connected ✅" if es else "Not running ⚠️",
        "sections": {
            "1_sql_problem": "GET /sql/search-slow?query=laptop",
            "2_inverted_index": "POST /products (creates inverted index)",
            "3_elasticsearch": "GET /elasticsearch/search?q=laptop",
            "4_relevance": "GET /elasticsearch/relevance-demo",
            "5_field_boosting": "GET /elasticsearch/field-boosting",
            "6_fuzzy": "GET /elasticsearch/fuzzy?q=laptob",
            "7_autocomplete": "GET /elasticsearch/autocomplete?prefix=mac",
            "8_performance": "GET /performance/compare?query=laptop",
            "9_elk_stack": "GET /elk/demo"
        },
        "key_concepts": {
            "inverted_index": "Term → [Documents] (instant lookup)",
            "bm25": "Relevance scoring (TF × IDF × length)",
            "field_boosting": "Prioritize matches in specific fields",
            "fuzzy_search": "Typo tolerance (Levenshtein distance)",
            "autocomplete": "Type-ahead suggestions",
            "performance": "7-15x faster than SQL at scale"
        },
        "setup_elasticsearch": "docker run -d -p 9200:9200 -e discovery.type=single-node -e xpack.security.enabled=false elasticsearch:8.11.0"
    }

# ============================================================================
# SEED DATA
# ============================================================================

@app.on_event("startup")
def seed_data():
    """Seed database and Elasticsearch with sample products"""
    db = SessionLocal()
    
    # Seed database
    if db.query(ProductModel).count() == 0:
        products = [
            ProductModel(name="MacBook Pro 16-inch", description="Powerful laptop for developers", category="electronics", price=249900),
            ProductModel(name="MacBook Air M2", description="Lightweight laptop for everyday use", category="electronics", price=119900),
            ProductModel(name="iPhone 15 Pro", description="Latest smartphone from Apple", category="electronics", price=99900),
            ProductModel(name="Laptop Bag Premium", description="Carry your laptop safely", category="accessories", price=7999),
            ProductModel(name="Wireless Mouse", description="Ergonomic computer mouse", category="accessories", price=2999),
            ProductModel(name="USB-C Hub", description="Expand your laptop connectivity", category="accessories", price=4999),
            ProductModel(name="Python Programming Book", description="Learn Python for machine learning", category="books", price=3999),
            ProductModel(name="FastAPI Guide", description="Build modern APIs with FastAPI", category="books", price=2999),
        ]
        
        db.add_all(products)
        db.commit()
        
        # Index in Elasticsearch
        if es:
            for product in products:
                db.refresh(product)
                index_product_in_es(product.id, {
                    "name": product.name,
                    "description": product.description,
                    "category": product.category,
                    "price": product.price
                })
            
            print(f"✅ Seeded {len(products)} products in DB and Elasticsearch")
    
    db.close()

# ============================================================================
# TEST COMMANDS
# ============================================================================
"""
SETUP:
  # Install packages
  pip install "fastapi[standard]" elasticsearch sqlalchemy
  
  # Start Elasticsearch with Docker
  docker run -d --name elasticsearch \
    -p 9200:9200 \
    -e "discovery.type=single-node" \
    -e "xpack.security.enabled=false" \
    elasticsearch:8.11.0
  
  # Verify Elasticsearch
  curl http://localhost:9200
  
  # Run FastAPI
  fastapi dev elasticsearch_complete.py
  
  # Open docs
  http://localhost:8000/docs

TEST THE CONCEPTS:

1. SQL vs Elasticsearch Performance:
   curl "http://localhost:8000/performance/compare?query=laptop"
   
2. Fuzzy search (typo tolerance):
   curl "http://localhost:8000/elasticsearch/fuzzy?q=laptob"
   # Finds "laptop" despite typo!

3. Autocomplete:
   curl "http://localhost:8000/elasticsearch/autocomplete?prefix=mac"
   # Real-time suggestions

4. Field boosting:
   curl "http://localhost:8000/elasticsearch/field-boosting?q=laptop"
   # Title matches score higher

5. Relevance scoring demo:
   curl http://localhost:8000/elasticsearch/relevance-demo
   # See BM25 in action

KEY INSIGHTS:

The Inverted Index:
  Traditional: Search through every document for term
  Elasticsearch: Look up term → get documents instantly
  
  Like a book index:
    "Python" → pages [12, 45, 89, 102]
    Instead of reading every page to find "Python"

BM25 Relevance Scoring:
  Not all matches are equal!
  - "laptop" in title > "laptop" in description
  - Rare terms > common terms
  - Results ranked by importance

Fuzzy Search:
  User typos: "laptob", "machien", "compter"
  Elasticsearch: Still finds correct results
  How: Levenshtein distance (edit distance)

Performance:
  50,000 records:
    SQL: 3.5-7.5 seconds
    Elasticsearch: 500 milliseconds
    
  5 million records:
    SQL: 30+ seconds (unusable)
    Elasticsearch: 100-500ms (still fast!)

When to Use:
  ✅ Large-scale text search (millions of documents)
  ✅ Need relevance ranking
  ✅ Type-ahead/autocomplete
  ✅ Typo tolerance
  ✅ Log management (ELK stack)
  
  ❌ Don't use as primary database
  ❌ Don't use for transactional data
  ❌ Don't over-engineer simple queries
"""
