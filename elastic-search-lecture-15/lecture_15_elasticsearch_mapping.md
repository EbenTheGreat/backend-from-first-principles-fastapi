# Lecture 15: Full-Text Search & Elasticsearch - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Full-Text Search & Elasticsearch - Fast, Smart Search at Scale  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Key Concepts from Your Lecture

### **The Problem with Traditional Database Search**

**Traditional SQL Search:**
```sql
SELECT * FROM products WHERE name LIKE '%laptop%';
```

**The "Librarian" Flaw:**
- Database scans EVERY row (full table scan)
- Character-by-character pattern matching
- No concept of "relevance" or "importance"
- Results in random order

**Performance Breakdown:**
```
5,000 products   → 50ms   ✅ Acceptable
50,000 products  → 500ms  ⚠️ Getting slow
500,000 products → 5s     ❌ Terrible UX
5,000,000 products → 30s  💀 Unusable
```

**What's Missing:**
1. Speed at scale
2. Relevance scoring
3. Typo tolerance
4. Type-ahead capability
5. Smart ranking

---

### **The Core Innovation: Inverted Index**

**Traditional Database:**
```
Document 1: "The quick brown fox"
Document 2: "Quick brown dogs"
Document 3: "The lazy cat"

Search "quick" → Scan ALL documents one by one
```

**Inverted Index (Elasticsearch):**
```
Pre-built index:
"the"    → [Doc 1, Doc 3]
"quick"  → [Doc 1, Doc 2]
"brown"  → [Doc 1, Doc 2]
"fox"    → [Doc 1]
"dogs"   → [Doc 2]
"lazy"   → [Doc 3]
"cat"    → [Doc 3]

Search "quick" → Instant lookup in index → [Doc 1, Doc 2]
```

**The Revolution:**
- Instead of searching documents to find terms
- Search terms to find documents
- Pre-processed at indexing time
- Instant retrieval at query time

**Powered by:** Apache Lucene

---

### **Elasticsearch Features**

#### **1. Inverted Index**
- Pre-processes all text when documents are stored
- Maps every term to documents containing it
- Instant lookups (no table scans)

#### **2. Relevance Scoring (BM25 Algorithm)**

Ranks results by importance using:

**Term Frequency (TF)**
- How often the search term appears in a document
- More appearances = higher score

**Document Frequency (DF)**
- How common/rare the term is across all documents
- Rare terms = more significant = higher score

**Document Length**
- Normalizes for document size
- Prevents long documents from dominating

**Formula (simplified):**
```
Score = TF × IDF × length_normalization

Where IDF (Inverse Document Frequency) = 
  log(total_docs / docs_containing_term)
```

#### **3. Field Boosting**

Prioritize specific fields:

```json
{
  "query": {
    "multi_match": {
      "query": "machine learning",
      "fields": [
        "title^3",      // Title matches: 3x weight
        "description^2", // Description: 2x weight
        "content"       // Content: 1x weight (default)
      ]
    }
  }
}
```

**Example:**
- Search: "laptop"
- Doc A: "laptop" in title → Score: 30
- Doc B: "laptop" in description → Score: 10
- Doc A ranks higher!

#### **4. Typo Tolerance**

```
User types: "laptob"
Elasticsearch: Fuzzy matching → finds "laptop"
Returns: Correct results despite typo
```

**How:** Levenshtein distance algorithm (edit distance)

#### **5. Type-Ahead (Autocomplete)**

Real-time search-as-you-type:
```
User types: "ma"     → Shows: MacBook, Machine Learning
User types: "mac"    → Shows: MacBook Pro, Mac Mini
User types: "macb"   → Shows: MacBook Pro, MacBook Air
```

---

### **Performance Comparison (50,000 Records)**

**Your lecture's benchmark:**

| Database | Query | Time |
|----------|-------|------|
| **PostgreSQL** | `ILIKE '%keyword%'` | **3.5-7.5 seconds** |
| **Elasticsearch** | Full-text search | **500 milliseconds** |

