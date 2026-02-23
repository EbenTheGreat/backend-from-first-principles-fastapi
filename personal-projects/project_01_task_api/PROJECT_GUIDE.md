# Project 1: Personal Task API — Complete Build Guide

## 🎯 Use Case: "Daily Task Tracker"

You're building a **personal API to track your daily tasks** — things like:
- "Study FastAPI lecture 12"
- "Buy groceries"  
- "Fix the bug in the login page"

Each task has a title, description, priority, status, and a due date.

---

## 📋 What You'll Practice (Mapped to Your Lectures)

| Concept | Where You Learned It | How You'll Use It Here |
|---------|---------------------|----------------------|
| HTTP Methods (GET, POST, PATCH, DELETE) | `http_complete.py` — Section 1 | CRUD operations on tasks |
| Status Codes (200, 201, 204, 404, 422) | `http_complete.py` — Section 2 | Correct responses for each operation |
| Static Routes | `routing_complete.py` — Section 1 | `GET /tasks`, `POST /tasks` |
| Dynamic Routes (Path Params) | `routing_complete.py` — Section 2 | `GET /tasks/{task_id}` |
| Query Parameters | `routing_complete.py` — Section 3 | `GET /tasks?status=pending&priority=high` |
| Type Validation (Pydantic) | `validations_complete.py` — Section 1 | Task model with correct types |
| Syntactic Validation (Format) | `validations_complete.py` — Section 2 | Title length, description length |
| Semantic Validation (Logic) | `validations_complete.py` — Section 3 | Due date can't be in the past |
| Design-First Workflow | `rest_api_complete.py` — Root endpoint | Plan before you code |
| Sane Defaults | `rest_api_complete.py` — List APIs | Default page=1, limit=10, status=all |
| Custom Actions | `rest_api_complete.py` — publish/archive | `POST /tasks/{id}/complete` |
| Consistent Naming | `rest_api_complete.py` — All schemas | Same field names everywhere |

---

# PHASE 1: DESIGN (Do This on Paper or in Your Head — No Code Yet!)

> ⏱️ Time: 20-30 minutes  
> 🎯 Goal: Know EXACTLY what you're building before touching the keyboard

---

## Step 1: Identify Your Resource

**Think about this:** What is the ONE thing your API manages?

<details>
<summary>💡 Answer (try to think first!)</summary>

Your resource is a **Task**.

In REST API design (Lecture 11), we learned:
- URLs use **plural nouns** → `/tasks` (not `/task`)
- Resources are **things**, not actions

</details>

---

## Step 2: Define What a Task Looks Like

**Think about this:** If you wrote a task on a sticky note, what information would you include?

Write down every field you think a task should have. For each field, think about:
- What **type** is it? (string, integer, boolean, date?)
- Is it **required** or optional?
- Does it have a **default value**?

<details>
<summary>💡 Answer (try first!)</summary>

A Task has these fields:

| Field | Type | Required? | Default | Notes |
|-------|------|-----------|---------|-------|
| `id` | integer | Auto-generated | Auto-increment | Server creates this, not the client |
| `title` | string | ✅ Yes | — | What the task is ("Buy groceries") |
| `description` | string | ❌ No | `null` | Extra details (optional) |
| `status` | string (enum) | ❌ No | `"pending"` | pending, in_progress, completed |
| `priority` | string (enum) | ❌ No | `"medium"` | low, medium, high |
| `dueDate` | date | ❌ No | `null` | When it's due |
| `createdAt` | datetime | Auto-generated | `now()` | When it was created |
| `updatedAt` | datetime | Auto-generated | `now()` | When it was last modified |

**Key decisions from your lectures:**
- `description` not `desc` (Lecture 11: no abbreviations!)
- `createdAt` / `updatedAt` consistent everywhere (Lecture 11: consistency!)
- `status` defaults to `"pending"` (Lecture 11: sane defaults!)
- `priority` defaults to `"medium"` (Lecture 11: sane defaults!)

</details>

---

## Step 3: Design Your Endpoints (Interface Design)

**Think about this:** What operations can a user perform on tasks? For each one, decide:
1. What **HTTP method**? (GET, POST, PATCH, DELETE)
2. What **URL path**?
3. What **status code** on success?
4. What does the **request body** look like (if any)?
5. What does the **response** look like?

