"""
Complete Production-Grade Configuration Management - FastAPI
Demonstrates all concepts from Lecture 17:

1. The 5 categories of configurations
2. Environment-specific settings (dev, staging, prod)
3. Validation at startup
4. Security best practices
5. Storage strategies (.env, YAML, secrets manager)
6. Feature flags
7. Least privilege access
8. Hybrid fallback approach

Run with:
  fastapi dev config_management_complete.py

Install:
  pip install "fastapi[standard]" pydantic-settings pyyaml boto3

Setup:
  # Create .env file
  cp .env.example .env
  # Edit .env with your values
"""

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any
from enum import Enum
import os
import yaml
import json
import logging
from functools import lru_cache

# ============================================================================
# ENVIRONMENT ENUM
# ============================================================================

class Environment(str, Enum):
    """
    Environment types
    
    Each has different priorities:
    - DEV: Developer productivity, debugging
    - STAGING: Mirror prod, minimize cost
    - PROD: Reliability, security, performance
    """
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

# ============================================================================
# CONFIGURATION SETTINGS (PRODUCTION-GRADE)
# ============================================================================

class Settings(BaseSettings):
    """
    PRODUCTION-GRADE CONFIGURATION
    
    Critical features:
    1. ✅ Validation at startup (fail fast!)
    2. ✅ Type safety (Pydantic)
    3. ✅ Environment-specific defaults
    4. ✅ Clear documentation
    5. ✅ Secure secrets handling
    
    If ANY required field is missing → app won't start!
    This is GOOD! Fail at startup, not in production.
    """
    
    # ========================================================================
    # CATEGORY 1: APPLICATION SETTINGS
    # ========================================================================
    
    app_name: str = "My Production API"
    environment: Environment = Environment.DEVELOPMENT
    
    # Server settings
    port: int = Field(8000, ge=1024, le=65535)
    workers: int = Field(4, ge=1, le=32)
    timeout: int = Field(60, ge=1, le=300, description="Request timeout in seconds")
    
    # Logging
    log_level: str = Field("info", pattern="^(debug|info|warning|error|critical)$")
    
    # CORS
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    
    # ========================================================================
    # CATEGORY 2: DATABASE CONFIGS
    # ========================================================================
    
    database_url: str = Field(
        ...,  # Required!
        description="PostgreSQL connection string"
    )
    
    # Connection pool - environment-specific
    db_pool_size: Optional[int] = None  # Computed based on environment
    db_max_overflow: int = Field(20, ge=0)
    db_pool_timeout: int = Field(30, ge=1)
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v):
        """Ensure database URL is valid format"""
        if not v.startswith(('postgresql://', 'sqlite://', 'mysql://')):
            raise ValueError(
                'Database URL must start with postgresql://, sqlite://, or mysql://'
            )
        return v
    
    # ========================================================================
    # CATEGORY 3: EXTERNAL SERVICE CONFIGS
    # ========================================================================
    
    # Payment processing
    stripe_api_key: str = Field(
        ...,  # Required!
        description="Stripe API key (sk_test_* for dev, sk_live_* for prod)"
    )
    stripe_webhook_secret: Optional[str] = Field(
        None,
        description="Stripe webhook signing secret"
    )
    
    # Email service
    resend_api_key: Optional[str] = Field(None, description="Resend API key")
    
    # Authentication
    clerk_api_key: Optional[str] = Field(None, description="Clerk API key")
    
    # Cloud storage
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    aws_region: str = Field("us-east-1", description="AWS region")
    
    # ========================================================================
    # CATEGORY 4: FEATURE FLAGS
    # ========================================================================
    
    enable_new_checkout: bool = Field(
        False,
        description="Enable new checkout flow (A/B testing)"
    )
    
    enable_beta_features: bool = Field(
        False,
        description="Enable beta features for testing"
    )
    
    enable_analytics: bool = Field(
        True,
        description="Enable analytics tracking"
    )
    
    # Geographic features
    enable_eu_gdpr_mode: bool = Field(
        False,
        description="Enable GDPR-compliant mode for EU users"
    )
    
    # ========================================================================
    # CATEGORY 5: BUSINESS RULES & PERFORMANCE
    # ========================================================================
    
    # Session management
    session_timeout: int = Field(
        1800,
        ge=300,
        le=86400,
        description="Session timeout in seconds (default: 30 min)"
    )
    
    # Business limits
    max_order_amount: int = Field(
        100000,
        ge=1,
        description="Maximum order amount in cents (default: $1000)"
    )
    
    max_file_size_mb: int = Field(
        50,
        ge=1,
        le=1000,
        description="Maximum file upload size in MB"
    )
    
    # Caching
    cache_ttl: Optional[int] = None  # Computed based on environment
    
    # Rate limiting
    rate_limit_per_minute: int = Field(
        100,
        ge=1,
        description="API rate limit per minute"
    )
    
    # ========================================================================
    # SECURITY
    # ========================================================================
    
    jwt_secret: str = Field(
        ...,  # Required!
        min_length=32,
        description="JWT signing secret (min 32 chars)"
    )
    
    jwt_algorithm: str = Field("HS256", description="JWT signing algorithm")
    
    jwt_expiration_hours: int = Field(
        24,
        ge=1,
        le=720,
        description="JWT token expiration in hours"
    )
    
    # ========================================================================
    # COMPUTED PROPERTIES (ENVIRONMENT-SPECIFIC)
    # ========================================================================
    
    @property
    def computed_db_pool_size(self) -> int:
        """
        Database pool size varies by environment
        
        - DEV: Small pool (cheap, fewer connections)
        - STAGING: Minimal pool (mirror prod but minimize cost)
        - PROD: Large pool (handle heavy traffic)
        """
        if self.db_pool_size is not None:
            return self.db_pool_size
        
        return {
            Environment.DEVELOPMENT: 10,
            Environment.STAGING: 2,
            Environment.PRODUCTION: 50
        }[self.environment]
    
    @property
    def computed_cache_ttl(self) -> int:
        """
        Cache TTL varies by environment
        
        - DEV: Short TTL (see changes quickly)
        - STAGING: Medium TTL (balance testing/performance)
        - PROD: Long TTL (optimize performance)
        """
        if self.cache_ttl is not None:
            return self.cache_ttl
        
        return {
            Environment.DEVELOPMENT: 300,    # 5 minutes
            Environment.STAGING: 1800,       # 30 minutes
            Environment.PRODUCTION: 3600     # 1 hour
        }[self.environment]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == Environment.DEVELOPMENT
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    @field_validator('stripe_api_key')
    @classmethod
    def validate_stripe_key(cls, v, info):
        """
        Ensure Stripe key matches environment
        
        - DEV/STAGING: Must use test key (sk_test_*)
        - PROD: Must use live key (sk_live_*)
        """
        env = info.data.get('environment', Environment.DEVELOPMENT)
        
        if env == Environment.PRODUCTION:
            if not v.startswith('sk_live_'):
                raise ValueError(
                    'Production must use live Stripe key (sk_live_*)'
                )
        else:
            if not v.startswith('sk_test_'):
                raise ValueError(
                    'Development/Staging must use test Stripe key (sk_test_*)'
                )
        
        return v
    
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# ============================================================================
# SINGLETON PATTERN - LOAD ONCE
# ============================================================================

