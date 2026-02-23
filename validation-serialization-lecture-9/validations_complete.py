"""
Complete Validations & Transformations Example - FastAPI
Demonstrates all 4 validation types + transformations from Lecture 9

Run with: fastapi dev validations_complete.py
Visit: http://127.0.0.1:8000/docs

Install dependencies:
pip install "fastapi[standard]" pydantic[email]
"""

from fastapi import FastAPI, Query, HTTPException, status
from pydantic import BaseModel, EmailStr, HttpUrl, Field, field_validator, model_validator
from typing import Optional, List
from datetime import date, datetime, timedelta
from enum import Enum
import re

# ============================================================================
# APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Validations & Transformations Complete Example",
    description="All 4 validation types: Type, Syntactic, Semantic, Complex + Transformations",
    version="1.0.0"
)

# ============================================================================
# DATA STORAGE (Simulated Database)
# ============================================================================

users_db = {
    "alice": {
        "username": "alice",
        "email": "alice@example.com",
        "age": 25
    }
}

products_db = {}
bookings_db = {}
registrations_db = {}

# ============================================================================
# SECTION 1: TYPE VALIDATION (Automatic with Pydantic)
# ============================================================================

class Book(BaseModel):
    """
    TYPE VALIDATION - Automatic with Pydantic Type Hints
    
    Pydantic automatically validates that data matches expected types:
    - title: Must be string
    - author: Must be string
    - year: Must be integer
    - price: Must be float
    - tags: Must be list of strings
    - available: Must be boolean
    - pages: Must be integer or None
    
    If wrong type is sent, Pydantic returns 422 with detailed error
    """
    title: str
    author: str
    year: int
    price: float
    tags: List[str]
    available: bool = True
    pages: Optional[int] = None

@app.post("/validation/type/book")
def create_book_type_validation(book: Book):
    """
    TYPE VALIDATION DEMO
    
    Valid Request:
    {
      "title": "1984",
      "author": "George Orwell",
      "year": 1949,
      "price": 12.99,
      "tags": ["dystopian", "classic"],
      "available": true,
      "pages": 328
    }
    
    INVALID Requests (will return 422):
    
    1. Wrong type for title:
       {"title": 123, "author": "Orwell", ...}
       → Error: "Input should be a valid string"
    
    2. Wrong type for year:
       {"title": "1984", "author": "Orwell", "year": "nineteen forty-nine", ...}
       → Error: "Input should be a valid integer"
    
    3. Wrong type for price:
       {"title": "1984", "author": "Orwell", "year": 1949, "price": "expensive", ...}
       → Error: "Input should be a valid number"
    
    4. Wrong type for tags:
       {"title": "1984", "author": "Orwell", "year": 1949, "price": 12.99, "tags": "dystopian", ...}
       → Error: "Input should be a valid list"
    
    5. Wrong type for available:
       {"title": "1984", "author": "Orwell", "year": 1949, "price": 12.99, "tags": [], "available": "yes"}
       → Error: "Input should be a valid boolean"
    
    PYDANTIC TYPE COERCION (automatic conversion):
    - year: "1949" (string) → 1949 (int) ✅ WORKS
    - price: "12.99" (string) → 12.99 (float) ✅ WORKS
    - available: "true" (string) → True (bool) ✅ WORKS (in query params)
    - available: 1 (int) → True (bool) ✅ WORKS
    
    But if conversion is impossible, you get 422 error
    """
    return {
        "message": "Book validated successfully",
        "book": book,
        "validation_type": "TYPE VALIDATION",
        "types_validated": {
            "title": f"{type(book.title).__name__} (expected: str)",
            "author": f"{type(book.author).__name__} (expected: str)",
            "year": f"{type(book.year).__name__} (expected: int)",
            "price": f"{type(book.price).__name__} (expected: float)",
            "tags": f"{type(book.tags).__name__} (expected: List[str])",
            "available": f"{type(book.available).__name__} (expected: bool)"
        }
    }

@app.get("/validation/type/demo")
def type_validation_demo():
    """
    Shows what type validation catches
    """
    return {
        "validation_type": "TYPE VALIDATION",
        "purpose": "Ensures data matches expected primitive types",
        "what_it_catches": {
            "wrong_type": "Sending number when string expected",
            "array_vs_string": "Sending 'text' when ['text'] expected",
            "null_for_required": "Sending null/None for required field"
        },
        "pydantic_features": {
            "automatic": "No code needed - just type hints",
            "type_coercion": "Automatically converts compatible types ('123' → 123)",
            "detailed_errors": "Returns exact field and expected type in 422 error"
        },
        "example": {
            "valid": {"name": "Alice", "age": 25},
            "invalid_type": {"name": "Alice", "age": "twenty-five"},
            "invalid_null": {"name": "Alice", "age": None}
        }
    }

# ============================================================================
# SECTION 2: SYNTACTIC VALIDATION (Structure/Format)
# ============================================================================

