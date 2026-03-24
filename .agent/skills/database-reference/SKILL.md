---
name: Database Quick Reference
description: A practical quick reference guide for SQL databases with SQLModel and FastAPI, covering models, sessions, CRUD operations, multiple model patterns, PostgreSQL data types, and connection setup.
---

# Database Quick Reference Guide

> **Last Updated**: 2026-03-24 · **SQLModel**: latest · **Python**: 3.10+ required

## 📚 Source Documentation Links

| Resource | URL |
|----------|-----|
| SQLModel — Intro to Databases | https://sqlmodel.tiangolo.com/databases/ |
| SQLModel — Home & Quick Start | https://sqlmodel.tiangolo.com/ |
| FastAPI — SQL (Relational) Databases | https://fastapi.tiangolo.com/tutorial/sql-databases/ |
| PostgreSQL — Data Types | https://www.postgresql.org/docs/current/datatype.html |
| PostgreSQL — SQL Commands Reference | https://www.postgresql.org/docs/current/sql-commands.html |

---

## 🧠 Core Concepts

### What is a Database?
A database is a system to **store and manage data in a structured and efficient way** — independent of your application code. Unlike variables in memory (which are lost when a program stops), databases **persist data** across restarts.

### Types of Databases
| Type | Description | Examples |
|------|-------------|---------|
| **SQL / Relational** | Structured tables with rows and columns; uses SQL language | PostgreSQL, MySQL, SQLite |
| **NoSQL** | Flexible, non-tabular storage | MongoDB, Redis, DynamoDB |

### SQLModel — Why Use It?
SQLModel is built on top of **SQLAlchemy** and **Pydantic**, created by the same author as FastAPI.
- Combines both libraries with minimal code duplication
- Perfect integration with FastAPI (type hints, validation, schemas all-in-one)
- Supports all SQLAlchemy-compatible databases (PostgreSQL, MySQL, SQLite, Oracle, MSSQL)

---

## 🚀 Installation

```bash
# Install SQLModel (includes SQLAlchemy + Pydantic)
pip install sqlmodel

# For PostgreSQL support
pip install psycopg2-binary   # or asyncpg for async

# For async SQLite (dev/testing)
pip install aiosqlite
```

---

## 🏗️ SQLModel Basics

### Define a Table Model
```python
from sqlmodel import Field, SQLModel

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    age: int | None = Field(default=None, index=True)
    secret_name: str
```
- `table=True` → tells SQLModel this is a **real database table**
- `primary_key=True` → marks the primary key column
- `index=True` → creates a DB index for faster lookups

### Create the Engine
```python
from sqlmodel import create_engine

# SQLite (development)
sqlite_url = "sqlite:///database.db"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

# PostgreSQL (production)
postgres_url = "postgresql://user:password@localhost/dbname"
engine = create_engine(postgres_url)
```

### Create Tables
```python
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
```

---

## 🔗 FastAPI + SQLModel Integration

### Session Dependency (Best Practice)
```python
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session

def get_session():
    with Session(engine) as session:
        yield session

# Reusable type alias — use this in all route parameters
SessionDep = Annotated[Session, Depends(get_session)]
```
> A `Session` stores objects in memory and tracks changes before sending them to the DB via the engine.

### Initialize Tables on Startup
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)
```

---

## 📦 Multiple Models Pattern (Recommended)

This is the **best practice** for production apps — separates concerns between what goes in the DB, what the client sends, and what the API returns.

```python
from sqlmodel import Field, SQLModel

# Base model — shared fields for all variants
class HeroBase(SQLModel):
    name: str = Field(index=True)
    age: int | None = Field(default=None, index=True)

# DB Table model — add DB-only fields here
class Hero(HeroBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    secret_name: str  # stored in DB, never returned to client

# Input model — what the client sends on CREATE
class HeroCreate(HeroBase):
    secret_name: str

# Output model — what the API returns (no secret fields)
class HeroPublic(HeroBase):
    id: int

# Update model — all fields optional for PATCH
class HeroUpdate(SQLModel):
    name: str | None = None
    age: int | None = None
    secret_name: str | None = None
```

---

## ⚡ CRUD Operations

### CREATE
```python
@app.post("/heroes/", response_model=HeroPublic)
def create_hero(hero: HeroCreate, session: SessionDep):
    db_hero = Hero.model_validate(hero)  # converts HeroCreate → Hero
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)   # reload from DB to get the generated id
    return db_hero
```

### READ (All with Pagination)
```python
from sqlmodel import select
from typing import Annotated
from fastapi import Query

