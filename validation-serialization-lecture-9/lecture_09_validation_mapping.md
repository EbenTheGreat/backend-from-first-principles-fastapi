# Lecture 9: Validations & Transformations - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Validations & Transformations - The Backend Gatekeeper  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Key Concepts from Your Lecture

### 1. **Architectural Placement**
**The Pipeline:**
```
1. Controller Layer (HTTP handling)
2. Validation & Transformation Pipeline ← THE GATEKEEPER
3. Service Layer (Business logic)
4. Repository Layer (Database)
```

**Why at Entry Point:**
- Prevents "unexpected state" in application
- Stops bad data before it reaches database
- Returns 400 (client error) instead of 500 (server crash)

### 2. **Four Categories of Validation**

**Type Validation**
- Ensures data matches expected type (String, Number, Boolean, Array)
- Example: Reject number when string expected

**Syntactic Validation (Structure)**
- Checks if data follows specific format/pattern
- Example: Email format (user@domain.com), Date format (YYYY-MM-DD)

**Semantic Validation (Meaning)**
- Checks if data makes sense in real-world context
- Example: Date of Birth cannot be in future, Age must be 1-120

**Complex/Conditional Validation**
- Logic spanning multiple fields
- Example: Password == Password Confirmation
- Example: If Married=true, then Partner Name required

### 3. **Transformations (Sanitization & Casting)**

**Type Casting**
- Query params always arrive as strings
- Must transform "2" → 2 before validation
- Example: ?page=2 (string) → page=2 (int)

**Normalization**
- Modify data for consistency
- Example: User@Gmail.com → user@gmail.com (lowercase)
- Example: 1234567890 → +1-1234567890 (phone formatting)

### 4. **Frontend vs Backend Validation**

**Frontend Validation:**
- Purpose: User Experience (UX)
- Provides immediate feedback
- Can be bypassed (Postman, Insomnia)

**Backend Validation:**
- Purpose: Security & Data Integrity
- Cannot trust client
- Must validate as if frontend doesn't exist
- **RULE**: Design APIs assuming frontend validation is bypassed

### 5. **Backend Architecture Layers**

**Middleware:**
- Broad, high-level validations
- CORS, Authentication, Rate limiting
- Applies to all/groups of requests

**Handler/Controller:**
- Specific endpoint validations
- Step 1: Binding (Deserialization)
- Step 2: Validation
- Step 3: Transformation
- Then calls Service layer

**Service Layer:**
- Receives clean, validated data
- Focuses on business logic
- Assumes data is already safe

**Repository Layer:**
- Receives transformed data
- Constructs database queries
- Returns raw results

**Request Context:**
- Shared state between layers
- Stores trusted data (User ID from auth)
- Prevents spoofing

---

## 🔗 FastAPI Documentation Mapping

| Your Lecture Concept | FastAPI Feature | Docs URL |
|---------------------|----------------|----------|
| **Type Validation** | Pydantic type hints | https://fastapi.tiangolo.com/tutorial/body/ |
| **Syntactic Validation** | Field validators, regex | https://fastapi.tiangolo.com/tutorial/body-fields/ |
| **Semantic Validation** | Custom validators | https://fastapi.tiangolo.com/tutorial/body-fields/ |
| **Query Parameter Validation** | Query with constraints | https://fastapi.tiangolo.com/tutorial/query-params-str-validations/ |
| **Path Parameter Validation** | Path with constraints | https://fastapi.tiangolo.com/tutorial/path-params-numeric-validations/ |
| **Transformations** | Pydantic validators | https://docs.pydantic.dev/latest/usage/validators/ |
| **Request Models** | Body - Nested Models | https://fastapi.tiangolo.com/tutorial/body-nested-models/ |
| **Response Models** | Response Model | https://fastapi.tiangolo.com/tutorial/response-model/ |

---

## 💡 FastAPI's Approach: Pydantic Does It All!

### The Magic of Pydantic

FastAPI uses **Pydantic** which handles:
1. **Type Validation** - Automatic
2. **Syntactic Validation** - Via Field constraints
3. **Semantic Validation** - Via custom validators
4. **Transformations** - Automatic type coercion + custom logic

**Key Advantage:**
- Define schema once
- Get validation, transformation, serialization automatically
- Returns 422 with detailed errors (not 400, but similar purpose)