class UserRegistration(BaseModel):
    """
    SYNTACTIC VALIDATION - Format and Structure Checks
    
    Validates that data follows specific patterns:
    - Email: Must follow email format (user@domain.com)
    - Website: Must be valid URL (https://example.com)
    - Phone: Must match specific pattern (+1-234-567-8900)
    - Username: Must be alphanumeric, 3-20 characters
    - Password: Must meet complexity requirements
    """
    
    # Built-in validators
    email: EmailStr  # Automatically validates email format
    website: Optional[HttpUrl] = None  # Automatically validates URL format
    
    # Custom pattern validators
    phone: str
    username: str
    password: str
    zip_code: str
    
    @field_validator('phone')
    @classmethod
    def validate_phone_format(cls, v):
        """
        Syntactic Validation: Phone number format
        
        Accepts: +1-234-567-8900
        Rejects: 1234567890, (234) 567-8900, abc-def-ghij
        """
        pattern = r'^\+\d{1,3}-\d{3}-\d{3}-\d{4}$'
        if not re.match(pattern, v):
            raise ValueError(
                'Phone must be in format: +1-234-567-8900 '
                '(country code + area code + number)'
            )
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username_format(cls, v):
        """
        Syntactic Validation: Username structure
        
        Rules:
        - Only alphanumeric and underscores
        - 3-20 characters
        - Cannot start with number
        - No spaces or special characters
        """
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{2,19}$', v):
            raise ValueError(
                'Username must: '
                '(1) Start with letter, '
                '(2) Be 3-20 characters, '
                '(3) Contain only letters, numbers, underscores'
            )
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password_format(cls, v):
        """
        Syntactic Validation: Password strength/complexity
        
        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        errors = []
        
        if len(v) < 8:
            errors.append("at least 8 characters")
        if not re.search(r'[A-Z]', v):
            errors.append("one uppercase letter")
        if not re.search(r'[a-z]', v):
            errors.append("one lowercase letter")
        if not re.search(r'\d', v):
            errors.append("one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            errors.append("one special character (!@#$%^&* etc.)")
        
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        
        return v
    
    @field_validator('zip_code')
    @classmethod
    def validate_zip_code_format(cls, v):
        """
        Syntactic Validation: US ZIP code format
        
        Accepts: 12345 or 12345-6789
        Rejects: 123, ABCDE, 12345-67
        """
        pattern = r'^\d{5}(-\d{4})?$'
        if not re.match(pattern, v):
            raise ValueError('ZIP code must be 5 digits or 5+4 format (12345 or 12345-6789)')
        return v

@app.post("/validation/syntactic/user")
def register_user_syntactic(user: UserRegistration):
    """
    SYNTACTIC VALIDATION DEMO
    
    Valid Request:
    {
      "email": "user@example.com",
      "website": "https://example.com",
      "phone": "+1-234-567-8900",
      "username": "john_doe",
      "password": "SecurePass123!",
      "zip_code": "12345"
    }
    
    INVALID Requests (422 errors):
    
    1. Invalid email:
       {"email": "not-an-email", ...}
       → "value is not a valid email address"
    
    2. Invalid phone:
       {"phone": "1234567890", ...}
       → "Phone must be in format: +1-234-567-8900"
    
    3. Invalid username (too short):
       {"username": "ab", ...}
       → "Username must be 3-20 characters"
    
    4. Invalid username (starts with number):
       {"username": "1user", ...}
       → "Username must start with letter"
    
    5. Weak password:
       {"password": "weak", ...}
       → "Password must contain: at least 8 characters, one uppercase..."
    
    6. Invalid ZIP:
       {"zip_code": "123", ...}
       → "ZIP code must be 5 digits"
    """
    return {
        "message": "User registered with valid formats",
        "user": user,
        "validation_type": "SYNTACTIC VALIDATION",
        "formats_validated": {
            "email": "Email address structure",
            "website": "URL format",
            "phone": "Phone number pattern (+X-XXX-XXX-XXXX)",
            "username": "Alphanumeric, 3-20 chars, starts with letter",
            "password": "8+ chars, uppercase, lowercase, digit, special",
            "zip_code": "US ZIP code (12345 or 12345-6789)"
        }
    }

# ============================================================================
# SECTION 3: SEMANTIC VALIDATION (Meaning/Logic)
# ============================================================================

class PersonProfile(BaseModel):
    """
    SEMANTIC VALIDATION - Real-world meaning checks
    
    Even if syntax is correct, data must make sense in reality:
    - Age must be realistic (not 430 years old)
    - Date of birth cannot be in the future
    - Height must be reasonable human height
    - Weight must be reasonable
    - Retirement age must be realistic
    """
    name: str
    date_of_birth: date
    age: int
    height_cm: float
    weight_kg: float
    retirement_age: Optional[int] = None
    
    @field_validator('age')
    @classmethod
    def validate_age_realistic(cls, v):
        """
        Semantic Validation: Age must be realistic
        
        Valid: 1, 25, 80, 120
        Invalid: 0, -5, 430, 200
        
        Why: Humans don't live to 430 years old!
        """
        if v < 1:
            raise ValueError('Age must be at least 1')
        if v > 120:
            raise ValueError(
                'Age cannot exceed 120 years '
                '(oldest verified person was 122)'
            )
        return v
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_dob_not_future(cls, v):
        """
        Semantic Validation: Date of birth cannot be in future
        
        Valid: 1990-01-01 (past date)
        Invalid: 2030-01-01 (future date)
        
        Why: You cannot be born in the future!
        """
        if v > date.today():
            raise ValueError('Date of birth cannot be in the future')
        
        # Additional: Not too far in past (150 years)
        if v < date.today() - timedelta(days=150*365):
            raise ValueError('Date of birth cannot be more than 150 years ago')
        
        return v
    
    @field_validator('height_cm')
    @classmethod
    def validate_height_realistic(cls, v):
        """
        Semantic Validation: Height must be realistic
        
        Valid: 50-250 cm (baby to very tall person)
        Invalid: 10 cm, 500 cm
        
        Why: Humans range from ~50cm (newborn) to ~272cm (tallest recorded)
        """
        if v < 30:
            raise ValueError('Height too small (minimum 30cm for newborn)')
        if v > 300:
            raise ValueError('Height too large (maximum 300cm)')
        return v
    
    @field_validator('weight_kg')
    @classmethod
    def validate_weight_realistic(cls, v):
        """
        Semantic Validation: Weight must be realistic
        
        Valid: 2-300 kg
        Invalid: 0.5 kg, 1000 kg
        """
        if v < 2:
            raise ValueError('Weight too small (minimum 2kg for newborn)')
        if v > 500:
            raise ValueError('Weight too large (maximum 500kg)')
        return v
    
    @field_validator('retirement_age')
    @classmethod
    def validate_retirement_age(cls, v):
        """
        Semantic Validation: Retirement age must be realistic
        
        Valid: 55-75
        Invalid: 25, 100
        """
        if v is None:
            return v
        
        if v < 50:
            raise ValueError('Retirement age must be at least 50')
        if v > 80:
            raise ValueError('Retirement age cannot exceed 80')
        return v

class EventBooking(BaseModel):
    """
    Semantic Validation: Date ranges must make sense
    """
    event_name: str
    start_date: date
    end_date: date
    max_attendees: int
    ticket_price: float
    discount_percent: float = 0.0
    
    @field_validator('end_date')
    @classmethod
    def validate_end_after_start(cls, v, info):
        """
        Semantic Validation: End date must be after start date
        
        Valid: start=2024-01-01, end=2024-01-05
        Invalid: start=2024-01-05, end=2024-01-01
        
        Why: Event cannot end before it starts!
        """
        start_date = info.data.get('start_date')
        if start_date and v < start_date:
            raise ValueError('End date must be after start date')
        return v
    
    @field_validator('start_date')
    @classmethod
    def validate_start_not_past(cls, v):
        """
        Semantic Validation: Cannot book events in the past
        """
        if v < date.today():
            raise ValueError('Cannot book events in the past')
        return v
    
    @field_validator('max_attendees')
    @classmethod
    def validate_max_attendees(cls, v):
        """
        Semantic Validation: Attendee count must be reasonable
        """
        if v < 1:
            raise ValueError('Must allow at least 1 attendee')
        if v > 100000:
            raise ValueError('Maximum 100,000 attendees')
        return v
    
    @field_validator('ticket_price')
    @classmethod
    def validate_ticket_price(cls, v):
        """
        Semantic Validation: Price must be positive
        """
        if v < 0:
            raise ValueError('Ticket price cannot be negative')
        if v > 10000:
            raise ValueError('Ticket price cannot exceed $10,000')
        return v
    
    @field_validator('discount_percent')
    @classmethod
    def validate_discount(cls, v):
        """
        Semantic Validation: Discount percentage must be valid
        
        Valid: 0-100
        Invalid: -10, 150
        
        Why: Cannot have negative discount or more than 100% off!
        """
        if v < 0:
            raise ValueError('Discount cannot be negative')
        if v > 100:
            raise ValueError('Discount cannot exceed 100%')
        return v

@app.post("/validation/semantic/person")
def create_person_profile(person: PersonProfile):
    """
    SEMANTIC VALIDATION DEMO
    
    Valid Request:
    {
      "name": "John Doe",
      "date_of_birth": "1990-01-01",
      "age": 34,
      "height_cm": 175.5,
      "weight_kg": 75.0,
      "retirement_age": 65
    }
    
    INVALID Requests (422 errors):
    
    1. Unrealistic age:
       {"age": 430, ...}
       → "Age cannot exceed 120 years"
    
    2. Future birth date:
       {"date_of_birth": "2030-01-01", ...}
       → "Date of birth cannot be in the future"
    
    3. Unrealistic height:
       {"height_cm": 500, ...}
       → "Height too large"
    
    4. Unrealistic weight:
       {"weight_kg": 1000, ...}
       → "Weight too large"
    
    5. Invalid retirement age:
       {"retirement_age": 25, ...}
       → "Retirement age must be at least 50"
    """
    return {
        "message": "Person profile validated",
        "person": person,
        "validation_type": "SEMANTIC VALIDATION",
        "meaning_checks": {
            "age": "Must be realistic (1-120 years)",
            "date_of_birth": "Cannot be in future or >150 years ago",
            "height": "Must be realistic human height (30-300cm)",
            "weight": "Must be realistic human weight (2-500kg)",
            "retirement_age": "Must be realistic (50-80)"
        }
    }

@app.post("/validation/semantic/event")
def create_event_booking(event: EventBooking):
    """
    SEMANTIC VALIDATION DEMO - Date Logic
    
    Valid Request:
    {
      "event_name": "Tech Conference",
      "start_date": "2024-06-01",
      "end_date": "2024-06-03",
      "max_attendees": 500,
      "ticket_price": 299.99,
      "discount_percent": 10.0
    }
    
    INVALID Requests:
    
    1. End before start:
       {"start_date": "2024-06-05", "end_date": "2024-06-01", ...}
       → "End date must be after start date"
    
    2. Event in past:
       {"start_date": "2020-01-01", ...}
       → "Cannot book events in the past"
    
    3. Discount > 100%:
       {"discount_percent": 150, ...}
       → "Discount cannot exceed 100%"
    """
    return {
        "message": "Event booking validated",
        "event": event,
        "validation_type": "SEMANTIC VALIDATION - Date Logic"
    }

# ============================================================================
# SECTION 4: COMPLEX/CONDITIONAL VALIDATION
# ============================================================================

class PasswordResetForm(BaseModel):
    """
    COMPLEX VALIDATION - Multi-field logic
    
    Password and confirmation must match
    """
    password: str
    password_confirmation: str
    
    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        """First validate individual password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @model_validator(mode='after')
    def passwords_must_match(self):
        """
        Complex Validation: Compare two fields
        
        This runs AFTER all individual field validators
        Checks that password == password_confirmation
        """
        if self.password != self.password_confirmation:
            raise ValueError('Passwords do not match')
        return self