@app.get("/heroes/", response_model=list[HeroPublic])
def read_heroes(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    heroes = session.exec(select(Hero).offset(offset).limit(limit)).all()
    return heroes
```

### READ (Single by ID)
```python
@app.get("/heroes/{hero_id}", response_model=HeroPublic)
def read_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero
```

### UPDATE (Partial — PATCH)
```python
@app.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(hero_id: int, hero: HeroUpdate, session: SessionDep):
    hero_db = session.get(Hero, hero_id)
    if not hero_db:
        raise HTTPException(status_code=404, detail="Hero not found")
    hero_data = hero.model_dump(exclude_unset=True)  # only fields sent by client
    hero_db.sqlmodel_update(hero_data)
    session.add(hero_db)
    session.commit()
    session.refresh(hero_db)
    return hero_db
```
> `exclude_unset=True` is the key trick — only updates fields the client explicitly sent.

### DELETE
```python
@app.delete("/heroes/{hero_id}")
def delete_hero(hero_id: int, session: SessionDep):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(hero)
    session.commit()
    return {"ok": True}
```

---

## 🔍 Querying with `select()`

```python
from sqlmodel import select

# Select all
session.exec(select(Hero)).all()

# Filter with WHERE
session.exec(select(Hero).where(Hero.name == "Spider-Man")).first()

# Filter with multiple conditions
session.exec(
    select(Hero).where(Hero.age >= 18, Hero.name.contains("man"))
).all()

# Ordering
session.exec(select(Hero).order_by(Hero.name)).all()

# Offset + Limit (pagination)
session.exec(select(Hero).offset(10).limit(10)).all()

# Count
from sqlmodel import func
count = session.exec(select(func.count()).select_from(Hero)).one()
```

---

## 🐘 PostgreSQL — Key Data Types

| Category | PostgreSQL Type | Python / SQLModel Equivalent |
|----------|----------------|------------------------------|
| **Integer** | `SMALLINT`, `INTEGER`, `BIGINT` | `int` |
| **Decimal** | `NUMERIC(p, s)` | `Decimal` |
| **Float** | `REAL`, `DOUBLE PRECISION` | `float` |
| **Auto-increment** | `SERIAL`, `BIGSERIAL` | `int` (with `primary_key=True`) |
| **Text** | `VARCHAR(n)`, `TEXT` | `str` |
| **Boolean** | `BOOLEAN` | `bool` |
| **Date/Time** | `DATE`, `TIME`, `TIMESTAMP` | `datetime.date`, `datetime.datetime` |
| **UUID** | `UUID` | `uuid.UUID` |
| **JSON** | `JSON`, `JSONB` | `dict` |
| **Array** | `INTEGER[]`, `TEXT[]` | `list` |

### Using PostgreSQL with SQLModel
```python
# Connection string
DATABASE_URL = "postgresql://username:password@localhost:5432/mydb"

# For async PostgreSQL
DATABASE_URL = "postgresql+asyncpg://username:password@localhost:5432/mydb"

# Use environment variables in practice
import os
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./default.db")
```

---

## 🐘 PostgreSQL — Essential SQL Commands

```sql
-- Create a table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert a row
INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');

-- Select with filter
SELECT * FROM users WHERE name LIKE '%Alice%';

-- Update
UPDATE users SET name = 'Bob' WHERE id = 1;

-- Delete
DELETE FROM users WHERE id = 1;

-- Add a column
ALTER TABLE users ADD COLUMN age INTEGER;

-- Create an index
CREATE INDEX idx_users_email ON users(email);

-- Transactions
BEGIN;
    UPDATE accounts SET balance = balance - 100 WHERE id = 1;
    UPDATE accounts SET balance = balance + 100 WHERE id = 2;
COMMIT;
-- or ROLLBACK; to undo
```

---

## 🔒 PostgreSQL — User & Permission Management

```sql
-- Create a role/user
CREATE ROLE myuser WITH LOGIN PASSWORD 'securepassword';

-- Grant privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO myuser;

-- Create a database
CREATE DATABASE myapp OWNER myuser;
```

---

## 🌐 Database Connection Patterns

### SQLite (Development)
```python
sqlite_url = "sqlite:///./database.db"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
```

### PostgreSQL (Production)
```python
import os
from sqlmodel import create_engine

DATABASE_URL = os.environ["DATABASE_URL"]  # set in .env
engine = create_engine(DATABASE_URL)
```

### Async PostgreSQL (with asyncpg)
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async_engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_session():
    async with AsyncSessionLocal() as session:
        yield session
```

---

## 🗂️ Project File Structure

```
myapp/
├── main.py           # FastAPI app + lifespan
├── models.py         # SQLModel table models
├── schemas.py        # Input/output Pydantic models (HeroCreate, HeroPublic, etc.)
├── database.py       # engine, get_session, create_db_and_tables
├── routers/
│   └── heroes.py     # Route handlers
└── .env              # DATABASE_URL and secrets
```

---

## 🚨 Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| Lost data after restart | Using in-memory dict, not DB | Use SQLModel + a real DB |
| Client controls the `id` | Single model for input & DB | Use `HeroCreate` input model without `id` |
| Secret fields leak in responses | Returning DB model directly | Use `HeroPublic` response model |
| PATCH overwrites unset fields | Using `model_dump()` without options | Use `model_dump(exclude_unset=True)` |
| SQLite threading errors | Default SQLite settings | Add `check_same_thread: False` to `connect_args` |

---

## 📚 Additional Resources

- **SQLModel Docs**: https://sqlmodel.tiangolo.com/
- **SQLModel — Intro to Databases**: https://sqlmodel.tiangolo.com/databases/
- **FastAPI — SQL Databases Tutorial**: https://fastapi.tiangolo.com/tutorial/sql-databases/
- **PostgreSQL — Data Types**: https://www.postgresql.org/docs/current/datatype.html
- **PostgreSQL — SQL Commands**: https://www.postgresql.org/docs/current/sql-commands.html
- **FastAPI + PostgreSQL Full Stack Template**: https://github.com/fastapi/full-stack-fastapi-template
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/

---

**Pro Tip**: Always separate your DB model (`table=True`) from your API input/output models. This keeps your API secure and your code clean! 🛡️
