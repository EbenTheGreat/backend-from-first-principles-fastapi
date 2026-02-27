# FastAPI Official Documentation - Extracted Content

> **Source**: https://fastapi.tiangolo.com
> **Last Updated**: 2026-01-29

---

## 📚 Documentation Structure

### 1. Tutorial - User Guide
**URL**: https://fastapi.tiangolo.com/tutorial/

This tutorial shows you how to use FastAPI with most of its features, step by step. Each section gradually builds on the previous ones, but it's structured to separate topics, so that you can go directly to any specific one to solve your specific API needs.

### 2. Advanced User Guide
**URL**: https://fastapi.tiangolo.com/advanced/

The main Tutorial should be enough to give you a tour through all the main features of FastAPI. In the next sections you will see other options, configurations, and additional features. The next sections are not necessarily "advanced" - for your use case, the solution might be in one of them.

### 3. Reference
**URL**: https://fastapi.tiangolo.com/reference/

Here's the reference or code API - the classes, functions, parameters, attributes, and all the FastAPI parts you can use in your applications.

---

## 🚀 First Steps

**URL**: https://fastapi.tiangolo.com/tutorial/first-steps/

### The Simplest FastAPI File

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

### Running the Server

```bash
fastapi dev main.py
```

Output shows:
- Server at: http://127.0.0.1:8000
- Documentation at: http://127.0.0.1:8000/docs
- For production: `fastapi run`

### Step-by-Step Breakdown

#### Step 1: Import FastAPI
```python
from fastapi import FastAPI
```
FastAPI is a Python class that provides all the functionality for your API. It inherits directly from Starlette.

#### Step 2: Create a FastAPI "instance"
```python
app = FastAPI()
```
The `app` variable will be an "instance" of the class FastAPI. This is the main point of interaction to create all your API.

#### Step 3: Create a Path Operation
- **Path**: The last part of the URL starting from the first `/` (also called "endpoint" or "route")
- **Operation**: An HTTP method (GET, POST, PUT, DELETE, etc.)

```python
@app.get("/")
```
The `@app.get("/")` decorator tells FastAPI that the function handles requests to path `/` using GET operation.

Other operations:
- `@app.post()`
- `@app.put()`
- `@app.delete()`
- `@app.options()`
- `@app.head()`
- `@app.patch()`
- `@app.trace()`

#### Step 4: Define the Path Operation Function
```python
async def root():
    return {"message": "Hello World"}
```
- Can be `async def` or regular `def`
- Called by FastAPI when it receives a request to the URL "/" using GET

#### Step 5: Return the Content
You can return:
- `dict`
- `list`
- Singular values: `str`, `int`, etc.
- Pydantic models
- Many other objects (automatically converted to JSON)

---

## 🛣️ Path Parameters

**URL**: https://fastapi.tiangolo.com/tutorial/path-params/

### Basic Path Parameters

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(item_id):
    return {"item_id": item_id}
```

The value of `item_id` is passed to your function as the argument `item_id`.

### Path Parameters with Types

```python
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
```

Benefits of type declaration:
- **Editor support**: Error checks, completion
- **Data conversion**: Automatic parsing (string "3" → int 3)
- **Data validation**: Invalid types return clear error messages
- **Documentation**: Auto-generated in Swagger UI

### Order Matters

```python
@app.get("/users/me")
async def read_user_me():
    return {"user_id": "the current user"}

@app.get("/users/{user_id}")
async def read_user(user_id: str):
    return {"user_id": user_id}
```

Put fixed paths before parameterized paths, otherwise `/users/{user_id}` would match `/users/me`.

### Predefined Values with Enum

```python
from enum import Enum
from fastapi import FastAPI

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

app = FastAPI()

@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    if model_name is ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}
    if model_name.value == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}
    return {"model_name": model_name, "message": "Have some residuals"}
```

By inheriting from `str`, the API docs know values must be strings.

---

## ❓ Query Parameters

**URL**: https://fastapi.tiangolo.com/tutorial/query-params/

### Basic Query Parameters

```python
from fastapi import FastAPI

app = FastAPI()

fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]

@app.get("/items/")
async def read_item(skip: int = 0, limit: int = 10):
    return fake_items_db[skip : skip + limit]
```

Query parameters are key-value pairs after `?` in a URL, separated by `&`:
```
http://127.0.0.1:8000/items/?skip=0&limit=10
```

### Defaults

```python
# Default values: skip=0, limit=10
# Going to /items/ is same as /items/?skip=0&limit=10
```

### Optional Parameters

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(item_id: str, q: str | None = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}
```

Setting default to `None` makes the parameter optional.

### Boolean Type Conversion

```python
@app.get("/items/{item_id}")
async def read_item(item_id: str, q: str | None = None, short: bool = False):
    item = {"item_id": item_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update({"description": "This is an amazing item that has a long description"})
    return item
```

All these are treated as `True`:
- `?short=1`
- `?short=True`
- `?short=true`
- `?short=on`
- `?short=yes`

### Multiple Path and Query Parameters

```python
@app.get("/users/{user_id}/items/{item_id}")
async def read_user_item(
    user_id: int, item_id: str, q: str | None = None, short: bool = False
):
    item = {"item_id": item_id, "owner_id": user_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update({"description": "This is an amazing item that has a long description"})
    return item
```