class EmployeeRegistration(BaseModel):
    """
    CONDITIONAL VALIDATION - Fields required based on other fields
    
    Business rules:
    - If married=True, partner_name is REQUIRED
    - If has_children=True, number_of_children is REQUIRED
    - If manager=True, department is REQUIRED
    """
    name: str
    email: EmailStr
    married: bool = False
    partner_name: Optional[str] = None
    has_children: bool = False
    number_of_children: Optional[int] = None
    is_manager: bool = False
    department: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_conditional_requirements(self):
        """
        Conditional Validation: Field requirements based on other fields
        
        Rules:
        1. married=True → partner_name REQUIRED
        2. has_children=True → number_of_children REQUIRED
        3. is_manager=True → department REQUIRED
        """
        # Rule 1: If married, must have partner name
        if self.married and not self.partner_name:
            raise ValueError('Partner name is required when married')
        
        # Rule 2: If has children, must specify number
        if self.has_children:
            if self.number_of_children is None:
                raise ValueError('Number of children required when has_children=True')
            if self.number_of_children < 1:
                raise ValueError('Number of children must be at least 1 if has_children=True')
        
        # Rule 3: Cannot have children count without has_children flag
        if not self.has_children and self.number_of_children is not None:
            raise ValueError('Cannot specify number_of_children when has_children=False')
        
        # Rule 4: If manager, must specify department
        if self.is_manager and not self.department:
            raise ValueError('Department is required for managers')
        
        return self

