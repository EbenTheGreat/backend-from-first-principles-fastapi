---
name: FastAPI Quick Reference
description: A practical quick reference guide for common FastAPI patterns, including routing, Pydantic models, validation, authentication, dependencies, and testing.
---

# FastAPI Quick Reference Guide

## 📁 Additional Resources

This skill includes extracted content from the official FastAPI documentation:

| Resource | Description |
|----------|-------------|
| [resources/official-docs.md](resources/official-docs.md) | Comprehensive guide with First Steps, Path Parameters, Query Parameters, and Request Body |
| [resources/tutorial-index.md](resources/tutorial-index.md) | Complete index of all FastAPI tutorial and advanced topics with direct links |

**Official Documentation Links:**
- Tutorial: https://fastapi.tiangolo.com/tutorial/
- Advanced: https://fastapi.tiangolo.com/advanced/
- Reference: https://fastapi.tiangolo.com/reference/

---

A practical reference for common FastAPI patterns and examples.

---

## 🚀 Basic Setup

### Installation
```bash
pip install "fastapi[standard]"
```

### Minimal App
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World"}
```

### Run Development Server
```bash
fastapi dev main.py
```

### Access Documentation
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

## 🛣️ Routing & HTTP Methods

### Basic Routes
```python
@app.get("/items")          # GET request
def get_items():
    return {"items": []}

@app.post("/items")         # POST request
def create_item():
    return {"created": True}

@app.put("/items/{id}")     # PUT request
def update_item(id: int):
    return {"updated": id}

@app.delete("/items/{id}")  # DELETE request
def delete_item(id: int):
    return {"deleted": id}

@app.patch("/items/{id}")   # PATCH request
def partial_update(id: int):
    return {"patched": id}
```

### Path Parameters
```python
# Simple path parameter
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}

# Multiple path parameters
@app.get("/users/{user_id}/posts/{post_id}")
def get_user_post(user_id: int, post_id: int):
    return {"user_id": user_id, "post_id": post_id}

# Path parameter with enum
from enum import Enum

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

@app.get("/models/{model_name}")
def get_model(model_name: ModelName):
    return {"model": model_name}
```

### Query Parameters
```python
# Optional query parameter
@app.get("/items")
def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

# Required query parameter (no default)
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str):
    return {"item_id": item_id, "q": q}

# Optional query with None
from typing import Union

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}

# Boolean query parameter
@app.get("/items/{item_id}")
def read_item(item_id: int, short: bool = False):
    item = {"item_id": item_id}
    if not short:
        item.update({"description": "Long description"})
    return item
```

---

## 📦 Request Body with Pydantic

### Basic Model
```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.post("/items")
def create_item(item: Item):
    return item
```

### Nested Models
```python
from pydantic import BaseModel

class Image(BaseModel):
    url: str
    name: str

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    images: list[Image] | None = None

@app.post("/items")
def create_item(item: Item):
    return item
```

### Model with Validation
```python
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=300)
    price: float = Field(..., gt=0)
    tax: float | None = Field(None, ge=0, le=100)

@app.post("/items")
def create_item(item: Item):
    return item
```

### Multiple Body Parameters
```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float

class User(BaseModel):
    username: str
    full_name: str | None = None

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item, user: User):
    return {"item_id": item_id, "item": item, "user": user}
```

---

## ✅ Validation

### Query Parameter Validation
```python
from typing import Annotated
from fastapi import Query

@app.get("/items")
def read_items(
    q: Annotated[str | None, Query(
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z]+$"
    )] = None
):
    return {"q": q}
```

### Path Parameter Validation
```python
from typing import Annotated
from fastapi import Path

@app.get("/items/{item_id}")
def read_item(
    item_id: Annotated[int, Path(title="Item ID", ge=1, le=1000)]
):
    return {"item_id": item_id}
```

### Body Field Validation
```python
from pydantic import BaseModel, Field, EmailStr

class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr
    age: int = Field(..., ge=18, le=120)
    full_name: str | None = None

@app.post("/users")
def create_user(user: User):
    return user
```

---

## 📤 Response Models

### Basic Response Model
```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float

class ItemResponse(BaseModel):
    name: str
    price: float
    id: int

@app.post("/items", response_model=ItemResponse)
def create_item(item: Item):
    # This will only return fields in ItemResponse
    return {**item.dict(), "id": 1, "secret": "hidden"}
```

### Response Model with Status Code
```python
from fastapi import status

@app.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(item: Item):
    return item

