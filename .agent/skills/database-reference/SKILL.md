---
name: Database Quick Reference
description: A practical quick reference guide for SQL databases with SQLModel and FastAPI, covering ORMs, SQL injection prevention, models, sessions, CRUD operations, multiple model patterns, PostgreSQL data types, and connection setup.
---

# Database Quick Reference Guide

> **Last Updated**: 2026-03-24 · **SQLModel**: latest · **Python**: 3.10+ required

## 📚 Source Documentation Links

| Resource | URL |
|----------|-----|
| SQLModel — Intro to Databases | https://sqlmodel.tiangolo.com/databases/ |
| SQLModel — Database to Code (ORMs) | https://sqlmodel.tiangolo.com/databases/ |
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

## 🗺️ ORMs — Database to Code (SQLModel)

> Source: https://sqlmodel.tiangolo.com/databases/

### Why Not Write Raw SQL Strings?

SQL was not designed to be mixed with application code. The simplest approach — putting SQL in a string — has major problems:

```python
# ❌ Problematic: SQL as a plain string
statement = "SELECT * FROM hero;"
results = database.execute(statement)
```

**Problems with raw SQL strings:**
- No editor autocompletion or inline error detection
- The editor sees it as just plain text — typos go unnoticed
- Parameters mixed via string formatting open the door to SQL Injection

---

### 💉 SQL Injection — What It Is & How It Happens

When user-provided values are concatenated directly into SQL strings, attackers can break out of the "data" context into "code" context:

```python
# ❌ NEVER DO THIS — user input in SQL string
user_id = input("Type the user ID: ")
statement = f"SELECT * FROM hero WHERE id = {user_id};"
results = database.execute(statement)
```

**Normal input:** `2` → runs `SELECT * FROM hero WHERE id = 2;` ✅

**Attacker input:** `2; DROP TABLE hero` → runs:
```sql
SELECT * FROM hero WHERE id = 2; DROP TABLE hero;
```
**Result: Entire table deleted! 💥**

---

### 🛡️ How SQLModel Prevents SQL Injection

SQLModel (via SQLAlchemy) **automatically sanitizes** all values — this is called **SQL Sanitization** and it comes built-in.

```python
# ✅ SAFE: SQLModel handles sanitization automatically
user_id = input("Type the user ID: ")

session.exec(
    select(Hero).where(Hero.id == user_id)
).all()
```

**If the attacker sends:** `2; DROP TABLE hero`

SQLModel converts it to a **literal string** and sends this to the database:
```sql
SELECT * FROM hero WHERE id = "2; DROP TABLE hero;";
--                              ^^ notice the quotes — it's DATA, not code!
```

The database finds no record with that ID → **returns empty result, table is never touched.** ✅

---

### 📝 Editor Support with SQLModel

Because SQLModel uses real Python classes, your editor can help you:

```python
# ❌ Raw SQL — editor can't help, typo goes unnoticed
statement = "SELECT * FROM hero WHERE secret_identity = 'Dive Wilson';"

# ✅ SQLModel — editor autocompletes Hero.secret_name, catches typos instantly
session.exec(
    select(Hero).where(Hero.secret_name == "Dive Wilson")
).all()
```

---

### 🧩 What is an ORM?

**ORM = Object-Relational Mapper** — a library that translates between SQL tables and Python classes.

| Term | Meaning |
|------|---------|
| **Object** | Python classes & instances (Object Oriented Programming) |
| **Relational** | SQL databases — also called "Relational Databases" because tables = "relations" |
| **Mapper** | Converts between the two — like a translation function |

```python
# This Python class (Object) ↕ maps to ↕ a SQL table (Relational)
class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    secret_name: str
    age: int | None = None
```

SQLModel is an ORM. Other popular ORMs include SQLAlchemy, Django ORM, Tortoise ORM.

---

### 📋 SQL Table Naming Convention

| Convention | Example | Used By |
|------------|---------|--------|
| SQL standard | `heroes` (plural) | Raw SQL writers |
| SQLModel default | `hero` (singular, derived from class name) | SQLModel |

> SQLModel auto-generates the table name from the class name. You write `class Hero` → table is named `hero`. You can override this in the Advanced User Guide.

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