<details>
<summary>💡 Answer (try first!)</summary>

### Standard CRUD Endpoints:

| Action | Method | URL | Status Code | Why This Code? |
|--------|--------|-----|------------|----------------|
| List all tasks | `GET` | `/tasks` | `200 OK` | Fetching data, even empty list = 200 |
| Get one task | `GET` | `/tasks/{task_id}` | `200 OK` / `404 Not Found` | 404 only when specific ID not found |
| Create a task | `POST` | `/tasks` | `201 Created` | New resource was created |
| Update a task | `PATCH` | `/tasks/{task_id}` | `200 OK` | Partial update, return updated resource |
| Delete a task | `DELETE` | `/tasks/{task_id}` | `204 No Content` | Success, nothing to return |

### Custom Action:

| Action | Method | URL | Status Code | Why? |
|--------|--------|-----|------------|------|
| Mark as complete | `POST` | `/tasks/{task_id}/complete` | `200 OK` | Custom action (Lecture 11 pattern) |

### Query Parameters for List endpoint:

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `status` | string | `null` (show all) | Filter: `?status=pending` |
| `priority` | string | `null` (show all) | Filter: `?priority=high` |
| `page` | integer | `1` | Pagination |
| `limit` | integer | `10` | Items per page (max 50) |

**Why these decisions?** (from your lectures)
- `PATCH` not `PUT` for updates (Lecture 11: partial updates are preferred for JSON APIs)
- `POST` for custom actions like `/complete` (Lecture 11: POST is open-ended in REST)
- `204` for DELETE, not 200 (Lecture 8: no content to return)
- Empty list → `200` with `[]`, NOT `404` (Lecture 11: critical distinction!)

</details>

---

## Step 4: Design Your Validation Rules

**Think about this:** What could go wrong with user input? What should you reject?

For each field, think about:
- **Type validation**: Is it the right type? (Lecture 9, Section 1)
- **Syntactic validation**: Is the format right? (Lecture 9, Section 2)  
- **Semantic validation**: Does it make sense in reality? (Lecture 9, Section 3)

<details>
<summary>💡 Answer (try first!)</summary>

| Field | Validation Type | Rule | Error Message |
|-------|----------------|------|---------------|
| `title` | Type | Must be string | Automatic (Pydantic) |
| `title` | Syntactic | 1-100 characters | "Title must be 1-100 characters" |
| `description` | Syntactic | Max 500 characters | "Description too long" |
| `status` | Type | Must be one of: pending, in_progress, completed | "Invalid status" |
| `priority` | Type | Must be one of: low, medium, high | "Invalid priority" |
| `dueDate` | Semantic | Cannot be in the past | "Due date cannot be in the past" |

</details>

---

## Step 5: Design Your Response Format

**Think about this:** When you list tasks, should you return just an array `[...]` or an envelope with metadata?

<details>
<summary>💡 Answer</summary>

Use an **envelope** (Lecture 11):

```json
{
  "data": [
    {
      "id": 1,
      "title": "Study FastAPI",
      "description": "Complete lecture 12",
      "status": "pending",
      "priority": "high",
      "dueDate": "2026-02-15",
      "createdAt": "2026-02-12T13:00:00",
      "updatedAt": "2026-02-12T13:00:00"
    }
  ],
  "total": 25,
  "page": 1,
  "totalPages": 3
}
```

For a single task (GET by ID), just return the object directly — no envelope needed.

</details>

---

# ✅ DESIGN CHECKPOINT

Before moving to code, you should be able to answer:
- [ ] What is my resource? → **Task**
- [ ] What fields does it have? → title, description, status, priority, dueDate, etc.
- [ ] What are my endpoints? → 6 endpoints (5 CRUD + 1 custom action)
- [ ] What status codes do I use? → 200, 201, 204, 404
- [ ] What validations do I need? → Length, enum, date logic
- [ ] What does my response look like? → Envelope for lists, plain object for single

**If you can answer all of these → you're ready to code!**

---

# PHASE 2: BUILD — The Skeleton (Start Coding!)