class HotelBooking(BaseModel):
    """
    COMPLEX BUSINESS RULES - Multiple constraints
    """
    guest_name: str
    email: EmailStr
    check_in: date
    check_out: date
    adults: int
    children: int = 0
    room_type: str
    special_requests: Optional[str] = None
    
    @field_validator('adults')
    @classmethod
    def validate_adults(cls, v):
        """At least 1 adult, max 10"""
        if v < 1:
            raise ValueError('At least 1 adult required')
        if v > 10:
            raise ValueError('Maximum 10 adults per booking')
        return v
    
    @field_validator('children')
    @classmethod
    def validate_children(cls, v):
        """Children count must be reasonable"""
        if v < 0:
            raise ValueError('Children count cannot be negative')
        if v > 10:
            raise ValueError('Maximum 10 children per booking')
        return v
    
    @field_validator('room_type')
    @classmethod
    def validate_room_type(cls, v):
        """Room type must be valid"""
        valid_types = ['single', 'double', 'suite', 'deluxe']
        if v.lower() not in valid_types:
            raise ValueError(f'Room type must be one of: {", ".join(valid_types)}')
        return v.lower()
    
    @model_validator(mode='after')
    def validate_booking_logic(self):
        """
        Complex Business Rules:
        1. Check-out must be after check-in
        2. Total guests (adults + children) cannot exceed room capacity
        3. Minimum 1 night stay
        4. Cannot book in the past
        5. Cannot book more than 1 year in advance
        """
        # Rule 1: Date logic
        if self.check_out <= self.check_in:
            raise ValueError('Check-out date must be after check-in date')
        
        # Rule 2: Room capacity
        total_guests = self.adults + self.children
        room_capacity = {
            'single': 2,
            'double': 4,
            'suite': 6,
            'deluxe': 8
        }
        
        max_capacity = room_capacity.get(self.room_type, 4)
        if total_guests > max_capacity:
            raise ValueError(
                f'Total guests ({total_guests}) exceeds {self.room_type} '
                f'room capacity ({max_capacity})'
            )
        
        # Rule 3: Minimum stay
        nights = (self.check_out - self.check_in).days
        if nights < 1:
            raise ValueError('Minimum 1 night stay required')
        
        # Rule 4: Cannot book in past
        if self.check_in < date.today():
            raise ValueError('Cannot book dates in the past')
        
        # Rule 5: Cannot book too far in future
        max_advance_days = 365
        if self.check_in > date.today() + timedelta(days=max_advance_days):
            raise ValueError(f'Cannot book more than {max_advance_days} days in advance')
        
        return self