## 🔗 Connected Tables — Foreign Keys & JOINs

> Source: https://sqlmodel.tiangolo.com/tutorial/connect/create-connected-tables/

The main power of SQL databases is **connecting related data** across tables.

### Relationship Types
| Type | Description | Example |
|------|-------------|---------|
| **One-to-Many** | One team has many heroes | `Team → [Hero, Hero, Hero]` |
| **Many-to-One** | Many heroes belong to one team | `Hero → Team` |
| **Many-to-Many** | Heroes can belong to many teams | Needs a link table |
| **One-to-One** | Each row links to exactly one other row | Rare, special case |

### Foreign Key — Linking Tables
```python
from sqlmodel import Field, SQLModel

class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)
    team_id: int | None = Field(default=None, foreign_key="team.id")
    #                                                       ^^^^^^^^
    #                              "tablename.columnname" — team is the table, id is the column
```

### Create Connected Rows
```python
with Session(engine) as session:
    team_preventers = Team(name="Preventers", headquarters="Sharp Tower")
    team_z_force = Team(name="Z-Force", headquarters="Sister Margaret's Bar")
    session.add(team_preventers)
    session.add(team_z_force)
    session.commit()  # commit teams first to get their IDs

    hero_deadpond = Hero(
        name="Deadpond",
        secret_name="Dive Wilson",
        team_id=team_z_force.id   # link hero to team using the ID
    )
    session.add(hero_deadpond)
    session.commit()
```

### Query with JOIN
```python
from sqlmodel import select

# Read hero AND team data together
statement = select(Hero, Team).where(Hero.team_id == Team.id)
results = session.exec(statement)
for hero, team in results:
    print(f"{hero.name} is on team {team.name}")

# Filter by joined table column
statement = (
    select(Hero)
    .join(Team)
    .where(Team.name == "Preventers")
)
preventers = session.exec(statement).all()
```

---

## 🤝 Relationship Attributes

> Source: https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/define-relationships-attributes/

Relationship attributes let you access related data **like normal Python attributes** — no manual JOINs needed.

### Define Relationships with `Relationship()`
```python
from sqlmodel import Field, Relationship, SQLModel

class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str
    heroes: list["Hero"] = Relationship(back_populates="team")
    #       ^^^^^^^^^^^^    starts empty, SQLModel fills it from DB

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)
    team_id: int | None = Field(default=None, foreign_key="team.id")
    team: Team | None = Relationship(back_populates="heroes")
    #     ^^^^^^^^^^^   single object (not list) — hero belongs to ONE team
```

> `back_populates` keeps both sides of the relationship in sync. When you add a hero to `team.heroes`, the hero's `team` attribute is also automatically updated.

### Access Related Data
```python
with Session(engine) as session:
    hero = session.get(Hero, 1)
    print(hero.team.name)       # Access team from hero — no JOIN needed!

    team = session.get(Team, 1)
    for hero in team.heroes:    # Access all heroes from team — automatic!
        print(hero.name)
```

### Type Annotation Strings (Forward References)
Use string annotations when classes reference each other to avoid import errors:
```python
class Team(SQLModel, table=True):
    heroes: list["Hero"] = Relationship(back_populates="team")
    #            ^^^^^^  — quoted string because Hero is defined AFTER Team
```

---

## 🔄 Many-to-Many Relationships

> Source: https://sqlmodel.tiangolo.com/tutorial/many-to-many/

When **heroes can belong to many teams** AND **teams can have many heroes**, you need a **link table**.

### The Problem with One-to-Many
```
# One-to-Many: Hero has ONE team_id → can only be on ONE team
hero.team_id = 1   # locks hero to a single team

# Many-to-Many: Hero needs to link to MULTIPLE teams dynamically
# → Solution: a separate link table
```

### Create the Link Model
```python
from sqlmodel import Field, Relationship, SQLModel

# Link table — holds pairs of (team_id, hero_id)
# Both columns are PRIMARY KEYS together → prevents duplicate links
class HeroTeamLink(SQLModel, table=True):
    team_id: int | None = Field(default=None, foreign_key="team.id", primary_key=True)
    hero_id: int | None = Field(default=None, foreign_key="hero.id", primary_key=True)

class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str
    heroes: list["Hero"] = Relationship(back_populates="teams", link_model=HeroTeamLink)
    #                                                            ^^^^^^^^^^^^^^^^^^^^^^
    #                                                            point to the link table

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)
    teams: list[Team] = Relationship(back_populates="heroes", link_model=HeroTeamLink)
```