> ⏱️ Time: 30-45 minutes  
> 🎯 Goal: Get the absolute minimum running and visible in the browser
> 📂 File: `project_01_task_api/main.py`

---

## Step 6: Create the App + In-Memory Storage

**Your challenge:** Open a blank `main.py` file and write:
1. Import FastAPI
2. Create the app instance
3. Create a dictionary to store tasks (like `books_db` in your HTTP lecture)
4. Create a counter variable for auto-incrementing IDs

**Concepts used:**
- `http_complete.py` lines 1-65: imports + in-memory database setup

**Hints if stuck:**
- Your HTTP lecture used `books_db = { 1: {"id": 1, "title": "..."}, ... }`
- Start with an empty dict: `tasks_db = {}`
- You need a counter: `task_id_counter = 0`

<details>
<summary>🔑 What it should roughly look like (peek ONLY if stuck)</summary>

```
- Import FastAPI
- Create app = FastAPI(title="...", description="...", version="...")
- Create empty tasks_db dictionary
- Create task_id_counter = 0
```

Don't copy this code. Try to write it yourself from what you remember from `http_complete.py`.

</details>

---

## Step 7: Create Your Pydantic Models

**Your challenge:** Create THREE Pydantic models:
1. `TaskCreate` — what the client sends when creating a task
2. `TaskUpdate` — what the client sends when updating (all fields optional!)
3. `TaskResponse` — what the server sends back

**Concepts used:**
- `validations_complete.py` Section 1: Type validation with Pydantic
- `rest_api_complete.py` lines 160-295: Create/Update/Response pattern

