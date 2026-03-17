# Lecture 17: Production-Grade Configuration Management - FastAPI Mapping

## 📚 Lecture Overview

**Topic**: Configuration Management - The DNA of Your Application  
**Date Started**: 2026-01-29  
**Status**: 🟡 In Progress

---

## 🎯 Core Philosophy from Your Lecture

> **"Configuration management is the DNA of your application. It's not just about hiding database passwords — that narrow view is like saying a car is just about the engine."**

### **The Real Scope**

Configuration management is the **systematic approach** to organizing, storing, and accessing ALL settings that dictate how your backend runs.

---

## 📋 The 5 Categories of Configurations

### **1. Application Settings**

**What:** Core operational metrics

**Examples:**
```python
# Server settings
PORT = 8000
TIMEOUT = 60  # Drop request after 60 seconds
WORKERS = 4   # Number of worker processes

# Logging
LOG_LEVEL = "debug"  # dev
LOG_LEVEL = "info"   # production

# CORS
ALLOWED_ORIGINS = ["http://localhost:3000"]  # dev
ALLOWED_ORIGINS = ["https://myapp.com"]      # production
```

---

### **2. Database Configs**

**What:** Connection parameters and performance tuning

**Examples:**
```python
# Connection string
DATABASE_URL = "postgresql://user:pass@host:5432/dbname"

# Performance tuning
DB_POOL_SIZE = 10   # dev: small pool
DB_POOL_SIZE = 50   # prod: large pool for traffic

DB_MAX_OVERFLOW = 20
DB_POOL_TIMEOUT = 30
```

**Why pool size differs:**
- **Dev:** Small pool (10) = fewer connections, cheaper
- **Staging:** Minimal pool (2) = mirror prod but minimize cost
- **Prod:** Large pool (50) = handle heavy user traffic

---

### **3. External Service Configs**

**What:** API keys for third-party services

**Examples:**
```python
# Payment processing
STRIPE_API_KEY = "sk_test_..."      # dev
STRIPE_API_KEY = "sk_live_..."      # production

# Authentication
CLERK_API_KEY = "..."

# Email
RESEND_API_KEY = "..."

# Cloud storage
AWS_ACCESS_KEY = "..."
AWS_SECRET_KEY = "..."
```

**Security:** These MUST be in environment variables or secrets manager, NEVER hardcoded!

---

### **4. Feature Flags**

**What:** Dynamic toggles to enable/disable features

**Examples:**
```python
# A/B testing
NEW_CHECKOUT_ENABLED = False  # Default
NEW_CHECKOUT_ENABLED = True   # For beta users

# Geographic features
ENABLE_EU_GDPR_MODE = True   # EU users
ENABLE_EU_GDPR_MODE = False  # US users

# Rollout strategy
ENABLE_NEW_DASHBOARD = True   # 10% of users
ENABLE_NEW_DASHBOARD = True   # 50% of users (ramp up)
ENABLE_NEW_DASHBOARD = True   # 100% (full rollout)
```

**Benefits:**
- Deploy code without activating feature
- Test on subset of users
- Instant rollback if issues
- No code deploy needed to toggle

---

### **5. Business Rules & Performance**

**What:** Domain-specific settings

**Examples:**
```python
# Session management
SESSION_TIMEOUT = 1800  # 30 minutes

# Business limits
MAX_ORDER_AMOUNT = 10000  # $100.00 in cents
MAX_FILE_SIZE_MB = 50

# Performance
CACHE_TTL = 300        # 5 minutes dev
CACHE_TTL = 3600       # 1 hour prod

CPU_INTENSIVE_WORKERS = 2   # dev
CPU_INTENSIVE_WORKERS = 16  # prod
```

---

## ⚠️ The Problem: Configuration Chaos

**What happens without proper config management:**

### **1. Hard-Coded Values Scattered Everywhere**

```python
# ❌ BAD: Hard-coded throughout codebase
@app.get("/checkout")
def checkout():
    timeout = 60  # Hardcoded!
    stripe_key = "sk_live_xyz"  # Hardcoded secret!
    max_amount = 10000  # Hardcoded business rule!
```

**Problems:**
- Can't change without redeploying
- Same value duplicated 50 places
- Secrets in version control
- Nightmare to maintain

### **2. Inconsistent Behavior Across Environments**

```python
# ❌ BAD: Different code in dev vs prod
if environment == "production":
    pool_size = 50
else:
    pool_size = 10

# Prod bug that doesn't reproduce in dev!
```

### **3. Security Vulnerabilities**

```python
# ❌ BAD: Secret in code
DATABASE_URL = "postgresql://admin:MyP@ssw0rd@db.company.com/prod"

# Committed to GitHub → secret leaked!
# Attacker has full database access!
```