FastAPI knows which is which - they're detected by name.

### Required Query Parameters

```python
@app.get("/items/{item_id}")
async def read_user_item(item_id: str, needy: str):
    item = {"item_id": item_id, "needy": needy}
    return item
```

No default value = required parameter. Missing it returns an error.

### Mixed: Required, Default, Optional

```python
@app.get("/items/{item_id}")
async def read_user_item(
    item_id: str, needy: str, skip: int = 0, limit: int | None = None
):
    item = {"item_id": item_id, "needy": needy, "skip": skip, "limit": limit}
    return item
```

- `needy`: required `str`
- `skip`: `int` with default 0
- `limit`: optional `int`

---

## 📦 Request Body

**URL**: https://fastapi.tiangolo.com/tutorial/body/

A request body is data sent by the client to your API. To declare one, use Pydantic models.

### Import BaseModel

```python
from fastapi import FastAPI
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

app = FastAPI()

@app.post("/items/")
async def create_item(item: Item):
    return item
```

### Data Model Rules

- Attributes with default values are **optional**
- Attributes without defaults are **required**
- Use `None` for optional attributes

Valid JSON:
```json
{
    "name": "Foo",
    "description": "An optional description",
    "price": 45.2,
    "tax": 3.5
}
```

Also valid (optional fields omitted):
```json
{
    "name": "Foo",
    "price": 45.2
}
```

### What FastAPI Does

With just the Python type declaration, FastAPI will:
1. Read the body of the request as JSON
2. Convert the corresponding types (if needed)
3. Validate the data
4. Give you the received data in the parameter
5. Generate JSON Schema definitions
6. Include schemas in OpenAPI/Swagger docs

### Use the Model

```python
@app.post("/items/")
async def create_item(item: Item):
    item_dict = item.model_dump()
    if item.tax is not None:
        price_with_tax = item.price + item.tax
        item_dict.update({"price_with_tax": price_with_tax})
    return item_dict
```

### Request Body + Path Parameters

```python
@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    return {"item_id": item_id, **item.model_dump()}
```

FastAPI recognizes:
- Parameters matching path parameters → taken from the path
- Parameters declared as Pydantic models → taken from request body

---

## 📖 Tutorial Topics Index

### Beginner Topics
1. **First Steps** - Basic FastAPI app structure
2. **Path Parameters** - Dynamic URL routing with `{param}`
3. **Query Parameters** - URL query strings after `?`
4. **Request Body** - Handling POST/PUT data with Pydantic

### Intermediate Topics
5. **Query Parameters and String Validations** - `Query()` constraints
6. **Path Parameters and Numeric Validations** - `Path()` constraints
7. **Body - Multiple Parameters** - Complex requests
8. **Body - Fields** - Pydantic field validation
9. **Body - Nested Models** - Complex data structures
10. **Declare Request Example Data** - OpenAPI examples
11. **Extra Data Types** - UUID, datetime, etc.
12. **Cookie Parameters** - Reading cookies
13. **Header Parameters** - Reading headers
14. **Cookie Parameter Models** - Structured cookies
15. **Header Parameter Models** - Structured headers
16. **Response Model** - Type-safe responses
17. **Extra Models** - Multiple related models
18. **Response Status Code** - HTTP status codes
19. **Form Data** - Handling form submissions
20. **Form Models** - Structured form data
21. **Request Files** - File uploads
22. **Request Forms and Files** - Mixed uploads
23. **Handling Errors** - HTTP exceptions
24. **Path Operation Configuration** - Tags, summary, description
25. **JSON Compatible Encoder** - `jsonable_encoder()`
26. **Body - Updates** - PATCH operations
27. **Dependencies** - Dependency injection
28. **Security** - Authentication & authorization
29. **Middleware** - Request/response processing
30. **CORS** - Cross-origin requests
31. **SQL Databases** - Database integration
32. **Bigger Applications** - Multiple files
33. **Background Tasks** - Async task processing
34. **Metadata and Docs URLs** - Customizing docs
35. **Static Files** - Serving static content
36. **Testing** - Writing tests
37. **Debugging** - Development tips

### Advanced Topics
- Path Operation Advanced Configuration
- Additional Status Codes
- Return a Response Directly
- Custom Response Classes
- Additional Responses in OpenAPI
- Response Cookies
- Response Headers
- Response - Change Status Code
- Advanced Dependencies
- Advanced Security
- Using the Request Directly
- Using Dataclasses
- Advanced Middleware
- Sub Applications - Mounts
- Behind a Proxy
- Templates
- WebSockets
- Lifespan Events
- Testing WebSockets
- Testing Events
- Testing Dependencies
- Async Tests
- Settings and Environment Variables
- OpenAPI Callbacks
- OpenAPI Webhooks
- Including WSGI
- Generate Clients
- Extending OpenAPI

---

## 🔗 Quick Links

- **Official Docs**: https://fastapi.tiangolo.com
- **Tutorial**: https://fastapi.tiangolo.com/tutorial/
- **Advanced**: https://fastapi.tiangolo.com/advanced/
- **Reference**: https://fastapi.tiangolo.com/reference/
- **GitHub**: https://github.com/fastapi/fastapi
- **Pydantic Docs**: https://docs.pydantic.dev/