@lru_cache()
def get_settings() -> Settings:
    """
    Load settings (cached singleton)
    
    - Loaded once at startup
    - Validated immediately
    - Cached for entire app lifetime
    - If validation fails → app won't start!
    """
    return Settings()

# ============================================================================
# AWS SECRETS MANAGER INTEGRATION (OPTIONAL)
# ============================================================================

def get_aws_secret(secret_name: str) -> Dict[str, Any]:
    """
    Fetch secret from AWS Secrets Manager
    
    Use for production deployments:
    - Encrypted at rest
    - Encrypted in transit
    - Audit logs
    - Automatic rotation
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=secret_name)
        
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            raise ValueError("Binary secrets not supported")
            
    except ClientError as e:
        raise Exception(f"Failed to fetch secret: {e}")

# ============================================================================
# HYBRID FALLBACK STRATEGY
# ============================================================================

class HybridSettings(BaseSettings):
    """
    HYBRID CONFIGURATION STRATEGY
    
    Priority (fallback chain):
    1. AWS Secrets Manager (production)
    2. Environment variable (local/CI)
    3. Config file (defaults)
    
    This allows:
    - Secure secrets in production (AWS)
    - Simple .env files for local dev
    - Defaults in YAML config
    """
    
    environment: Environment = Environment.DEVELOPMENT
    
    def __init__(self, **kwargs):
        # Try AWS Secrets Manager first (production only)
        if os.getenv('ENVIRONMENT') == 'production':
            try:
                secret_name = os.getenv('AWS_SECRET_NAME', 'myapp/prod/secrets')
                aws_secrets = get_aws_secret(secret_name)
                kwargs.update(aws_secrets)
            except Exception as e:
                logging.warning(f"Failed to load AWS secrets: {e}")
        
        super().__init__(**kwargs)

# ============================================================================
# YAML CONFIG FILE SUPPORT
# ============================================================================

def load_yaml_config(file_path: str = "config.yaml") -> dict:
    """
    Load configuration from YAML file
    
    Benefits:
    - Supports comments (self-documenting)
    - Hierarchical structure
    - Human-readable
    
    Example config.yaml:
    
    app:
      name: "My API"
      # Port to run server on
      port: 8000
    
    database:
      # Connection pool size
      # Dev: 10, Staging: 2, Prod: 50
      pool_size: 10
    """
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, 'r') as f:
        return yaml.safe_load(f) or {}

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Configuration Management Complete API",
    description="Production-grade configuration with validation",
    version="1.0.0"
)

# ============================================================================
# STARTUP VALIDATION
# ============================================================================

@app.on_event("startup")
def startup_event():
    """
    VALIDATE CONFIGURATIONS AT STARTUP
    
    This is THE MOST IMPORTANT PATTERN!
    
    - If configs invalid → app won't start
    - Fail fast, fail loudly
    - No silent failures in production
    - No 3 AM pages for missing env var
    """
    try:
        settings = get_settings()
        
        logging.info("✅ Configuration validation passed")
        logging.info(f"   Environment: {settings.environment.value}")
        logging.info(f"   Database pool size: {settings.computed_db_pool_size}")
        logging.info(f"   Cache TTL: {settings.computed_cache_ttl}s")
        logging.info(f"   Log level: {settings.log_level}")
        
        # Verify critical services
        if settings.is_production:
            logging.info("   Running in PRODUCTION mode")
            if not settings.stripe_api_key.startswith('sk_live_'):
                raise ValueError("Production requires live Stripe key!")
        
    except Exception as e:
        logging.error(f"❌ Configuration validation FAILED: {e}")
        logging.error("   Application will not start!")
        raise

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/config/info")
def get_config_info(settings: Settings = Depends(get_settings)):
    """
    Get current configuration info (safe subset)
    
    ⚠️ NEVER expose secrets in API responses!
    """
    return {
        "environment": settings.environment.value,
        "app_name": settings.app_name,
        "application": {
            "port": settings.port,
            "workers": settings.workers,
            "timeout": settings.timeout,
            "log_level": settings.log_level,
        },
        "database": {
            "pool_size": settings.computed_db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "note": "Connection string hidden for security"
        },
        "performance": {
            "cache_ttl": settings.computed_cache_ttl,
            "rate_limit_per_minute": settings.rate_limit_per_minute
        },
        "feature_flags": {
            "new_checkout": settings.enable_new_checkout,
            "beta_features": settings.enable_beta_features,
            "analytics": settings.enable_analytics,
            "eu_gdpr_mode": settings.enable_eu_gdpr_mode
        },
        "business_rules": {
            "session_timeout": settings.session_timeout,
            "max_order_amount": settings.max_order_amount,
            "max_file_size_mb": settings.max_file_size_mb
        },
        "warning": "Secrets are hidden for security"
    }

@app.get("/config/validate")
def validate_config(settings: Settings = Depends(get_settings)):
    """
    Validate current configuration
    
    Returns validation status and any warnings
    """
    warnings = []
    
    # Check environment-specific rules
    if settings.is_production:
        if settings.log_level == "debug":
            warnings.append("Production using debug logging (performance impact!)")
        
        if settings.computed_db_pool_size < 20:
            warnings.append("Production pool size seems low (<20)")
        
        if not settings.stripe_webhook_secret:
            warnings.append("Stripe webhook secret not configured")
    
    if settings.is_development:
        if settings.computed_db_pool_size > 20:
            warnings.append("Dev pool size seems high (wasted resources)")
    
    return {
        "valid": True,
        "environment": settings.environment.value,
        "warnings": warnings if warnings else None,
        "message": "Configuration is valid" if not warnings else "Configuration valid with warnings"
    }

@app.get("/features/{feature_name}")
def check_feature(
    feature_name: str,
    settings: Settings = Depends(get_settings)
):
    """
    FEATURE FLAGS DEMO
    
    Check if a feature is enabled
    
    Benefits:
    - Deploy code without activating feature
    - A/B test on subset of users
    - Instant rollback (no deploy)
    - Toggle without code changes
    """
    features = {
        "new_checkout": settings.enable_new_checkout,
        "beta_features": settings.enable_beta_features,
        "analytics": settings.enable_analytics,
        "eu_gdpr": settings.enable_eu_gdpr_mode
    }
    
    if feature_name not in features:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    return {
        "feature": feature_name,
        "enabled": features[feature_name],
        "environment": settings.environment.value,
        "note": "Feature flags allow instant toggle without deployment"
    }

@app.get("/demo/environment-differences")
def show_environment_differences():
    """
    ENVIRONMENT-SPECIFIC CONFIGS DEMO
    
    Shows how same codebase behaves differently per environment
    """
    return {
        "principle": "Same codebase, different behavior via configs",
        "environments": {
            "development": {
                "priority": "Developer productivity & debugging",
                "db_pool_size": 10,
                "log_level": "debug",
                "stripe_key": "sk_test_* (test mode)",
                "cache_ttl": "300s (5 min)",
                "resources": "Small (cheap)"
            },
            "staging": {
                "priority": "Mirror production + minimize costs",
                "db_pool_size": 2,
                "log_level": "info",
                "stripe_key": "sk_test_* (still test!)",
                "cache_ttl": "1800s (30 min)",
                "resources": "Minimal (cost control)"
            },
            "production": {
                "priority": "Reliability, security, performance",
                "db_pool_size": 50,
                "log_level": "warn",
                "stripe_key": "sk_live_* (REAL MONEY!)",
                "cache_ttl": "3600s (1 hour)",
                "resources": "Large (handle traffic)"
            }
        },
        "note": "Your current environment determines which configs are active"
    }

@app.get("/demo/security-practices")
def show_security_practices():
    """
    SECURITY BEST PRACTICES
    
    Critical rules for production
    """
    return {
        "security_rules": {
            "1_never_hardcode": {
                "rule": "Never hardcode secrets in code",
                "wrong": "STRIPE_KEY = 'sk_live_abc123'",
                "correct": "STRIPE_KEY = os.getenv('STRIPE_API_KEY')"
            },
            "2_validate_startup": {
                "rule": "Validate all configs at startup",
                "benefit": "Fail fast (before serving traffic), not in production",
                "implementation": "Pydantic Settings with required fields"
            },
            "3_least_privilege": {
                "rule": "Only access what you need",
                "frontend_dev": "Can see: NEXT_PUBLIC_* only",
                "backend_dev": "Can see: API keys, database configs",
                "devops": "Can see: Everything (infrastructure)"
            },
            "4_rotate_secrets": {
                "rule": "Rotate secrets regularly",
                "frequency": "Monthly or quarterly",
                "tools": "AWS Secrets Manager (auto-rotation)"
            },
            "5_encrypt_storage": {
                "rule": "Encrypt secrets at rest and in transit",
                "dev": ".env files (not encrypted, but git-ignored)",
                "prod": "AWS Secrets Manager (encrypted both ways)"
            },
            "6_audit_logs": {
                "rule": "Track who accesses secrets when",
                "tools": "CloudTrail, AWS IAM logs"
            }
        }
    }

@app.get("/")
def root():
    return {
        "message": "Configuration Management Complete API",
        "documentation": "/docs",
        "config_categories": {
            "1_application": "Port, workers, timeout, logging",
            "2_database": "URL, pool size, connection limits",
            "3_external_services": "Stripe, Resend, Clerk, AWS",
            "4_feature_flags": "A/B testing, rollout control",
            "5_business_rules": "Session timeout, order limits"
        },
        "endpoints": {
            "config_info": "GET /config/info",
            "validate": "GET /config/validate",
            "feature_check": "GET /features/{feature_name}",
            "environment_diff": "GET /demo/environment-differences",
            "security": "GET /demo/security-practices"
        },
        "key_principle": "Same codebase, different behavior via environment-specific configs"
    }

# ============================================================================
# EXAMPLE .ENV FILE
# ============================================================================

"""
# .env.example
# Copy this to .env and fill in your values