---

## 🏗️ FastAPI Implementation Examples

### PART 1: TYPE VALIDATION (Automatic)

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

class Book(BaseModel):
    """
    TYPE VALIDATION - Automatic with Pydantic
    
    Pydantic automatically validates types:
    - title: Must be string
    - year: Must be integer
    - price: Must be float
    - tags: Must be list of strings
    - available: Must be boolean
    """
    title: str          # Type validation: must be string
    year: int           # Type validation: must be integer
    price: float        # Type validation: must be number
    tags: List[str]     # Type validation: must be array of strings
    available: bool     # Type validation: must be boolean

@app.post("/books/type-validation")
def create_book(book: Book):
    """
    Automatic Type Validation Demo
    
    Valid Request:
    {
      "title": "1984",
      "year": 1949,
      "price": 12.99,
      "tags": ["dystopian", "classic"],
      "available": true
    }
    
    Invalid Requests (will return 422):
    
    1. Wrong type for title:
       {"title": 123, ...}
       → "str type expected"
    
    2. Wrong type for year:
       {"year": "1949", ...}
       → Actually works! Pydantic coerces "1949" → 1949
    
    3. Wrong type for tags:
       {"tags": "dystopian", ...}
       → "value is not a valid list"
    
    4. Wrong type for available:
       {"available": "yes", ...}
       → "value could not be parsed to a boolean"
    """
    return {
        "message": "Book validated and created",
        "book": book,
        "validation_passed": "All types correct!"
    }

# Test different type errors
@app.post("/books/type-errors-demo")
def type_errors_demo(data: dict):
    """
    This endpoint accepts ANY dict to show you what errors look like
    
    Try sending:
    {"title": 123}  # Number instead of string
    {"year": [1, 2, 3]}  # Array instead of number
    {"price": "expensive"}  # String instead of number
    
    The 422 error will tell you exactly what's wrong!
    """
    try:
        book = Book(**data)
        return {"success": True, "book": book}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### PART 2: SYNTACTIC VALIDATION (Structure/Format)

```python
from pydantic import BaseModel, EmailStr, field_validator, HttpUrl
from typing import Optional
import re

class User(BaseModel):
    """
    SYNTACTIC VALIDATION - Format/Structure checks
    
    These validate that data follows specific patterns:
    - Email format: user@domain.com
    - URL format: https://example.com
    - Phone format: +1-234-567-8900
    - Date format: YYYY-MM-DD
    """
    
    # Email - built-in EmailStr validator
    email: EmailStr  # Automatically validates email format
    
    # URL - built-in HttpUrl validator
    website: Optional[HttpUrl] = None
    
    # Phone - custom pattern validation
    phone: str
    
    # Username - custom pattern validation
    username: str
    
    # Password - custom pattern validation
    password: str
    
    @field_validator('phone')
    @classmethod
    def validate_phone_format(cls, v):
        """
        Syntactic validation: Phone number format
        
        Accepts: +1-234-567-8900 or (234) 567-8900
        Rejects: 1234567890 or abc-def-ghij
        """
        # Pattern: +X-XXX-XXX-XXXX
        pattern = r'^\+\d{1,3}-\d{3}-\d{3}-\d{4}$'
        if not re.match(pattern, v):
            raise ValueError('Phone must be in format: +1-234-567-8900')
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username_format(cls, v):
        """
        Syntactic validation: Username format
        
        Rules:
        - Only alphanumeric and underscores
        - 3-20 characters
        - No spaces
        """
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', v):
            raise ValueError(
                'Username must be 3-20 characters, '
                'alphanumeric and underscores only'
            )
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password_format(cls, v):
        """
        Syntactic validation: Password strength
        
        Rules:
        - At least 8 characters
        - At least one uppercase
        - At least one lowercase  
        - At least one digit
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain special character')
        return v

@app.post("/users/syntactic-validation")
def create_user_syntactic(user: User):
    """
    Syntactic Validation Demo
    
    Valid Request:
    {
      "email": "user@example.com",
      "website": "https://example.com",
      "phone": "+1-234-567-8900",
      "username": "john_doe",
      "password": "SecurePass123!"
    }
    
    Invalid Requests (422 errors):
    
    1. Bad email:
       {"email": "not-an-email"}
       → "value is not a valid email address"
    
    2. Bad phone:
       {"phone": "1234567890"}
       → "Phone must be in format: +1-234-567-8900"
    
    3. Bad username:
       {"username": "ab"}
       → "Username must be 3-20 characters..."
    
    4. Weak password:
       {"password": "weak"}
       → "Password must be at least 8 characters"
    """
    return {
        "message": "User validated",
        "user": user,
        "validation_passed": "All formats correct!"
    }
```

