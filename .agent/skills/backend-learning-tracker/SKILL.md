---
name: Backend Learning Tracker
description: Track and map backend development learning from YouTube courses to FastAPI documentation, with progress tracking and mastery criteria.
---

# Backend Learning Tracker - Course to FastAPI Mapping

## 🎯 Learning Strategy Overview

**Goal**: Master backend development by mapping YouTube course concepts to FastAPI documentation and practicing until mastery.

**Workflow**:
1. Watch lecture in YouTube series
2. Query NotebookLM for lecture notes
3. Map concepts to FastAPI docs
4. Practice implementation
5. Mark as mastered

---

## 📚 FastAPI Documentation Structure

### Core Tutorial Sections (Beginner → Intermediate)
1. **First Steps** - Basic FastAPI app structure
2. **Path Parameters** - Dynamic URL routing
3. **Query Parameters** - URL query strings
4. **Request Body** - Handling POST/PUT data
5. **Query/Path Validations** - Input validation
6. **Query/Path Parameter Models** - Structured params
7. **Body - Multiple Parameters** - Complex requests
8. **Body - Nested Models** - Complex data structures
9. **Response Models** - Type-safe responses
10. **Form Data & Files** - Handling uploads
11. **Handling Errors** - HTTP exceptions
12. **Dependencies** - Dependency injection system
13. **Security** - Authentication & authorization
14. **Middleware** - Request/response processing
15. **CORS** - Cross-origin requests
16. **SQL Databases** - Database integration
17. **Background Tasks** - Async task processing
18. **Testing** - Writing tests for APIs

### Advanced Topics
- Advanced Dependencies
- OAuth2 with JWT
- WebSockets
- Custom responses
- Advanced middleware
- Settings management

---

## 📝 Lecture Mapping Template

For each lecture, use this template:

```markdown
### Lecture [NUMBER]: [LECTURE TITLE]

**Date Completed**: YYYY-MM-DD
**Status**: 🔴 Not Started | 🟡 In Progress | 🟢 Mastered

#### Key Concepts from Lecture
- Concept 1
- Concept 2
- Concept 3

#### Mapped FastAPI Documentation
- [FastAPI Doc Section](URL)
- [Related Topic](URL)

#### Practice Exercises Completed
- [ ] Exercise 1: [Description]
- [ ] Exercise 2: [Description]
- [ ] Exercise 3: [Description]

#### Code Examples
```python
# Your practice code here
```

#### Notes & Insights
- Personal notes
- Gotchas
- Best practices learned

#### Questions for Further Exploration
- Question 1?
- Question 2?

---
```

---

## 🗺️ Example Mapping: Common Backend Topics → FastAPI

| Backend Concept | FastAPI Tutorial Section | Advanced Topics |
|-----------------|--------------------------|-----------------|
| **HTTP Methods (GET, POST, PUT, DELETE)** | First Steps, Path Operations | Path Operation Advanced Config |
| **Routing & URL Patterns** | Path Parameters, Query Parameters | Advanced routing, Sub-applications |
| **Request/Response Cycle** | Request Body, Response Model | Using Request Directly, Custom Response |
| **Data Validation** | Pydantic models, Query/Path Validations | Extra Data Types, Custom Validators |
| **Authentication & Authorization** | Security (OAuth2, JWT) | Advanced Security, OAuth2 Scopes |
| **Database Operations (CRUD)** | SQL Databases | Async databases, Multiple databases |
| **Error Handling** | Handling Errors | Custom Exception Handlers |
| **Middleware** | Middleware | Advanced Middleware |
| **File Uploads** | Request Files | Streaming responses, Large files |
| **Background Jobs** | Background Tasks | Async tasks, Task queues |
| **API Documentation** | Auto-generated (Swagger/ReDoc) | Extending OpenAPI |
| **Testing** | Testing | Async Tests, Testing Dependencies |
| **Deployment** | Deployment section | Docker, Cloud providers |
| **WebSockets** | WebSockets | Testing WebSockets |
| **CORS & Security Headers** | CORS | Advanced Security |

---

## 📊 Progress Tracking

### Current Progress
- **Total Lectures**: [Fill in from NotebookLM]
- **Completed**: 0
- **In Progress**: 0
- **Mastered**: 0

### Lecture Checklist

#### Module 1: [Module Name]
- [ ] Lecture 1: [Title]
- [ ] Lecture 2: [Title]
- [ ] Lecture 3: [Title]

#### Module 2: [Module Name]
- [ ] Lecture 4: [Title]
- [ ] Lecture 5: [Title]

---

## 🎓 Mastery Criteria

Before marking a topic as "Mastered", ensure you can:

✅ **Understand**: Explain the concept in your own words
✅ **Implement**: Write code from scratch without references
✅ **Debug**: Identify and fix common errors
✅ **Extend**: Modify and enhance the implementation
✅ **Test**: Write tests for the functionality

---

## 🔧 Quick Reference: FastAPI Core Patterns

### Basic API Structure
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

### Path Parameters
```python
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
```

### Query Parameters
```python
@app.get("/items/")
def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

### Request Body with Pydantic
```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float

@app.post("/items/")
def create_item(item: Item):
    return item
```

### Async Operations
```python
@app.get("/async-items/")
async def read_async_items():
    return {"message": "Async response"}
```

---

## 📖 Learning Resources

### FastAPI Official Docs
- Main: https://fastapi.tiangolo.com
- Tutorial: https://fastapi.tiangolo.com/tutorial/
- Advanced: https://fastapi.tiangolo.com/advanced/

### Practice Projects Ideas
1. **Todo API** - Basic CRUD operations
2. **Blog API** - Posts, comments, users
3. **E-commerce API** - Products, orders, cart
4. **Social Media API** - Posts, likes, follows
5. **File Management API** - Upload, download, organize

---

## 💡 Tips for Effective Learning

1. **Code Along**: Don't just read - type out the examples
2. **Modify & Break**: Change parameters, see what breaks
3. **Build Projects**: Apply concepts to real projects
4. **Review Regularly**: Revisit previous topics
5. **Ask Questions**: Use NotebookLM to query your notes
6. **Document Learning**: Keep this tracker updated

---

## 🎯 Next Steps

1. Query your NotebookLM to list all lectures
2. Fill in the lecture checklist above
3. Start with Lecture 1
4. Map concepts to FastAPI docs
5. Practice, practice, practice!
6. Mark as mastered when confident
7. Move to next lecture

---

## 📅 Study Schedule Template

| Day | Lecture | FastAPI Topics | Practice Time | Status |
|-----|---------|----------------|---------------|--------|
| Mon | Lecture 1 | First Steps, Path Params | 2 hours | |
| Tue | Lecture 1 (cont.) | Query Params | 2 hours | |
| Wed | Lecture 2 | Request Body | 2 hours | |
| Thu | Review & Practice | Mixed exercises | 2 hours | |
| Fri | Lecture 3 | Validation | 2 hours | |
| Sat | Project Work | Build mini-project | 3 hours | |
| Sun | Review & Test | Write tests | 2 hours | |

---

**Last Updated**: [Date]
**Current Focus**: [Current Lecture/Topic]