# Environment
ENVIRONMENT=development

# Application
APP_NAME=My API
PORT=8000
LOG_LEVEL=debug

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb
DB_POOL_SIZE=10

# External Services
STRIPE_API_KEY=sk_test_your_key_here
RESEND_API_KEY=re_your_key_here

# Security
JWT_SECRET=your-super-secret-jwt-key-at-least-32-characters-long

# Feature Flags
ENABLE_NEW_CHECKOUT=false
ENABLE_BETA_FEATURES=false

# Business Rules
MAX_ORDER_AMOUNT=100000
SESSION_TIMEOUT=1800

# CORS
ALLOWED_ORIGINS=["http://localhost:3000"]
"""

# ============================================================================
# TEST COMMANDS
# ============================================================================
"""
SETUP:
  # Install
  pip install "fastapi[standard]" pydantic-settings pyyaml boto3
  
  # Create .env file
  cat > .env << EOF
ENVIRONMENT=development
DATABASE_URL=postgresql://localhost/mydb
STRIPE_API_KEY=sk_test_123456
JWT_SECRET=super-secret-key-that-is-at-least-32-chars-long
EOF
  
  # Run
  fastapi dev config_management_complete.py

TESTS:

1. View current config:
   curl http://localhost:8000/config/info
   
   # Shows environment-specific values (pool size, cache TTL, etc.)