### Create Many-to-Many Data
```python
with Session(engine) as session:
    team_preventers = Team(name="Preventers", headquarters="Sharp Tower")
    team_z_force = Team(name="Z-Force", headquarters="Sister Margaret's Bar")

    # Deadpond is on BOTH teams!
    hero_deadpond = Hero(
        name="Deadpond",
        secret_name="Dive Wilson",
        teams=[team_z_force, team_preventers],  # list of teams
    )
    hero_spider_boy = Hero(
        name="Spider-Boy",
        secret_name="Pedro Parqueador",
        teams=[team_preventers],
    )
    session.add(hero_deadpond)
    session.add(hero_spider_boy)
    session.commit()
```

### Link Model with Extra Fields
Add extra data to the link itself (e.g. when the hero joined the team):
```python
class HeroTeamLink(SQLModel, table=True):
    team_id: int | None = Field(default=None, foreign_key="team.id", primary_key=True)
    hero_id: int | None = Field(default=None, foreign_key="hero.id", primary_key=True)
    is_training: bool = False   # extra field on the link itself!
```

---

## 🔑 Update with Extra Data (Hashed Passwords)

> Source: https://sqlmodel.tiangolo.com/tutorial/fastapi/update-extra-data/

A common pattern: **client sends plain password → you hash it → store only the hash**.

### Model Setup
```python
class HeroBase(SQLModel):
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)

class Hero(HeroBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str = Field()   # DB stores HASH, never plain text

class HeroCreate(HeroBase):
    password: str          # client sends plain text password

class HeroPublic(HeroBase):
    id: int                # response never includes password or hash

class HeroUpdate(SQLModel):
    name: str | None = None
    secret_name: str | None = None
    age: int | None = None
    password: str | None = None    # optional plain password for updates
```

### CREATE with Extra Data (`model_validate` + `update=`)
```python
def hash_password(password: str) -> str:
    return f"hashed_{password}"   # use passlib/bcrypt in production!

@app.post("/heroes/", response_model=HeroPublic)
def create_hero(hero: HeroCreate, session: SessionDep):
    hashed_password = hash_password(hero.password)
    extra_data = {"hashed_password": hashed_password}
    db_hero = Hero.model_validate(hero, update=extra_data)
    #                                   ^^^^^^^^^^^^^^^^
    #                   inject extra fields not in HeroCreate
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero
```

### UPDATE with Extra Data (`sqlmodel_update` + `update=`)
```python
@app.patch("/heroes/{hero_id}", response_model=HeroPublic)
def update_hero(hero_id: int, hero: HeroUpdate, session: SessionDep):
    db_hero = session.get(Hero, hero_id)
    if not db_hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    hero_data = hero.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in hero_data:
        password = hero_data["password"]
        extra_data["hashed_password"] = hash_password(password)
    db_hero.sqlmodel_update(hero_data, update=extra_data)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero
```

---

## 🧪 Testing with FastAPI + SQLModel

> Source: https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/

Use an **in-memory SQLite database** for tests — fast, isolated, no cleanup needed.

### Install Test Dependencies
```bash
pip install pytest httpx
```

### The Key Pattern — Override the DB Session Dependency
```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from .main import app, get_session

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",                              # in-memory, no file!
        connect_args={"check_same_thread": False},
        poolclass=StaticPool                      # share same con across threads
    )
    SQLModel.metadata.create_all(engine)          # create all tables
    with Session(engine) as session:
        yield session                             # give session to each test

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session                            # swap real DB for test DB

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()              # always clean up!
```