### PART 3: SEMANTIC VALIDATION (Meaning/Logic)

```python
from datetime import date, datetime
from pydantic import BaseModel, field_validator

class Person(BaseModel):
    """
    SEMANTIC VALIDATION - Real-world meaning checks
    
    Even if syntax is correct, data must make sense:
    - Age must be realistic (1-120)
    - Date of birth cannot be in future
    - End date must be after start date
    - Discount cannot exceed 100%
    """
    name: str
    date_of_birth: date
    age: int
    height_cm: float
    discount_percent: float
    
    @field_validator('age')
    @classmethod
    def validate_age_realistic(cls, v):
        """
        Semantic validation: Age must be realistic
        
        Rejects: 430, -5, 0
        Accepts: 25, 80, 120
        """
        if v < 1:
            raise ValueError('Age must be at least 1')
        if v > 120:
            raise ValueError('Age cannot exceed 120 (not realistic)')
        return v
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_dob_not_future(cls, v):
        """
        Semantic validation: Date of birth cannot be in future
        
        This is logically impossible!
        """
        if v > date.today():
            raise ValueError('Date of birth cannot be in the future')
        return v
    
    @field_validator('height_cm')
    @classmethod
    def validate_height_realistic(cls, v):
        """
        Semantic validation: Height must be realistic
        
        Human height range: ~50cm (baby) to ~272cm (tallest recorded)
        """
        if v < 30:
            raise ValueError('Height too small (minimum 30cm)')
        if v > 300:
            raise ValueError('Height too large (maximum 300cm)')
        return v
    
    @field_validator('discount_percent')
    @classmethod
    def validate_discount_range(cls, v):
        """
        Semantic validation: Discount percentage must be valid
        
        Cannot be negative or exceed 100%
        """
        if v < 0:
            raise ValueError('Discount cannot be negative')
        if v > 100:
            raise ValueError('Discount cannot exceed 100%')
        return v

class DateRange(BaseModel):
    """Semantic validation: Date ranges"""
    start_date: date
    end_date: date
    
    @field_validator('end_date')
    @classmethod
    def validate_end_after_start(cls, v, info):
        """
        Semantic validation: End date must be after start date
        
        This is a real-world logical constraint
        """
        start_date = info.data.get('start_date')
        if start_date and v < start_date:
            raise ValueError('End date must be after start date')
        return v

@app.post("/person/semantic-validation")
def create_person(person: Person):
    """
    Semantic Validation Demo
    
    Valid Request:
    {
      "name": "John",
      "date_of_birth": "1990-01-01",
      "age": 34,
      "height_cm": 175.5,
      "discount_percent": 15.0
    }
    
    Invalid Requests (422 errors):
    
    1. Future birth date:
       {"date_of_birth": "2030-01-01"}
       → "Date of birth cannot be in the future"
    
    2. Unrealistic age:
       {"age": 430}
       → "Age cannot exceed 120"
    
    3. Invalid height:
       {"height_cm": 500}
       → "Height too large"
    
    4. Invalid discount:
       {"discount_percent": 150}
       → "Discount cannot exceed 100%"
    """
    return {
        "message": "Person validated",
        "person": person,
        "validation_passed": "All values make real-world sense!"
    }
```

### PART 4: COMPLEX/CONDITIONAL VALIDATION