@app.post("/validation/complex/password-reset")
def reset_password(form: PasswordResetForm):
    """
    COMPLEX VALIDATION DEMO - Password Matching
    
    Valid Request:
    {
      "password": "SecurePass123!",
      "password_confirmation": "SecurePass123!"
    }
    
    INVALID Request:
    {
      "password": "SecurePass123!",
      "password_confirmation": "Different123!"
    }
    → "Passwords do not match"
    """
    return {
        "message": "Password reset validated",
        "validation_type": "COMPLEX VALIDATION",
        "rule": "password == password_confirmation"
    }

@app.post("/validation/complex/employee")
def register_employee(employee: EmployeeRegistration):
    """
    CONDITIONAL VALIDATION DEMO
    
    Valid Request 1 (married with partner):
    {
      "name": "John",
      "email": "john@example.com",
      "married": true,
      "partner_name": "Jane",
      "has_children": false,
      "is_manager": false
    }
    
    Valid Request 2 (has children):
    {
      "name": "John",
      "email": "john@example.com",
      "married": false,
      "has_children": true,
      "number_of_children": 2,
      "is_manager": false
    }
    
    INVALID Requests:
    
    1. Married without partner name:
       {"married": true, "partner_name": null, ...}
       → "Partner name is required when married"
    
    2. Has children without count:
       {"has_children": true, "number_of_children": null, ...}
       → "Number of children required when has_children=True"
    
    3. Manager without department:
       {"is_manager": true, "department": null, ...}
       → "Department is required for managers"
    """
    return {
        "message": "Employee registration validated",
        "employee": employee,
        "validation_type": "CONDITIONAL VALIDATION",
        "rules_checked": [
            "married → partner_name required",
            "has_children → number_of_children required",
            "is_manager → department required"
        ]
    }

@app.post("/validation/complex/hotel-booking")
def create_hotel_booking(booking: HotelBooking):
    """
    COMPLEX BUSINESS RULES DEMO
    
    Valid Request:
    {
      "guest_name": "John Doe",
      "email": "john@example.com",
      "check_in": "2024-06-01",
      "check_out": "2024-06-05",
      "adults": 2,
      "children": 1,
      "room_type": "double"
    }
    
    INVALID Requests:
    
    1. Check-out before check-in:
       {"check_in": "2024-06-05", "check_out": "2024-06-01", ...}
       → "Check-out date must be after check-in date"
    
    2. Too many guests for room:
       {"adults": 5, "children": 3, "room_type": "single", ...}
       → "Total guests (8) exceeds single room capacity (2)"
    
    3. Booking in past:
       {"check_in": "2020-01-01", ...}
       → "Cannot book dates in the past"
    """
    nights = (booking.check_out - booking.check_in).days
    total_guests = booking.adults + booking.children
    
    return {
        "message": "Hotel booking validated",
        "booking": booking,
        "validation_type": "COMPLEX BUSINESS RULES",
        "computed_values": {
            "nights": nights,
            "total_guests": total_guests
        }
    }

# ============================================================================
# SECTION 5: TRANSFORMATIONS (Type Casting & Normalization)
# ============================================================================

class SearchQuery(BaseModel):
    """
    TRANSFORMATION: Type Casting from Query Parameters
    
    Query parameters ALWAYS arrive as strings!
    Pydantic automatically casts them to correct types
    
    Example URL: /search?page=2&limit=20&sort=date&ascending=false
    - "2" (string) → 2 (int)
    - "20" (string) → 20 (int)
    - "false" (string) → False (bool)
    """
    page: int = Field(1, ge=1, le=1000, description="Page number")
    limit: int = Field(10, ge=1, le=100, description="Items per page")
    sort: str = Field("date", description="Sort field")
    ascending: bool = Field(True, description="Sort order")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")

@app.get("/transformation/search")
def search_with_casting(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(10, ge=1, le=100),
    sort: str = Query("date"),
    ascending: bool = Query(True),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0)
):
    """
    TRANSFORMATION DEMO: Type Casting
    
    Try these URLs:
    
    1. /transformation/search?page=2&limit=20
       → Casts "2" → 2, "20" → 20
    
    2. /transformation/search?page=5&limit=50&ascending=false
       → Casts "5" → 5, "50" → 50, "false" → False
    
    3. /transformation/search?min_price=10.50&max_price=99.99
       → Casts "10.50" → 10.5, "99.99" → 99.99
    
    Pydantic automatically:
    - Converts string to int: "2" → 2
    - Converts string to float: "10.50" → 10.5
    - Converts string to bool: "false" → False, "true" → True
    - Validates constraints: page >= 1, page <= 1000
    
    If conversion fails (e.g., page=abc), returns 422 error
    """
    return {
        "message": "Query parameters casted successfully",
        "transformation_type": "TYPE CASTING",
        "params": {
            "page": page,
            "limit": limit,
            "sort": sort,
            "ascending": ascending,
            "min_price": min_price,
            "max_price": max_price
        },
        "types": {
            "page": type(page).__name__,
            "limit": type(limit).__name__,
            "sort": type(sort).__name__,
            "ascending": type(ascending).__name__
        },
        "note": "All values were casted from strings to their proper types"
    }