2. Validate config:
   curl http://localhost:8000/config/validate
   
   # Checks for warnings based on environment

3. Check feature flag:
   curl http://localhost:8000/features/new_checkout
   
   # Returns: {"feature": "new_checkout", "enabled": false}

4. Test validation (missing required field):
   # Remove DATABASE_URL from .env
   # Restart server
   # Server won't start! "Field required: database_url"

5. Test environment-specific behavior:
   # In .env: ENVIRONMENT=development → pool_size=10
   # In .env: ENVIRONMENT=staging → pool_size=2
   # In .env: ENVIRONMENT=production → pool_size=50

KEY INSIGHTS:

The 5 Config Categories:
  1. Application: Port, workers, logging
  2. Database: Connection, pool size
  3. External: API keys (Stripe, AWS, etc.)
  4. Feature flags: A/B testing, rollouts
  5. Business: Timeouts, limits, rules

Validate at Startup (CRITICAL!):
  ✅ Use Pydantic Settings
  ✅ Mark required fields with ...
  ✅ App won't start if missing
  ✅ Fail fast, not in production

Environment-Specific:
  Dev: Small resources, verbose logging, test keys
  Staging: Mirror prod, minimal resources, test keys
  Prod: Large resources, minimal logging, LIVE keys

Security:
  ❌ Never hardcode secrets
  ✅ Validate at startup
  ✅ Least privilege access
  ✅ Rotate secrets regularly
  ✅ Use secrets manager in prod
  ✅ Encrypt at rest + in transit

Storage Strategy:
  Dev: .env files (simple)
  Staging: .env or Parameter Store
  Prod: AWS Secrets Manager (encrypted, audited)

Feature Flags:
  Deploy code → Feature disabled
  Enable for 10% → Test
  Enable for 100% → Full rollout
  Instant rollback → Just toggle flag (no deploy!)
"""