```python
from pydantic import BaseModel, field_validator, model_validator

class PasswordReset(BaseModel):
    """
    COMPLEX VALIDATION - Multiple field logic
    
    Password and password_confirmation must match
    """
    password: str
    password_confirmation: str
    
    @model_validator(mode='after')
    def validate_passwords_match(self):
        """
        Complex validation: Compare two fields
        
        This validates AFTER all fields are processed
        """
        if self.password != self.password_confirmation:
            raise ValueError('Passwords do not match')
        return self

class PersonalInfo(BaseModel):
    """
    CONDITIONAL VALIDATION - Fields required based on other fields
    
    If married=True, then partner_name is required
    If has_children=True, then number_of_children is required
    """
    name: str
    married: bool
    partner_name: Optional[str] = None
    has_children: bool = False
    number_of_children: Optional[int] = None
    
    @model_validator(mode='after')
    def validate_conditional_fields(self):
        """
        Conditional validation: Field requirements based on other fields
        
        Business rules:
        - If married, must provide partner name
        - If has children, must provide number
        """
        if self.married and not self.partner_name:
            raise ValueError('Partner name required when married')
        
        if self.has_children and self.number_of_children is None:
            raise ValueError('Number of children required when has_children=True')
        
        if not self.has_children and self.number_of_children:
            raise ValueError('Cannot have children count when has_children=False')
        
        return self

class BookingRequest(BaseModel):
    """
    Complex validation: Multiple business rules
    """
    check_in: date
    check_out: date
    guests: int
    children: int = 0
    
    @field_validator('guests')
    @classmethod
    def validate_guests_count(cls, v):
        """Guests must be reasonable"""
        if v < 1:
            raise ValueError('At least 1 guest required')
        if v > 10:
            raise ValueError('Maximum 10 guests allowed')
        return v
    
    @model_validator(mode='after')
    def validate_booking_logic(self):
        """
        Complex business rules:
        1. Check-out must be after check-in
        2. Total people (guests + children) cannot exceed 10
        3. Minimum 1 night stay
        """
        # Rule 1: Date logic
        if self.check_out <= self.check_in:
            raise ValueError('Check-out must be after check-in')
        
        # Rule 2: Total capacity
        total_people = self.guests + self.children
        if total_people > 10:
            raise ValueError(f'Total people ({total_people}) exceeds maximum (10)')
        
        # Rule 3: Minimum stay
        nights = (self.check_out - self.check_in).days
        if nights < 1:
            raise ValueError('Minimum 1 night stay required')
        
        return self

@app.post("/complex/password-reset")
def reset_password(data: PasswordReset):
    """
    Complex validation: Passwords must match
    
    Invalid:
    {
      "password": "Pass123!",
      "password_confirmation": "Different123!"
    }
    → "Passwords do not match"
    """
    return {"message": "Passwords match and validated"}

@app.post("/complex/personal-info")
def submit_personal_info(info: PersonalInfo):
    """
    Conditional validation demo
    
    Invalid examples:
    
    1. Married without partner name:
       {"name": "John", "married": true}
       → "Partner name required when married"
    
    2. Has children without count:
       {"name": "John", "married": false, "has_children": true}
       → "Number of children required when has_children=True"
    """
    return {"message": "Personal info validated", "info": info}

@app.post("/complex/booking")
def create_booking(booking: BookingRequest):
    """
    Complex business rules validation
    
    Invalid examples:
    
    1. Check-out before check-in:
       {"check_in": "2024-02-01", "check_out": "2024-01-31", "guests": 2}
       → "Check-out must be after check-in"
    
    2. Too many people:
       {"check_in": "2024-02-01", "check_out": "2024-02-05", 
        "guests": 8, "children": 4}
       → "Total people (12) exceeds maximum (10)"
    """
    return {"message": "Booking validated", "booking": booking}
```

### PART 5: TRANSFORMATIONS (Type Casting & Normalization)