class UserInput(BaseModel):
    """
    TRANSFORMATION: Normalization/Sanitization
    
    Modify data to ensure consistency across the system
    """
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    phone: str
    country_code: str = "+1"
    bio: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v):
        """
        Transform: Convert email to lowercase
        
        Input: User@Gmail.COM
        Output: user@gmail.com
        
        Benefit: Prevents duplicate accounts with different casings
        """
        return v.lower()
    
    @field_validator('username')
    @classmethod
    def normalize_username(cls, v):
        """
        Transform: Strip whitespace, convert to lowercase
        
        Input: "  JohnDoe  "
        Output: "johndoe"
        """
        return v.strip().lower()
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def normalize_names(cls, v):
        """
        Transform: Strip whitespace, capitalize first letter
        
        Input: "  john  "
        Output: "John"
        """
        return v.strip().capitalize()
    
    @field_validator('phone')
    @classmethod
    def normalize_phone(cls, v):
        """
        Transform: Remove all non-digit characters
        
        Input: (123) 456-7890
        Output: 1234567890
        
        Input: +1-234-567-8900
        Output: 12345678900
        """
        return re.sub(r'\D', '', v)
    
    @field_validator('bio')
    @classmethod
    def clean_bio(cls, v):
        """
        Transform: Strip whitespace, set default if empty
        
        Input: "   "
        Output: None
        """
        if v:
            v = v.strip()
            return v if v else None
        return None
    
    @model_validator(mode='after')
    def format_phone_number(self):
        """
        Transform: Format phone with country code
        
        Input: phone="2345678900", country_code="+1"
        Output: phone="+12345678900"
        """
        if self.phone and not self.phone.startswith('+'):
            self.phone = f"{self.country_code}{self.phone}"
        return self

class ProductInput(BaseModel):
    """
    TRANSFORMATION: Setting defaults and computed values
    """
    name: str
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    discount_percent: float = Field(0, ge=0, le=100)
    category: str
    
    @field_validator('name')
    @classmethod
    def clean_name(cls, v):
        """
        Transform: Strip whitespace, title case
        
        Input: "  wireless headphones  "
        Output: "Wireless Headphones"
        """
        return v.strip().title()
    
    @field_validator('category')
    @classmethod
    def normalize_category(cls, v):
        """
        Transform: Lowercase for consistency
        
        Input: "Electronics"
        Output: "electronics"
        """
        return v.strip().lower()
    
    @field_validator('description')
    @classmethod
    def set_default_description(cls, v):
        """
        Transform: Provide default if empty
        """
        if not v or not v.strip():
            return "No description available"
        return v.strip()
    
    @model_validator(mode='after')
    def calculate_final_price(self):
        """
        Transform: Add computed field
        
        Calculates final_price based on price and discount
        """
        discount_amount = self.price * (self.discount_percent / 100)
        self.final_price = round(self.price - discount_amount, 2)
        return self

@app.post("/transformation/user")
def register_user_transformation(user: UserInput):
    """
    TRANSFORMATION DEMO: Normalization
    
    Input (messy data):
    {
      "email": "User@GMAIL.com",
      "username": "  JohnDoe  ",
      "first_name": "  john  ",
      "last_name": "  DOE  ",
      "phone": "(234) 567-8900",
      "bio": "   I love coding   "
    }
    
    Output (clean data):
    {
      "email": "user@gmail.com",
      "username": "johndoe",
      "first_name": "John",
      "last_name": "Doe",
      "phone": "+12345678900",
      "bio": "I love coding"
    }
    
    Transformations applied:
    1. Email → lowercase
    2. Username → trimmed, lowercase
    3. Names → trimmed, capitalized
    4. Phone → digits only, formatted with country code
    5. Bio → trimmed
    """
    return {
        "message": "User data transformed and normalized",
        "user": user,
        "transformation_type": "NORMALIZATION",
        "transformations_applied": [
            "Email: User@GMAIL.com → user@gmail.com",
            "Username: '  JohnDoe  ' → 'johndoe'",
            "Names: '  john  ' → 'John'",
            "Phone: '(234) 567-8900' → '+12345678900'",
            "Bio: Trimmed whitespace"
        ],
        "benefits": [
            "Prevents duplicate accounts (case-insensitive)",
            "Consistent formatting in database",
            "Easier searching and matching",
            "Better data quality"
        ]
    }

@app.post("/transformation/product")
def create_product_transformation(product: ProductInput):
    """
    TRANSFORMATION DEMO: Computed Values
    
    Input:
    {
      "name": "  wireless headphones  ",
      "description": "   ",
      "price": 99.99,
      "discount_percent": 15,
      "category": "Electronics"
    }
    
    Output:
    {
      "name": "Wireless Headphones",
      "description": "No description available",
      "price": 99.99,
      "discount_percent": 15,
      "category": "electronics",
      "final_price": 84.99  ← COMPUTED!
    }
    """
    return {
        "message": "Product created with transformations",
        "product": product,
        "transformation_type": "NORMALIZATION + COMPUTATION",
        "computed_values": {
            "final_price": product.final_price,
            "discount_amount": round(product.price - product.final_price, 2)
        }
    }

# ============================================================================
# SECTION 6: FRONTEND vs BACKEND VALIDATION
# ============================================================================