**Think about:**
- Which fields go in `TaskCreate`? (NOT `id`, `createdAt`, `updatedAt` — server generates those!)
- Which fields in `TaskUpdate` are `Optional`? (ALL of them — it's a partial update!)
- Which fields go in `TaskResponse`? (ALL fields, including `id` and timestamps)

**Hints if stuck:**
- Use `Field(...)` for required fields with validation
- Use `Field(None, ...)` for optional fields
- Use `Optional[str]` for fields that might be null
- Use enums for `status` and `priority`

<details>
<summary>🔑 Structure hint (peek ONLY if stuck)</summary>

```
- Create TaskStatus enum: pending, in_progress, completed
- Create TaskPriority enum: low, medium, high

- TaskCreate model:
    - title: required, string, 1-100 chars
    - description: optional, string, max 500 chars
    - priority: optional, defaults to "medium"
    - due_date: optional, date type

- TaskUpdate model:
    - ALL fields from TaskCreate, but ALL are Optional

- TaskResponse model:
    - ALL fields from TaskCreate
    - PLUS: id, status, created_at, updated_at
```

</details>

---

## Step 8: Build Your First Two Endpoints (GET + POST)

**Your challenge:** Build just these two first:
1. `POST /tasks` — Create a task (returns 201)
2. `GET /tasks/{task_id}` — Get a task by ID (returns 200 or 404)

**Concepts used:**
- `http_complete.py` lines 88-135: GET and POST methods
- `routing_complete.py` lines 91-101: Dynamic routes with path parameters

**Think about:**
- How do you generate the `id`? (increment `task_id_counter`)
- How do you add the task to `tasks_db`?
- What happens when the `task_id` doesn't exist in the dict?

**Test it:**
```bash
fastapi dev main.py
```
Then open `http://127.0.0.1:8000/docs` and try creating a task!

<details>
<summary>🔑 Logic hint (peek ONLY if stuck)</summary>

```
POST /tasks:
    1. Increment task_id_counter
    2. Build a task dict from the request data
    3. Add id, status="pending", created_at=now, updated_at=now
    4. Store in tasks_db[new_id]
    5. Return the task with 201 status

GET /tasks/{task_id}:
    1. Look up task_id in tasks_db
    2. If not found → raise HTTPException(404)
    3. If found → return the task
```

</details>

---

## Step 9: Build the List Endpoint with Filtering

**Your challenge:** Build `GET /tasks` with:
- Pagination: `?page=1&limit=10`
- Filtering: `?status=pending&priority=high`
- Return the envelope format: `{data, total, page, totalPages}`

**Concepts used:**
- `rest_api_complete.py` lines 307-389: Complete list API with pagination + filtering
- `routing_complete.py` lines 130-186: Query parameters

**Think about:**
- Start with ALL tasks from `tasks_db`
- Apply filters one by one (if the query param is provided)
- Calculate total BEFORE pagination
- Slice the list for the current page

<details>
<summary>🔑 Logic hint (peek ONLY if stuck)</summary>

```
GET /tasks:
    1. Get all tasks as a list: list(tasks_db.values())
    2. If status filter → keep only tasks with that status 
    3. If priority filter → keep only tasks with that priority
    4. Count total (after filtering, before pagination)
    5. Calculate offset = (page - 1) * limit
    6. Slice the list: tasks[offset : offset + limit]
    7. Calculate total_pages = ceil(total / limit)
    8. Return envelope: {data, total, page, totalPages}
```

</details>

---

## Step 10: Build Update and Delete

**Your challenge:** Build:
1. `PATCH /tasks/{task_id}` — Partial update (returns 200)
2. `DELETE /tasks/{task_id}` — Delete (returns 204)

**Concepts used:**
- `http_complete.py` lines 156-202: PATCH and DELETE methods
- `rest_api_complete.py` lines 451-514: Update and Delete patterns

**Think about (PATCH):**
- How do you update ONLY the fields that were provided?
- Don't forget to update `updated_at`!

**Think about (DELETE):**
- What do you return? (Nothing! 204 = No Content)
- What if the task doesn't exist? (404)

<details>
<summary>🔑 Logic hint (peek ONLY if stuck)</summary>

```
PATCH /tasks/{task_id}:
    1. Find task in tasks_db (404 if not found)
    2. Get only the fields that were sent (exclude_unset=True)
    3. Loop through those fields and update the task dict
    4. Update updated_at = now
    5. Return updated task

DELETE /tasks/{task_id}:
    1. Check task exists (404 if not)
    2. Delete from tasks_db: del tasks_db[task_id]
    3. Return nothing (204)
```

</details>

---

## Step 11: Build the Custom Action

**Your challenge:** Build `POST /tasks/{task_id}/complete`

This changes the task's status to `"completed"`, but ONLY if it's not already completed.

**Concepts used:**
- `rest_api_complete.py` lines 624-675: Custom actions (publish/archive pattern)

**Think about:**
- What if the task is already completed? (Return 400 Bad Request)
- Don't forget to update `updated_at`!

---

## Step 12: Add Validation

**Your challenge:** Add these validations to your Pydantic models:
1. `title` must be 1-100 characters (syntactic)
2. `description` must be max 500 characters (syntactic)
3. `due_date` cannot be in the past (semantic — use `@field_validator`)

**Concepts used:**
- `validations_complete.py` Section 2 (lines 161-264): Syntactic validation with Field()
- `validations_complete.py` Section 3 (lines 325-431): Semantic validation with @field_validator

**Hints if stuck:**
- Use `Field(..., min_length=1, max_length=100)` for title
- For due_date validation, compare with `date.today()`

---

# PHASE 3: TEST & POLISH

> ⏱️ Time: 30-45 minutes  
> 🎯 Goal: Make sure everything works correctly

---

## Step 13: Test Every Endpoint

Run your server and test in the Swagger UI (`/docs`):

```
Test Checklist:
□ POST /tasks — Create 3-4 tasks with different statuses/priorities
□ GET /tasks — See all tasks (should return envelope)
□ GET /tasks?status=pending — Filter works
□ GET /tasks?priority=high — Filter works
□ GET /tasks?page=1&limit=2 — Pagination works
□ GET /tasks/1 — Get specific task
□ GET /tasks/999 — Should return 404
□ PATCH /tasks/1 — Update title only (other fields unchanged)
□ POST /tasks/1/complete — Mark as complete
□ POST /tasks/1/complete — Try again (should fail, already complete)
□ DELETE /tasks/1 — Delete task
□ DELETE /tasks/1 — Try again (should return 404)
□ GET /tasks — Confirm task is gone
□ POST /tasks with title="" — Validation should reject
□ POST /tasks with past due_date — Validation should reject
```

---

## Step 14: Check Your Design Principles

Review against the checklist from Lecture 11:

```
Design Checklist:
□ URLs use plural nouns? (/tasks not /task)
□ Correct HTTP methods? (GET=fetch, POST=create, PATCH=update, DELETE=remove)
□ Correct status codes? (200, 201, 204, 404)
□ List API has envelope? ({data, total, page, totalPages})
□ List API has sane defaults? (works without any query params)
□ Empty list returns 200, not 404?
□ Field names are consistent? (createdAt everywhere, not mixed)
□ No abbreviations? (description, not desc)
□ Custom action uses POST? (/tasks/{id}/complete)
□ Validation gives clear error messages?
```

---

# PHASE 4: STRETCH GOALS (Only After Phases 1-3 Are Done!)

If you finish everything above and want more:

1. **Add sorting** — `?sort_by=created_at&sort_order=desc`
2. **Add a search** — `?search=groceries` (search in title and description)
3. **Add bulk complete** — `POST /tasks/bulk-complete` with a list of IDs
4. **Add statistics** — `GET /tasks/stats` (count by status, by priority)
5. **Add due date filtering** — `?due_before=2026-02-15` or `?overdue=true`

---

# 📚 Quick Reference: Which Lecture File to Look At

| When you're stuck on... | Look at this file | Specific section |
|--------------------------|-------------------|-----------------|
| Imports and app setup | `http_complete.py` | Lines 1-70 |
| HTTP methods (GET/POST/PATCH/DELETE) | `http_complete.py` | Section 1 (lines 70-202) |
| Status codes | `http_complete.py` | Section 2 (lines 207-292) |
| Path parameters (`/tasks/{id}`) | `routing_complete.py` | Section 2 (lines 90-124) |
| Query parameters (`?status=pending`) | `routing_complete.py` | Section 3 (lines 129-186) |
| Pydantic models (BaseModel) | `validations_complete.py` | Section 1 (lines 49-130) |
| Field validation (min_length, max) | `validations_complete.py` | Section 2 (lines 161-264) |
| Custom validators (@field_validator) | `validations_complete.py` | Section 3 (lines 325-431) |
| Enums (status, priority) | `rest_api_complete.py` | Lines 115-124 |
| List API (pagination, filtering) | `rest_api_complete.py` | Lines 307-389 |
| Create/Update/Response models | `rest_api_complete.py` | Lines 160-295 |
| Custom actions (/publish, /archive) | `rest_api_complete.py` | Lines 624-675 |
| PATCH (partial update) | `rest_api_complete.py` | Lines 451-484 |
| DELETE (204 No Content) | `rest_api_complete.py` | Lines 486-514 |

---

# ⏱️ Suggested Time Breakdown

| Phase | What | Time |
|-------|------|------|
| Phase 1 | Design on paper (Steps 1-5) | 20-30 min |
| Phase 2a | Skeleton + first 2 endpoints (Steps 6-8) | 30-45 min |
| Phase 2b | List, Update, Delete, Custom Action (Steps 9-11) | 45-60 min |
| Phase 2c | Validation (Step 12) | 20-30 min |
| Phase 3 | Testing + Design Review (Steps 13-14) | 30-45 min |
| **Total** | | **~3-4 hours** |

**You don't have to do this all in one sitting!** Split it across 2-3 days:
- **Day 1**: Phase 1 (design) + Steps 6-8 (first endpoints running)
- **Day 2**: Steps 9-12 (all endpoints + validation)
- **Day 3**: Phase 3 (testing + polish)

---

# 🧠 The Learning Mindset

Remember:
1. **It's normal to get stuck** — that's learning happening
2. **It's okay to look at your reference files** — but try yourself first for 5 minutes
3. **Run your code often** — after every endpoint, test it in `/docs`
4. **Errors are your teacher** — read the error message, it usually tells you exactly what's wrong
5. **You don't need to memorize** — you need to understand the PATTERN and know where to look

> *"A great developer doesn't memorize code. They understand patterns and know where to find references."*

---

**Ready? Start with Phase 1, Step 1. Open a blank piece of paper (or a new markdown file) and answer: What is your resource?** 🚀