```python
from pydantic import BaseModel, field_validator, Field
from typing import Optional

class SearchRequest(BaseModel):
    """
    TRANSFORMATION: Type Casting
    
    Query parameters always arrive as strings!
    Pydantic automatically casts them to correct types
    """
    # These will be cast from strings automatically
    page: int = Field(1, ge=1, le=1000)  # "2" → 2
    limit: int = Field(10, ge=1, le=100)  # "20" → 20
    sort: str = "date"  # String stays string
    ascending: bool = True  # "true" → True, "false" → False

@app.get("/search/auto-casting")
def search_with_casting(params: SearchRequest = Query()):
    """
    Automatic Type Casting Demo
    
    URL: /search/auto-casting?page=2&limit=20&ascending=false
    
    Pydantic automatically:
    - "2" (string) → 2 (int)
    - "20" (string) → 20 (int)
    - "false" (string) → False (bool)
    
    Then validates:
    - page >= 1 and page <= 1000
    - limit >= 1 and limit <= 100
    """
    return {
        "message": "Query params casted and validated",
        "params": params,
        "types": {
            "page": type(params.page).__name__,
            "limit": type(params.limit).__name__,
            "ascending": type(params.ascending).__name__
        }
    }

class UserRegistration(BaseModel):
    """
    TRANSFORMATION: Normalization/Sanitization
    
    Modify data to ensure consistency
    """
    email: EmailStr
    username: str
    phone: str
    country_code: str = "+1"  # Default
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v):
        """
        Transform: Convert email to lowercase
        
        User@Gmail.com → user@gmail.com
        
        Prevents duplicate accounts with different casings
        """
        return v.lower()
    
    @field_validator('username')
    @classmethod
    def normalize_username(cls, v):
        """
        Transform: Convert to lowercase, strip whitespace
        
        " JohnDoe " → "johndoe"
        """
        return v.strip().lower()
    
    @field_validator('phone')
    @classmethod
    def normalize_phone(cls, v):
        """
        Transform: Remove all non-digit characters
        
        (123) 456-7890 → 1234567890
        +1-234-567-8900 → 12345678900
        """
        return re.sub(r'\D', '', v)
    
    @model_validator(mode='after')
    def format_phone_with_country_code(self):
        """
        Transform: Add country code if missing
        
        1234567890 → +1-1234567890
        """
        if not self.phone.startswith(self.country_code):
            self.phone = f"{self.country_code}{self.phone}"
        return self

class ProductInput(BaseModel):
    """
    TRANSFORMATION: Setting defaults and cleaning data
    """
    name: str
    description: Optional[str] = None
    price: float
    discount: float = 0.0
    
    @field_validator('name')
    @classmethod
    def clean_name(cls, v):
        """
        Transform: Strip whitespace, capitalize
        
        "  smartphone  " → "Smartphone"
        """
        return v.strip().capitalize()
    
    @field_validator('description')
    @classmethod
    def clean_description(cls, v):
        """
        Transform: Strip whitespace, or set to default message
        """
        if v:
            v = v.strip()
            if not v:  # Empty after stripping
                return "No description provided"
            return v
        return "No description provided"
    
    @model_validator(mode='after')
    def calculate_final_price(self):
        """
        Transform: Add calculated field
        
        Adds 'final_price' based on price and discount
        """
        self.final_price = self.price * (1 - self.discount / 100)
        return self

@app.post("/users/transformation")
def register_user_with_transformation(user: UserRegistration):
    """
    Transformation Demo: Normalization
    
    Input:
    {
      "email": "User@Gmail.COM",
      "username": " JohnDoe ",
      "phone": "(234) 567-8900"
    }
    
    After transformation:
    {
      "email": "user@gmail.com",
      "username": "johndoe",
      "phone": "+1234567890"
    }
    
    Benefits:
    - Prevents duplicate accounts (case-insensitive matching)
    - Consistent phone format in database
    - Clean usernames
    """
    return {
        "message": "User registered with transformations applied",
        "user": user,
        "transformations": [
            "Email converted to lowercase",
            "Username trimmed and lowercased",
            "Phone normalized and formatted"
        ]
    }
```

### PART 6: FRONTEND VS BACKEND VALIDATION