class FrontendBypassDemo(BaseModel):
    """
    Demonstrates why BACKEND validation is MANDATORY
    
    Even if frontend validates, backend must validate everything
    """
    username: str
    email: EmailStr
    age: int
    password: str
    agree_to_terms: bool
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """
        Backend validation: Check uniqueness and format
        
        Frontend might check this, but can be bypassed!
        """
        # Check if username exists
        if v.lower() in users_db:
            raise ValueError('Username already taken')
        
        # Check format
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        
        return v
    
    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        """
        Backend validation: Age restrictions
        
        Even if frontend has dropdown (18-100),
        attacker can send age=5 via Postman!
        """
        if v < 18:
            raise ValueError('Must be 18 or older to register')
        if v > 120:
            raise ValueError('Age is unrealistic')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """
        Backend validation: Password strength
        
        Frontend might have password meter,
        but backend MUST enforce rules!
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v
    
    @field_validator('agree_to_terms')
    @classmethod
    def validate_terms(cls, v):
        """
        Backend validation: Terms agreement
        
        Frontend might disable submit button,
        but attacker can send agree_to_terms=false!
        """
        if not v:
            raise ValueError('Must agree to terms and conditions')
        return v

@app.post("/validation/frontend-vs-backend")
def register_with_backend_validation(user: FrontendBypassDemo):
    """
    FRONTEND vs BACKEND VALIDATION DEMO
    
    SCENARIO: Attacker bypasses frontend using Postman
    
    Attack Attempt (all invalid):
    {
      "username": "a",  ← Too short (frontend would prevent)
      "email": "not-email",  ← Invalid format (frontend would prevent)
      "age": 5,  ← Too young (frontend dropdown: 18-100)
      "password": "weak",  ← Too weak (frontend password meter)
      "agree_to_terms": false  ← Frontend disables submit button
    }
    
    Backend Response: 422 with ALL errors listed!
    - Username must be at least 3 characters
    - value is not a valid email address
    - Must be 18 or older to register
    - Password must be at least 8 characters
    - Must agree to terms and conditions
    
    KEY INSIGHT: Backend caught EVERYTHING!
    
    Frontend Validation Purpose:
    ✅ Better User Experience (immediate feedback)
    ✅ Saves bandwidth (no unnecessary requests)
    ✅ Faster feedback (no network roundtrip)
    
    Backend Validation Purpose:
    ✅ SECURITY (cannot be bypassed)
    ✅ Data integrity (protects database)
    ✅ Prevents malicious data
    
    GOLDEN RULE: Design backend as if frontend doesn't exist!
    """
    # If we reach here, all validations passed
    users_db[user.username.lower()] = {
        "username": user.username,
        "email": user.email,
        "age": user.age
    }
    
    return {
        "message": "Registration successful",
        "note": "Backend validated everything, regardless of frontend",
        "username": user.username,
        "validation_philosophy": {
            "frontend": "User Experience (UX) - Can be bypassed",
            "backend": "Security - Cannot be bypassed",
            "rule": "ALWAYS validate on backend, even if frontend validates"
        }
    }

@app.get("/validation/philosophy")
def validation_philosophy():
    """
    Explains the validation philosophy and architecture
    """
    return {
        "title": "Validation & Transformation Philosophy",
        "architecture": {
            "flow": [
                "1. HTTP Request arrives",
                "2. Controller Layer receives request",
                "3. VALIDATION & TRANSFORMATION PIPELINE ← THE GATEKEEPER",
                "4. Service Layer (business logic) - receives CLEAN data",
                "5. Repository Layer (database) - receives TRANSFORMED data"
            ],
            "why_at_entry_point": [
                "Prevents 'unexpected state' in application",
                "Returns 422 (client error) instead of 500 (server crash)",
                "Protects database from invalid data",
                "Provides clear error messages to client"
            ]
        },
        "four_validation_types": {
            "type": {
                "purpose": "Ensures data matches expected type",
                "example": "Reject 'abc' when integer expected",
                "pydantic": "Automatic with type hints"
            },
            "syntactic": {
                "purpose": "Checks format/structure",
                "example": "Email must be user@domain.com",
                "pydantic": "EmailStr, HttpUrl, field_validator with regex"
            },
            "semantic": {
                "purpose": "Checks real-world meaning",
                "example": "Age cannot be 430 years",
                "pydantic": "Custom field_validator"
            },
            "complex": {
                "purpose": "Multi-field logic",
                "example": "Password must match confirmation",
                "pydantic": "model_validator"
            }
        },
        "transformations": {
            "type_casting": {
                "purpose": "Convert types",
                "example": "'2' (string) → 2 (int)",
                "when": "Query parameters, automatic with Pydantic"
            },
            "normalization": {
                "purpose": "Ensure consistency",
                "example": "User@Gmail.com → user@gmail.com",
                "when": "Before storage, custom validators"
            }
        },
        "frontend_vs_backend": {
            "frontend": {
                "purpose": "User Experience (UX)",
                "can_be_bypassed": True,
                "tools": ["Postman", "curl", "browser dev tools"]
            },
            "backend": {
                "purpose": "Security & Data Integrity",
                "can_be_bypassed": False,
                "mandatory": True,
                "rule": "Design as if frontend doesn't exist"
            }
        },
        "best_practices": [
            "Always validate on backend (even if frontend validates)",
            "Use Pydantic for automatic type validation",
            "Write custom validators for business rules",
            "Transform data before passing to service layer",
            "Return clear, specific error messages (422)",
            "Never trust client input"
        ]
    }

# ============================================================================
# ROOT & INFO ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """API overview"""
    return {
        "message": "Validations & Transformations Complete API",
        "documentation": "/docs",
        "sections": {
            "type_validation": {
                "endpoint": "POST /validation/type/book",
                "demo": "GET /validation/type/demo"
            },
            "syntactic_validation": {
                "endpoint": "POST /validation/syntactic/user"
            },
            "semantic_validation": {
                "person": "POST /validation/semantic/person",
                "event": "POST /validation/semantic/event"
            },
            "complex_validation": {
                "password_reset": "POST /validation/complex/password-reset",
                "employee": "POST /validation/complex/employee",
                "hotel_booking": "POST /validation/complex/hotel-booking"
            },
            "transformations": {
                "search_casting": "GET /transformation/search",
                "user_normalization": "POST /transformation/user",
                "product_computation": "POST /transformation/product"
            },
            "frontend_vs_backend": {
                "demo": "POST /validation/frontend-vs-backend",
                "philosophy": "GET /validation/philosophy"
            }
        },
        "tip": "Visit /docs for interactive testing!"
    }

@app.get("/validation/summary")
def validation_summary():
    """Summary of all validation types"""
    return {
        "validation_types": {
            "1_type": {
                "what": "Data matches expected type",
                "example_valid": {"name": "Alice", "age": 25},
                "example_invalid": {"name": "Alice", "age": "twenty-five"},
                "pydantic_solution": "Type hints (age: int)"
            },
            "2_syntactic": {
                "what": "Data follows specific format/pattern",
                "example_valid": {"email": "user@example.com"},
                "example_invalid": {"email": "not-an-email"},
                "pydantic_solution": "EmailStr, HttpUrl, field_validator with regex"
            },
            "3_semantic": {
                "what": "Data makes sense in real world",
                "example_valid": {"age": 25},
                "example_invalid": {"age": 430},
                "pydantic_solution": "Custom field_validator"
            },
            "4_complex": {
                "what": "Multi-field logic",
                "example_valid": {"password": "abc123", "confirm": "abc123"},
                "example_invalid": {"password": "abc123", "confirm": "different"},
                "pydantic_solution": "model_validator"
            }
        },
        "transformations": {
            "type_casting": "Query param '2' → int 2",
            "normalization": "User@Gmail.com → user@gmail.com",
            "computation": "price=100, discount=10% → final_price=90"
        },
        "golden_rules": [
            "Backend validation is MANDATORY (cannot trust frontend)",
            "Validate at entry point (before service/repository layer)",
            "Return 422 with clear error messages",
            "Transform data for consistency",
            "Design as if frontend validation doesn't exist"
        ]
    }

# ============================================================================
# RUN INSTRUCTIONS
# ============================================================================
"""
SETUP & RUN:
1. pip install "fastapi[standard]" pydantic[email]
2. fastapi dev validations_complete.py
3. Visit: http://127.0.0.1:8000/docs