**Elasticsearch is 7-15x faster!**

---

### **Real-World Use Cases**

#### **1. E-Commerce Search**
- **Amazon:** Millions of products
- **Need:** Sub-second search with relevance
- **Solution:** Elasticsearch with field boosting

#### **2. Log Management (ELK Stack)**
- **E**lasticsearch: Storage & search
- **L**ogstash: Data ingestion pipeline
- **K**ibana: Visualization dashboard
- **Use:** Search billions of logs in milliseconds

#### **3. Content Platforms**
- **Medium/Wikipedia:** Article search
- **GitHub:** Code search
- **Need:** Smart, relevant results

#### **4. Type-Ahead Interfaces**
- **Google:** Search suggestions
- **Amazon:** Product autocomplete
- **Need:** Real-time updates as user types

---

## 🔗 FastAPI + Elasticsearch Integration

### **Installation**

```bash
# Elasticsearch Python client
pip install elasticsearch

# Run Elasticsearch with Docker
docker run -d \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  elasticsearch:8.11.0
```

---

## 💡 FastAPI Implementation Patterns

### **Pattern 1: Basic Full-Text Search**

```python
from elasticsearch import Elasticsearch
from fastapi import FastAPI, Query

es = Elasticsearch(["http://localhost:9200"])
app = FastAPI()

@app.post("/products/index")
def index_product(product_id: int, name: str, description: str):
    """
    INDEX a product in Elasticsearch
    
    This builds the inverted index
    """
    doc = {
        "name": name,
        "description": description,
        "timestamp": datetime.now()
    }
    
    es.index(index="products", id=product_id, document=doc)
    
    return {"message": "Product indexed", "id": product_id}

@app.get("/products/search")
def search_products(q: str = Query(..., min_length=1)):
    """
    SEARCH products with full-text search
    
    Elasticsearch uses inverted index → instant results
    """
    query = {
        "query": {
            "multi_match": {
                "query": q,
                "fields": ["name^3", "description"],  # Boost name 3x
                "fuzziness": "AUTO"  # Typo tolerance!
            }
        }
    }
    
    result = es.search(index="products", body=query)
    
    hits = []
    for hit in result['hits']['hits']:
        hits.append({
            "id": hit['_id'],
            "score": hit['_score'],  # Relevance score!
            "product": hit['_source']
        })
    
    return {
        "query": q,
        "total": result['hits']['total']['value'],
        "results": hits,
        "took_ms": result['took']  # Search time in ms
    }
```

### **Pattern 2: Field Boosting**

```python
@app.get("/search/boosted")
def search_with_boosting(q: str):
    """
    FIELD BOOSTING
    
    Title matches are 3x more relevant than description
    Description matches are 2x more relevant than content
    """
    query = {
        "query": {
            "multi_match": {
                "query": q,
                "fields": [
                    "title^3",        # 3x weight
                    "description^2",   # 2x weight
                    "content"         # 1x weight (default)
                ],
                "type": "best_fields"
            }
        }
    }
    
    result = es.search(index="documents", body=query)
    
    return {
        "results": [
            {
                "title": hit['_source']['title'],
                "score": hit['_score'],  # Higher score = more relevant
                "matched_field": "Determined by boosting"
            }
            for hit in result['hits']['hits']
        ]
    }
```

### **Pattern 3: Autocomplete (Type-Ahead)**

```python
@app.get("/autocomplete")
def autocomplete(prefix: str = Query(..., min_length=1)):
    """
    TYPE-AHEAD / AUTOCOMPLETE
    
    Real-time suggestions as user types
    Uses edge n-gram tokenizer for prefix matching
    """
    query = {
        "query": {
            "match_phrase_prefix": {
                "name": {
                    "query": prefix,
                    "max_expansions": 10
                }
            }
        },
        "size": 5  # Top 5 suggestions
    }
    
    result = es.search(index="products", body=query)
    
    suggestions = [
        hit['_source']['name']
        for hit in result['hits']['hits']
    ]
    
    return {
        "prefix": prefix,
        "suggestions": suggestions
    }
```

