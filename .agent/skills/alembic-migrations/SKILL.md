---
name: Alembic Migrations
description: A complete reference guide for Alembic database migrations with FastAPI + SQLModel/SQLAlchemy, covering setup, daily workflow, migration file anatomy, common operations, critical gotchas, and startup integration.
---

# Alembic Migrations — The Complete Guide 🗄️

Since you're already building with FastAPI + SQLModel/SQLAlchemy, Alembic is the natural choice for managing database schema changes. Let me break this down properly.

---

## What is Alembic?

Alembic is a **database migration tool** for SQLAlchemy. Think of it like Git, but for your database schema:

- **Git** tracks changes to your *code*
- **Alembic** tracks changes to your *database structure*

Without migrations, if you add a new column to your model, you'd have to manually write `ALTER TABLE` SQL. Alembic generates and manages all of that for you.

---

## Core Concepts

| Concept | What it is |
|---|---|
| **Migration** | A script describing a schema change (up and down) |
| **Revision** | A unique ID for each migration (like a git commit hash) |
| **Head** | The latest migration revision |
| **`alembic_version` table** | Alembic creates this in your DB to track the current revision |
| **`upgrade()`** | Function to apply the change |
| **`downgrade()`** | Function to reverse the change |

---

## Setup

### 1. Install Alembic
```bash
pip install alembic
```

### 2. Initialize Alembic in your project
```bash
alembic init alembic
```

This creates:
```
your-project/
├── alembic/
│   ├── versions/          # ← Your migration scripts live here
│   ├── env.py             # ← The brain of Alembic (configure this)
│   └── script.py.mako     # ← Template for new migrations
├── alembic.ini            # ← Top-level config
└── main.py
```

### 3. Configure `alembic.ini`
```ini
# alembic.ini
sqlalchemy.url = postgresql+psycopg2://user:password@localhost/dbname
```

> **Tip**: You're using `.env` files. Don't hardcode this — override it in `env.py` instead (see below).

### 4. Configure `alembic/env.py`

This is the most important file. You need to point Alembic at your SQLModel metadata:

```python
# alembic/env.py
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Load your .env file
load_dotenv()

# Import your models so Alembic can see them
from models import SQLModel  # or wherever your Base/SQLModel is

config = context.config

# Override the DB URL from environment variable
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

fileConfig(config.config_file_name)

# THIS IS THE KEY LINE — point to your metadata
target_metadata = SQLModel.metadata
```

> **Why `target_metadata`?** This tells Alembic to compare your Python models against the actual database to detect what changed.

---

## Daily Workflow

### The Core Commands

```bash
# 1. Create a new migration (auto-detect changes from your models)
alembic revision --autogenerate -m "add weather_cache table"

# 2. Apply migrations (upgrade to latest)
alembic upgrade head

# 3. Roll back one migration
alembic downgrade -1

# 4. Roll back ALL the way
alembic downgrade base

# 5. See current revision in your DB
alembic current

# 6. See migration history
alembic history --verbose

# 7. Upgrade to a specific revision
alembic upgrade ae1027a6acf
```

---

## What a Migration File Looks Like

When you run `alembic revision --autogenerate -m "add city column"`, Alembic generates:

```python
# alembic/versions/3d1f2a4b5c6e_add_city_column.py

"""add city column

Revision ID: 3d1f2a4b5c6e
Revises: 1a2b3c4d5e6f
Create Date: 2026-04-06 16:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '3d1f2a4b5c6e'
down_revision = '1a2b3c4d5e6f'  # ← previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Alembic generated this automatically from your model change
    op.add_column('weatherhistory', sa.Column('city', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('weatherhistory', 'city')
```

---

## Applied to YOUR Project

Based on your `models.py`, here's exactly how it would work:

**Step 1**: You add a new field to a model
```python
# models.py
class WeatherHistory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    city: str
    temperature: float
    recorded_at: datetime
    feels_like: float | None = None  # ← NEW FIELD you just added
```

**Step 2**: Auto-generate the migration
```bash
alembic revision --autogenerate -m "add feels_like to weatherhistory"
```

Alembic diffs your models vs the DB and writes the migration script automatically.

**Step 3**: Review the generated script (always do this!)

**Step 4**: Apply it
```bash
alembic upgrade head
```

Your DB now has the new `feels_like` column. ✅

---

## Common Operations Reference

```python
# In a migration file — common things you'll write or see:

# Add a column
op.add_column('table_name', sa.Column('col', sa.String(), nullable=True))

# Drop a column
op.drop_column('table_name', 'col')

# Rename a column
op.alter_column('table_name', 'old_name', new_column_name='new_name')

# Create an index
op.create_index('ix_table_col', 'table_name', ['col'])

# Add a foreign key
op.create_foreign_key('fk_name', 'source_table', 'target_table', ['col'], ['id'])

# Create a whole new table
op.create_table('newtable',
    sa.Column('id', sa.Integer(), primary_key=True),
    sa.Column('name', sa.String(), nullable=False),
)

# Drop a table
op.drop_table('old_table')
```

---

## ⚠️ Critical Gotchas

### 1. `--autogenerate` is not magic
It **cannot detect**:
- Changes to column **defaults**
- Changes to **constraints** in some databases
- Data changes (you write data migrations manually)

Always **read the generated file** before running `upgrade`.

### 2. Never edit an applied migration
Once a migration has been applied to any environment (especially production), treat it as **immutable**. Create a new migration instead.

### 3. Nullable columns in production
When adding a column to a large table with existing rows:
```python
# BAD — will fail if table has rows and column is NOT NULL
op.add_column('weatherhistory', sa.Column('city', sa.String(), nullable=False))

# GOOD — add nullable first, backfill data, then add constraint
op.add_column('weatherhistory', sa.Column('city', sa.String(), nullable=True))
# ... later migration to backfill and make NOT NULL
```

### 4. SQLModel specific: import all models
Alembic only detects models it *knows about*. If you have models spread across files, import them all in `env.py`:

```python
# env.py
from models import WeatherHistory, Bookmark, WeatherCache  # import ALL models
```

---

## Running Migrations on Startup (Optional)

Some projects run migrations automatically when the app starts:

```python
# main.py
from alembic.config import Config
from alembic import command

def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()  # run on startup
    yield

app = FastAPI(lifespan=lifespan)
```

> **Caution**: Fine for development/small apps. In production with multiple instances, this can cause race conditions — use a separate deployment step instead.

---

## Quick Reference Card

```
alembic init alembic                    → Setup
alembic revision --autogenerate -m ""  → Create migration
alembic upgrade head                   → Apply all pending
alembic downgrade -1                   → Undo last
alembic current                        → What version is my DB at?
alembic history                        → Show all migrations
```