@app.delete("/items/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(id: int):
    return None
```

### Multiple Response Models
```python
from typing import Union

class BaseUser(BaseModel):
    username: str
    email: str

class UserIn(BaseUser):
    password: str

class UserOut(BaseUser):
    id: int

@app.post("/users", response_model=UserOut)
def create_user(user: UserIn):
    # Password won't be in response
    return {"id": 1, **user.dict()}
```

---

## ⚠️ Error Handling

### Raise HTTP Exceptions
```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
def read_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )
    return items_db[item_id]
```

### Custom Exception Handler
```python
from fastapi import Request
from fastapi.responses import JSONResponse

class CustomException(Exception):
    def __init__(self, name: str):
        self.name = name

@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name} did something."}
    )

@app.get("/custom")
def read_custom():
    raise CustomException(name="Something")
```

---

## 🔐 Security & Authentication

### OAuth2 with Password Flow
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User(BaseModel):
    username: str
    email: str | None = None

def get_current_user(token: str = Depends(oauth2_scheme)):
    # Decode token and get user
    user = fake_decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@app.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Verify credentials
    if form_data.username != "test" or form_data.password != "test":
        raise HTTPException(status_code=400, detail="Incorrect credentials")
    return {"access_token": "fake-token", "token_type": "bearer"}
```

### API Key Security
```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY = "your-secret-api-key"
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    return api_key

@app.get("/secure")
def secure_endpoint(api_key: str = Depends(verify_api_key)):
    return {"message": "Secure data"}
```

---

## 🔗 Dependencies

### Simple Dependency
```python
from fastapi import Depends

def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items")
def read_items(commons: dict = Depends(common_parameters)):
    return commons

@app.get("/users")
def read_users(commons: dict = Depends(common_parameters)):
    return commons
```

### Class as Dependency
```python
class CommonQueryParams:
    def __init__(self, q: str | None = None, skip: int = 0, limit: int = 100):
        self.q = q
        self.skip = skip
        self.limit = limit

@app.get("/items")
def read_items(commons: CommonQueryParams = Depends()):
    return commons
```

### Sub-dependencies
```python
def query_extractor(q: str | None = None):
    return q

def query_or_default(query: str = Depends(query_extractor)):
    if not query:
        return "default"
    return query

@app.get("/items")
def read_items(query: str = Depends(query_or_default)):
    return {"query": query}
```

---

## 📁 Form Data & File Uploads

### Form Data
```python
from fastapi import Form

@app.post("/login")
def login(username: str = Form(), password: str = Form()):
    return {"username": username}
```

### File Upload
```python
from fastapi import File, UploadFile

@app.post("/upload")
async def upload_file(file: UploadFile = File()):
    contents = await file.read()
    return {
        "filename": file.filename,
        "size": len(contents)
    }

@app.post("/uploadfiles")
async def upload_files(files: list[UploadFile] = File()):
    return {
        "filenames": [file.filename for file in files]
    }
```

---

## 🗄️ Database Integration (SQLAlchemy Example)

### Models
```python
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)

Base.metadata.create_all(bind=engine)
```

### Dependency for DB Session
```python
from fastapi import Depends

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users")
def read_users(db = Depends(get_db)):
    users = db.query(User).all()
    return users
```

---

## ⚡ Async Operations

### Async Endpoint
```python
@app.get("/async-items")
async def read_async_items():
    # Await async operations here
    return {"message": "Async response"}
```

### Async with Database
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

async_engine = create_async_engine("sqlite+aiosqlite:///./test.db")
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.get("/async-users")
async def read_async_users(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users
```

---

## 🎯 Background Tasks

```python
from fastapi import BackgroundTasks

def send_email(email: str, message: str):
    # Simulate sending email
    print(f"Sending email to {email}: {message}")

@app.post("/send-notification")
async def send_notification(
    email: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(send_email, email, "Hello!")
    return {"message": "Notification sent in background"}
```

---

## 🧪 Testing

```python
# test_main.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_create_item():
    response = client.post(
        "/items",
        json={"name": "Test", "price": 10.5}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Test"
```

---

## 🌐 CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📚 Additional Resources

- **Official Docs**: https://fastapi.tiangolo.com
- **GitHub**: https://github.com/fastapi/fastapi
- **Tutorial**: https://fastapi.tiangolo.com/tutorial/
- **Advanced Guide**: https://fastapi.tiangolo.com/advanced/

---

**Pro Tip**: Keep this file open while coding and reference it as needed!