### **Pattern 4: Fuzzy Search (Typo Tolerance)**

```python
@app.get("/search/fuzzy")
def fuzzy_search(q: str):
    """
    FUZZY MATCHING - Typo Tolerance
    
    "laptob" → finds "laptop"
    "machien" → finds "machine"
    
    Uses Levenshtein distance (edit distance)
    """
    query = {
        "query": {
            "match": {
                "name": {
                    "query": q,
                    "fuzziness": "AUTO",  # Auto-determines edit distance
                    "prefix_length": 0,
                    "max_expansions": 50
                }
            }
        }
    }
    
    result = es.search(index="products", body=query)
    
    return {
        "query": q,
        "note": "Results include fuzzy matches (typos)",
        "results": [
            {
                "name": hit['_source']['name'],
                "score": hit['_score']
            }
            for hit in result['hits']['hits']
        ]
    }
```

### **Pattern 5: Aggregations (Analytics)**

```python
@app.get("/analytics/categories")
def category_analytics():
    """
    AGGREGATIONS
    
    Get statistics and counts
    Used in ELK stack for log analysis
    """
    query = {
        "size": 0,  # Don't return documents, just aggregations
        "aggs": {
            "categories": {
                "terms": {
                    "field": "category.keyword",
                    "size": 10
                }
            },
            "avg_price": {
                "avg": {
                    "field": "price"
                }
            }
        }
    }
    
    result = es.search(index="products", body=query)
    
    return {
        "category_counts": result['aggregations']['categories']['buckets'],
        "average_price": result['aggregations']['avg_price']['value']
    }
```

---

## 🎯 When to Use Elasticsearch

### ✅ **USE Elasticsearch When:**

1. **Large-scale text search** (millions of documents)
2. **Relevance matters** (need smart ranking)
3. **Typo tolerance required** (user-facing search)
4. **Type-ahead/autocomplete needed**
5. **Log management** (ELK stack)
6. **Analytics on text data**
7. **Multi-language search**
8. **Faceted search** (filters + search)

### ❌ **DON'T Use Elasticsearch When:**

1. **Simple exact-match queries** (use SQL)
2. **Transactional data** (use relational DB)
3. **Primary data store** (not a replacement for DB!)
4. **Strong consistency required** (eventual consistency model)
5. **Budget constraints** (Elasticsearch needs resources)

---

## 📊 Elasticsearch vs SQL

| Feature | SQL Database | Elasticsearch |
|---------|-------------|---------------|
| **Search Type** | Pattern matching (`LIKE`) | Full-text search |
| **Speed (1M rows)** | 5-30 seconds | 100-500ms |
| **Relevance** | None (random order) | BM25 scoring |
| **Typo Tolerance** | None | Built-in fuzzy matching |
| **Scaling** | Vertical (bigger server) | Horizontal (more nodes) |
| **Use Case** | Structured data, transactions | Unstructured text, logs |
| **Consistency** | Strong (ACID) | Eventual |
| **Primary Storage** | Yes | No (secondary index) |

---

## 🏗️ Architecture Pattern: SQL + Elasticsearch

```
Write Flow:
  User creates product
      ↓
  Save to PostgreSQL (source of truth)
      ↓
  Index in Elasticsearch (searchable copy)
      ↓
  Return success

Search Flow:
  User searches "laptop"
      ↓
  Query Elasticsearch (fast, relevant results)
      ↓
  Get product IDs
      ↓
  Fetch full details from PostgreSQL (if needed)
      ↓
  Return to user

Pattern: Dual-write or async indexing
```

### **Sync Strategies:**

**1. Dual Write (Synchronous)**
```python
def create_product(product: Product, db: Session):
    # 1. Save to database
    db_product = ProductModel(**product.dict())
    db.add(db_product)
    db.commit()
    
    # 2. Index in Elasticsearch
    es.index(
        index="products",
        id=db_product.id,
        document=product.dict()
    )
    
    return db_product
```