TEST EXAMPLES:

# Type Validation
curl -X POST http://localhost:8000/validation/type/book \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "year": 1949,
    "price": 12.99,
    "tags": ["dystopian"],
    "available": true
  }'

# Type Validation Error (wrong type for year)
curl -X POST http://localhost:8000/validation/type/book \
  -H "Content-Type: application/json" \
  -d '{
    "title": "1984",
    "author": "George Orwell",
    "year": "nineteen forty-nine",
    "price": 12.99,
    "tags": ["dystopian"],
    "available": true
  }'

# Syntactic Validation
curl -X POST http://localhost:8000/validation/syntactic/user \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "website": "https://example.com",
    "phone": "+1-234-567-8900",
    "username": "john_doe",
    "password": "SecurePass123!",
    "zip_code": "12345"
  }'

# Semantic Validation
curl -X POST http://localhost:8000/validation/semantic/person \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John",
    "date_of_birth": "1990-01-01",
    "age": 34,
    "height_cm": 175.5,
    "weight_kg": 75.0
  }'

# Complex Validation (password match)
curl -X POST http://localhost:8000/validation/complex/password-reset \
  -H "Content-Type: application/json" \
  -d '{
    "password": "SecurePass123!",
    "password_confirmation": "SecurePass123!"
  }'

# Transformation (normalization)
curl -X POST http://localhost:8000/transformation/user \
  -H "Content-Type: application/json" \
  -d '{
    "email": "User@GMAIL.com",
    "username": "  JohnDoe  ",
    "first_name": "  john  ",
    "last_name": "  DOE  ",
    "phone": "(234) 567-8900"
  }'

# Type Casting (query params)
curl "http://localhost:8000/transformation/search?page=2&limit=20&ascending=false"

# Frontend Bypass Demo
curl -X POST http://localhost:8000/validation/frontend-vs-backend \
  -H "Content-Type: application/json" \
  -d '{
    "username": "a",
    "email": "not-email",
    "age": 5,
    "password": "weak",
    "agree_to_terms": false
  }'
"""