```python
from fastapi import FastAPI, HTTPException

# Simulated database
users_db = {"alice": {"email": "alice@example.com"}}

class UserRegistration(BaseModel):
    """
    BACKEND VALIDATION: Cannot trust frontend!
    
    Even if frontend validates, backend must re-validate everything
    """
    username: str
    email: EmailStr
    password: str
    age: int
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """
        Backend validation: Check uniqueness
        
        Frontend might check this, but attacker can bypass!
        Backend MUST check again
        """
        if v in users_db:
            raise ValueError('Username already exists')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v
    
    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        """
        Backend validation: Age restrictions
        
        Even if frontend has a dropdown (18-100),
        attacker can send age=5 via Postman!
        """
        if v < 18:
            raise ValueError('Must be 18 or older')
        if v > 120:
            raise ValueError('Age unrealistic')
        return v

@app.post("/register/backend-validation")
def register_with_backend_validation(user: UserRegistration):
    """
    BACKEND VALIDATION: Zero Trust
    
    Frontend Validation (UX):
    - Shows red box if email invalid
    - Disables submit button if password weak
    - Provides immediate feedback
    
    Backend Validation (Security):
    - Re-validates EVERYTHING
    - Assumes frontend can be bypassed
    - Protects database integrity
    
    Why both needed:
    - Frontend: Better UX, saves bandwidth
    - Backend: Security, cannot trust client
    
    Attack scenario:
    Attacker uses Postman to send:
    {
      "username": "a",  ← Too short (bypassed frontend)
      "email": "not-email",  ← Invalid (bypassed frontend)
      "password": "weak",  ← Too weak (bypassed frontend)
      "age": 5  ← Too young (bypassed frontend dropdown)
    }
    
    Backend catches ALL of these! Returns 422 with details.
    """
    # If we reach here, all validations passed
    users_db[user.username] = user.dict()
    
    return {
        "message": "User registered",
        "note": "Backend validated everything, regardless of frontend",
        "username": user.username
    }

@app.get("/validation/philosophy")
def validation_philosophy():
    """
    Explains the validation philosophy
    """
    return {
        "principle": "Zero Trust - Never trust the client",
        "frontend_validation": {
            "purpose": "User Experience (UX)",
            "benefits": [
                "Immediate feedback",
                "No network roundtrip",
                "Saves bandwidth",
                "Better UX"
            ],
            "limitation": "Can be completely bypassed"
        },
        "backend_validation": {
            "purpose": "Security & Data Integrity",
            "benefits": [
                "Cannot be bypassed",
                "Protects database",
                "Prevents malicious data",
                "Ensures data quality"
            ],
            "rule": "Design as if frontend validation doesn't exist"
        },
        "attack_vectors": [
            "Postman/Insomnia (direct API calls)",
            "Browser dev tools (modify JavaScript)",
            "curl commands",
            "Custom scripts"
        ],
        "best_practice": "Implement both, but backend is MANDATORY"
    }
```

---

## 🎯 Practice Exercises

### Exercise 1: Type Validation ✅
```python
# TODO:
# 1. Create Product model with: name (str), price (float), quantity (int)
# 2. Test sending wrong types
# 3. Observe 422 errors
```

### Exercise 2: Syntactic Validation ✅
```python
# TODO:
# 1. Create model with email, phone, URL validation
# 2. Use regex for custom patterns
# 3. Test invalid formats
```

### Exercise 3: Semantic Validation ✅
```python
# TODO:
# 1. Create Event model with start_date, end_date
# 2. Validate end_date > start_date
# 3. Validate dates not in past
```

### Exercise 4: Transformations ✅
```python
# TODO:
# 1. Create User model that normalizes email to lowercase
# 2. Transform phone numbers to standard format
# 3. Test with messy input
```

### Exercise 5: Complex Validation ✅
```python
# TODO:
# 1. Create form with password + password_confirmation
# 2. Validate they match
# 3. Add conditional: if newsletter=True, email required
```

---

## 🎓 Mastery Checklist

Can you:
- [ ] Explain the 4 types of validation?
- [ ] Implement type validation with Pydantic?
- [ ] Use field_validator for custom validation?
- [ ] Use model_validator for multi-field validation?
- [ ] Transform data with validators (lowercase email)?
- [ ] Understand query param type casting?
- [ ] Explain why backend validation is mandatory?
- [ ] Debug 422 validation errors?
- [ ] Implement conditional validation?
- [ ] Normalize data for consistency?

---

## 💭 Key Insights

### Pydantic's Power
- Automatic type validation
- Type coercion ("2" → 2)
- Detailed error messages (422)
- Custom validators for any logic
- Transformations in same flow

### Security Critical
**NEVER trust frontend validation!**
- Frontend = UX convenience
- Backend = Security requirement
- Design assuming frontend bypassed
- Validate everything, every time

### 422 vs 400
- FastAPI returns **422 Unprocessable Entity**
- Your lecture mentions **400 Bad Request**
- Both serve same purpose: client error
- 422 is more specific: "syntax ok, semantics bad"

---

**Last Updated**: 2026-01-29  
**Status**: 🟡 In Progress  
**Next**: Build complete validation pipeline