### Write Tests Using the Fixtures
```python
# test_heroes.py
def test_create_hero(client: TestClient):
    response = client.post(
        "/heroes/",
        json={"name": "Deadpond", "secret_name": "Dive Wilson"}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == "Deadpond"
    assert data["secret_name"] == "Dive Wilson"
    assert data["age"] is None
    assert data["id"] is not None    # DB assigned an ID

def test_read_hero(client: TestClient, session: Session):
    # Pre-seed test data directly via session
    hero = Hero(name="Spider-Boy", secret_name="Pedro Parqueador")
    session.add(hero)
    session.commit()

    response = client.get(f"/heroes/{hero.id}")
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == "Spider-Boy"

def test_hero_not_found(client: TestClient):
    response = client.get("/heroes/9999")
    assert response.status_code == 404
```

### Run Tests
```bash
pytest                    # run all tests
pytest -v                 # verbose output
pytest tests/test_heroes.py  # specific file
```

---

## 🔢 Advanced Types

### UUID (Universally Unique Identifier)

> Source: https://sqlmodel.tiangolo.com/advanced/uuid/

UUIDs are an alternative to auto-incrementing integers for primary keys.

**Why use UUIDs:**
- Works across **distributed systems** — no central counter needed
- **Prevents information leakage** — attacker can't guess `id=2` after seeing `id=1`
- Globally unique — safe to merge data from multiple databases

```python
import uuid
from sqlmodel import Field, SQLModel

class Hero(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,   # Python generates UUID BEFORE saving
        primary_key=True
    )
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)
```

> **Note:** `default_factory=uuid.uuid4` (no parentheses!) — passes the function itself so SQLModel calls it each time a new instance is created.

```python
# UUID is set immediately when you create the object, before DB commit
hero = Hero(name="Deadpond", secret_name="Dive Wilson")
print(hero.id)  # e.g. 4ff2dab7-bffe-414d-88a5-1826b9fea8df
```

---

### Decimal Numbers

> Source: https://sqlmodel.tiangolo.com/advanced/decimal/

Use `Decimal` instead of `float` when **exact precision matters** (e.g. money, financial data).

| Type | Precision | Use case |
|------|-----------|---------|
| `float` | Approximate (binary floating point) | Scientific calculations |
| `Decimal` | Exact (arbitrary precision) | Money, financial data ✅ |

```python
from decimal import Decimal
from sqlmodel import Field, SQLModel

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    money: Decimal = Field(
        default=0,
        max_digits=5,      # total digits (both sides of decimal point)
        decimal_places=3   # digits after the decimal point
    )
    # max_digits=5, decimal_places=3 means:
    # ✅ valid: 12.345, 12.3, 12, 0.123
    # ❌ invalid: 123.456 (6 total digits), 1.2345 (4 decimal places)
```

```python
# Arithmetic stays precise with Decimal
hero_1.money = Decimal("1.1")
hero_2.money = Decimal("2.2")
total = hero_1.money + hero_2.money
print(total)  # Decimal('3.3') — exact!
# float would give: 3.3000000000000003 ← rounding error
```

---

## 📚 Additional Resources

- **SQLModel Docs**: https://sqlmodel.tiangolo.com/
- **SQLModel — Intro to Databases**: https://sqlmodel.tiangolo.com/databases/
- **SQLModel — Database to Code (ORMs)**: https://sqlmodel.tiangolo.com/databases/
- **SQLModel — Connect Tables (JOINs)**: https://sqlmodel.tiangolo.com/tutorial/connect/
- **SQLModel — Relationship Attributes**: https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/
- **SQLModel — Many-to-Many**: https://sqlmodel.tiangolo.com/tutorial/many-to-many/
- **SQLModel — Testing**: https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/
- **SQLModel — UUID**: https://sqlmodel.tiangolo.com/advanced/uuid/
- **SQLModel — Decimal Numbers**: https://sqlmodel.tiangolo.com/advanced/decimal/
- **FastAPI — SQL Databases Tutorial**: https://fastapi.tiangolo.com/tutorial/sql-databases/
- **PostgreSQL — Data Types**: https://www.postgresql.org/docs/current/datatype.html
- **PostgreSQL — SQL Commands**: https://www.postgresql.org/docs/current/sql-commands.html
- **FastAPI + PostgreSQL Full Stack Template**: https://github.com/fastapi/full-stack-fastapi-template
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/

---

**Pro Tip**: Always separate your DB model (`table=True`) from your API input/output models. This keeps your API secure and your code clean! 🛡️