### **4. Frontend vs Backend Impact**

**Misconfigured Frontend:**
- Broken UI element
- User sees error message
- Annoying, but contained

**Misconfigured Backend:**
- Expose sensitive customer data 💀
- Process payments incorrectly 💸
- Bring down entire platform 🔥
- Legal liability (GDPR violations) ⚖️

**Backend misconfigurations have catastrophic consequences!**

---

## 🌍 Environment-Specific Configurations

### **Core Principle:**

> **"Your codebase remains exactly the same across all deployments, but its behavior changes based on environment-specific configurations."**

### **The 3 Environments**

#### **Development (Local)**

**Priority:** Developer productivity & debugging

```python
# dev.env
PORT=8000
LOG_LEVEL=debug           # Verbose logging
DB_POOL_SIZE=10           # Small pool
STRIPE_API_KEY=sk_test_*  # Test mode
ENABLE_DEBUG_TOOLBAR=true
ALLOWED_ORIGINS=http://localhost:3000
```

**Characteristics:**
- Verbose logging (see everything)
- Test API keys (don't charge real cards)
- Relaxed security (easier debugging)
- Small resource allocation (cheap)

---

#### **Staging**

**Priority:** Mirror production + minimize costs

```python
# staging.env
PORT=8000
LOG_LEVEL=info            # Production-like
DB_POOL_SIZE=2            # MINIMAL (cost control!)
STRIPE_API_KEY=sk_test_*  # Still test mode
ENABLE_DEBUG_TOOLBAR=false
ALLOWED_ORIGINS=https://staging.myapp.com
```

**Characteristics:**
- Production-like behavior
- Test API keys (catch integration bugs safely)
- Minimal resources (staging is expensive!)
- Catches bugs before production

---

#### **Production**

**Priority:** Reliability, security, performance

```python
# production.env
PORT=443
LOG_LEVEL=warn            # Only warnings/errors
DB_POOL_SIZE=50           # Large pool (handle traffic!)
STRIPE_API_KEY=sk_live_*  # LIVE MODE (real money!)
ENABLE_DEBUG_TOOLBAR=false
ALLOWED_ORIGINS=https://myapp.com
RATE_LIMIT=1000           # Strict limits
```

**Characteristics:**
- Minimal logging (reduce noise)
- Live API keys (real transactions)
- Maximum resources (performance!)
- Strict security (every edge case handled)

---

## 🗄️ Storage Strategies

### **1. Environment Variables (.env files)**

**Use for:** Local development

```bash
# .env (local development)
DATABASE_URL=postgresql://localhost/mydb
STRIPE_API_KEY=sk_test_123
LOG_LEVEL=debug
```

**Pros:**
- Simple, standard practice
- Easy to read/edit
- Git-ignored (not committed)

**Cons:**
- Not encrypted
- Not suitable for production
- Manual management

---

### **2. Configuration Files (YAML/TOML)**

**Use for:** Complex configs with comments

```yaml
# config.yaml
app:
  name: "My API"
  port: 8000
  # Timeout in seconds
  timeout: 60

database:
  # Connection pool size
  # Dev: 10, Staging: 2, Prod: 50
  pool_size: 10
  url: ${DATABASE_URL}  # Still use env var for secret!

features:
  new_checkout: false
  beta_features: true
```

**Pros:**
- Supports comments (self-documenting)
- Hierarchical structure
- Type-safe with validation

**Cons:**
- Still not encrypted
- Requires parsing library

---

### **3. Cloud Secrets Managers (Production)**

**Use for:** Production deployments

**Options:**
- AWS Parameter Store
- AWS Secrets Manager
- HashiCorp Vault
- Google Secret Manager
- Azure Key Vault

**Example: AWS Parameter Store**
```python
import boto3

def get_secret(name):
    """Fetch secret from AWS Parameter Store"""
    client = boto3.client('ssm')
    response = client.get_parameter(
        Name=name,
        WithDecryption=True  # Auto-decrypt
    )
    return response['Parameter']['Value']

# Usage
DATABASE_URL = get_secret('/myapp/prod/database-url')
STRIPE_KEY = get_secret('/myapp/prod/stripe-api-key')
```

**Benefits:**
- ✅ Encrypted at rest (in storage)
- ✅ Encrypted in transit (when fetching)
- ✅ Audit logs (who accessed when)
- ✅ Automatic rotation
- ✅ Fine-grained permissions (IAM)
- ✅ No secrets in code/containers

**Costs:** Small fee (worth it for security!)

---

### **4. Hybrid Approach (Recommended)**

**Pattern:** Fallback hierarchy

```python
def get_config(key: str) -> str:
    """
    HYBRID FALLBACK STRATEGY
    
    Priority:
    1. Cloud secrets manager (production)
    2. Environment variable (local/CI)
    3. Config file (defaults)
    """
    # Try AWS Parameter Store first (production)
    try:
        return get_aws_secret(f"/myapp/{ENV}/{key}")
    except:
        pass
    
    # Fallback to environment variable
    value = os.getenv(key)
    if value:
        return value
    
    # Fallback to config file
    return config_file.get(key)
```

---

## 🔒 Security Best Practices

### **1. Never Hardcode Secrets**

```python
# ❌ WRONG: Secret in code
STRIPE_KEY = "sk_live_abc123"

# ✅ CORRECT: Secret in environment
STRIPE_KEY = os.getenv("STRIPE_API_KEY")
```

---

### **2. Implement Least Privilege**

**Principle:** Only access what you need

```
Frontend Developer:
  ✅ Can see: NEXT_PUBLIC_* variables
  ❌ Cannot see: Database passwords, API keys

Backend Developer:
  ✅ Can see: Database configs, API keys
  ❌ Cannot see: AWS infrastructure secrets

DevOps Team:
  ✅ Can see: Everything (infrastructure, security)
  ❌ Only team with full access
```

**Implementation (AWS IAM):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:*:*:parameter/myapp/backend/*"
    }
  ]
}
```

**Result:** Backend dev can only access `/myapp/backend/*` configs!

---

### **3. Rotate Secrets Regularly**

**Why:** If leaked, old secrets become invalid

**Strategy:**
```python
# JWT secrets
JWT_SECRET = "secret-v1"  # Month 1
JWT_SECRET = "secret-v2"  # Month 2 (rotate)

# Support both during transition
def verify_token(token):
    try:
        return jwt.decode(token, JWT_SECRET_V2)
    except:
        # Fallback to old secret (grace period)
        return jwt.decode(token, JWT_SECRET_V1)
```

**Tools:**
- AWS Secrets Manager (auto-rotation)
- Rotate monthly or quarterly
- Immediate rotation if suspected leak

---

### **4. Validate at Startup (MOST CRITICAL!)**

> **"The most important rule: Your application must validate ALL configurations the moment it boots up."**

**❌ WRONG: Discover missing config in production**
```python
@app.get("/checkout")
def checkout():
    stripe_key = os.getenv("STRIPE_API_KEY")  # None!
    # Crashes when user tries to checkout
    # User sees error, you get paged at 3 AM
```

**✅ CORRECT: Validate at startup**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    VALIDATE ALL CONFIGS AT STARTUP
    
    If any required config is missing → app won't start!
    Fail fast, fail loudly, fail at startup (not in production)
    """
    database_url: str
    stripe_api_key: str
    jwt_secret: str
    log_level: str = "info"  # Optional with default
    
    class Config:
        env_file = ".env"

# This raises ValidationError if anything missing
settings = Settings()

# Now safe to use!
stripe.api_key = settings.stripe_api_key
```

**Benefits:**
- ✅ Fail immediately (before serving traffic)
- ✅ Clear error message (which config missing)
- ✅ No silent failures in production
- ✅ No 3 AM pages for missing env var

---

## 💡 FastAPI Implementation Patterns

### **Pattern 1: Simple Environment Variables**

```python
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Access configs
DATABASE_URL = os.getenv("DATABASE_URL")
STRIPE_KEY = os.getenv("STRIPE_API_KEY")

# Problem: No validation! Could be None
```

---

### **Pattern 2: Pydantic Settings (Recommended)**

```python
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    """
    Production-grade configuration with validation
    """
    # Application
    app_name: str = "My API"
    port: int = 8000
    log_level: str = Field("info", pattern="^(debug|info|warn|error)$")
    
    # Database
    database_url: str
    db_pool_size: int = Field(10, ge=1, le=100)
    
    # External services
    stripe_api_key: str
    stripe_webhook_secret: str
    
    # Feature flags
    enable_new_checkout: bool = False
    
    # Security
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    
    # Validators
    @validator('database_url')
    def validate_db_url(cls, v):
        if not v.startswith(('postgresql://', 'sqlite://')):
            raise ValueError('Invalid database URL')
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Validate at startup
settings = Settings()
```

---

### **Pattern 3: Environment-Specific Configs**

```python
import os
from enum import Enum

class Environment(str, Enum):
    DEV = "development"
    STAGING = "staging"
    PROD = "production"

class Settings(BaseSettings):
    environment: Environment = Environment.DEV
    
    # Database pool size varies by environment
    @property
    def db_pool_size(self) -> int:
        return {
            Environment.DEV: 10,
            Environment.STAGING: 2,
            Environment.PROD: 50
        }[self.environment]
    
    # Log level varies by environment
    @property
    def log_level(self) -> str:
        return {
            Environment.DEV: "debug",
            Environment.STAGING: "info",
            Environment.PROD: "warn"
        }[self.environment]

settings = Settings()
```

---

### **Pattern 4: AWS Secrets Manager Integration**

```python
import boto3
from functools import lru_cache

@lru_cache()
def get_aws_secret(secret_name: str) -> dict:
    """Fetch secret from AWS Secrets Manager (cached)"""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

class Settings(BaseSettings):
    environment: str
    aws_secret_name: str = "myapp/prod/secrets"
    
    @property
    def database_url(self) -> str:
        if self.environment == "production":
            secrets = get_aws_secret(self.aws_secret_name)
            return secrets['database_url']
        return os.getenv("DATABASE_URL")
```

---

## 🔗 FastAPI Documentation Mapping

| Your Lecture Concept | FastAPI Feature | FastAPI Docs | Notes |
|---------------------|-----------------|--------------|-------|
| **Environment Variables** | `os.getenv()` | [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/) | Standard Python approach |
| **Pydantic Settings** | `pydantic-settings` | [Settings Management](https://fastapi.tiangolo.com/advanced/settings/#pydantic-settings) | Recommended for FastAPI |
| **Config Validation** | `BaseSettings` | [Settings Validation](https://fastapi.tiangolo.com/advanced/settings/#settings-in-a-dependency) | Automatic type checking |
| **Environment-specific configs** | `.env` files | [.env file support](https://fastapi.tiangolo.com/advanced/settings/#reading-a-env-file) | Built into pydantic-settings |
| **Dependency Injection** | `Depends()` | [Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) | Inject settings into endpoints |
| **Settings as Dependency** | `@lru_cache` | [Settings in a Dependency](https://fastapi.tiangolo.com/advanced/settings/#settings-in-a-dependency) | Singleton pattern |
| **Secrets Management** | External integration | [Security](https://fastapi.tiangolo.com/tutorial/security/) | Integrate AWS/Vault |
| **CORS Configuration** | `CORSMiddleware` | [CORS](https://fastapi.tiangolo.com/tutorial/cors/) | allowed_origins from config |
| **Startup Events** | `@app.on_event("startup")` | [Events: startup - shutdown](https://fastapi.tiangolo.com/advanced/events/) | Validate configs on startup |

### **Key FastAPI Patterns**

**Pattern 1: Basic Settings (FastAPI Docs)**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "My API"
    admin_email: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```
[FastAPI Settings Guide](https://fastapi.tiangolo.com/advanced/settings/)

**Pattern 2: Settings as Dependency (Recommended)**
```python
from functools import lru_cache

@lru_cache()
def get_settings():
    return Settings()

@app.get("/info")
def info(settings: Settings = Depends(get_settings)):
    return {"app_name": settings.app_name}
```
[Settings in a Dependency](https://fastapi.tiangolo.com/advanced/settings/#settings-in-a-dependency)

**Pattern 3: Environment-Specific Files**
```python
class Settings(BaseSettings):
    class Config:
        # Load .env.production in production
        env_file = f".env.{os.getenv('ENV', 'development')}"
```

**Pattern 4: Startup Validation**
```python
@app.on_event("startup")
def validate_configs():
    settings = get_settings()
    # Settings() will raise ValidationError if invalid
    logger.info(f"✅ Configs validated: {settings.app_name}")
```
[Startup Events](https://fastapi.tiangolo.com/advanced/events/#startup-event)

---

## 🎓 Mastery Checklist

- [ ] List the 5 categories of configurations?
- [ ] Explain why config management is critical for backends?
- [ ] Understand environment-specific priorities (dev, staging, prod)?
- [ ] Use .env files for local development?
- [ ] Validate configs at startup with Pydantic?
- [ ] Never hardcode secrets in code?
- [ ] Implement least privilege access?
- [ ] Rotate secrets regularly?
- [ ] Use cloud secrets managers for production?
- [ ] Implement hybrid fallback strategy?
- [ ] Understand feature flags?
- [ ] Configure different pool sizes per environment?

---

## 📍 Configuration in the Architecture

```
Application Startup
    ↓
Load & Validate Configurations
    ├─ Try AWS Secrets Manager (production)
    ├─ Fallback to environment variables
    └─ Fallback to config file
    ↓
Validation (Pydantic)
    ├─ All required fields present?
    ├─ Correct types?
    └─ Valid formats?
    ↓
❌ FAIL → Application won't start (good!)
✅ PASS → Start server
    ↓
Use configurations throughout app
    ├─ Database connection
    ├─ External API calls
    ├─ Feature flags
    └─ Business rules
```

---

**Last Updated**: 2026-01-29  
**Status**: ✅ Mapping Complete  
**Practice File**: config_management_complete.py (next)