**2. Async Indexing (Background Job)**
```python
from fastapi import BackgroundTasks

def create_product(
    product: Product,
    db: Session,
    background_tasks: BackgroundTasks
):
    # 1. Save to database
    db_product = ProductModel(**product.dict())
    db.add(db_product)
    db.commit()
    
    # 2. Schedule indexing in background
    background_tasks.add_task(
        index_in_elasticsearch,
        db_product.id,
        product.dict()
    )
    
    return db_product
```

**3. Change Data Capture (CDC)**
- Database triggers send changes to message queue
- Worker consumes queue and indexes in Elasticsearch
- Most reliable, decoupled

---

## 💭 Key Insights from Your Lecture

### **The 99/1 Rule**

> "Master relational databases (99% of codebase), 
> but have Elasticsearch in your arsenal for the 1%"

**Translation:**
- Your primary database is still SQL
- Elasticsearch is a **specialized tool**
- Use it specifically for search, not as primary storage
- Learn it when needed, don't over-engineer

### **The Inverted Index Analogy**

```
Book Index (back of textbook):
  "Python" → pages 12, 45, 89, 102
  "FastAPI" → pages 67, 78, 95
  "Redis" → pages 34, 56

Instead of reading every page to find "Python",
you flip to the index and immediately know which pages.

Elasticsearch does this for ALL your text data.
```

### **BM25 is the Secret Sauce**

Traditional database:
```
Search "laptop" → returns ALL matches in random order
```

Elasticsearch:
```
Search "laptop" → 
  Doc A: "laptop" in title, mentioned 5 times → Score: 15.3
  Doc B: "laptop" in description once → Score: 3.2
  Doc C: "laptop bag" in title → Score: 8.1
  
Results: [Doc A, Doc C, Doc B]  ← Ranked by relevance!
```

---

## 🎓 Mastery Checklist

- [ ] Explain why `LIKE` is slow at scale?
- [ ] Describe the inverted index concept?
- [ ] Understand BM25 relevance scoring?
- [ ] Implement field boosting?
- [ ] Set up fuzzy search (typo tolerance)?
- [ ] Build autocomplete functionality?
- [ ] Index documents in Elasticsearch?
- [ ] Query Elasticsearch from FastAPI?
- [ ] Know when to use Elasticsearch vs SQL?
- [ ] Understand dual-write pattern?

---

## 📍 Elasticsearch in the Architecture

```
HTTP Request: "Search for laptop"
    ↓
Handler/Controller
    ↓
Service Layer
    ├─ Option 1: Query Elasticsearch directly
    │   └─ Get ranked, scored results
    │   └─ Return to user
    │
    └─ Option 2: Query ES + fetch from DB
        ├─ Query Elasticsearch (get IDs + scores)
        ├─ Fetch full data from PostgreSQL
        └─ Merge and return

Write Flow:
    ↓
Service Layer
    ├─ Write to PostgreSQL (source of truth)
    └─ Index in Elasticsearch (searchable copy)
```

---

## 🔑 Quick Reference: Elasticsearch DSL

```json
// Basic match
{
  "query": {
    "match": {
      "field_name": "search text"
    }
  }
}

// Multi-field with boosting
{
  "query": {
    "multi_match": {
      "query": "search text",
      "fields": ["title^3", "description^2", "content"]
    }
  }
}

// Fuzzy search
{
  "query": {
    "match": {
      "name": {
        "query": "laptob",
        "fuzziness": "AUTO"
      }
    }
  }
}

// Autocomplete
{
  "query": {
    "match_phrase_prefix": {
      "name": {
        "query": "macb",
        "max_expansions": 10
      }
    }
  }
}

// Filtering + search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "description": "laptop" } }
      ],
      "filter": [
        { "range": { "price": { "lte": 1000 } } }
      ]
    }
  }
}
```

---

**Last Updated**: 2026-01-29  
**Status**: ✅ Mapping Complete  
**Practice File**: elasticsearch_complete.py (next)
