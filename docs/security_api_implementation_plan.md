# Security-Focused API Implementation Plan for ClassicLib

**Version**: 1.0
**Date**: 2025-09-21
**Purpose**: Create a secure API layer for ClassicLib that enables safe web deployment while maintaining desktop functionality

## Executive Summary

This plan outlines the implementation of a security-focused API layer (`ClassicAPI`) that wraps the existing ClassicLib functionality with proper security controls. The design maintains backward compatibility for desktop applications while providing a secure interface for web deployment.

### Core Principles
1. **Zero-Trust Architecture** - Never trust input, always verify
2. **Defense in Depth** - Multiple security layers
3. **Principle of Least Privilege** - Minimal permissions
4. **Separation of Concerns** - Desktop vs Web security models
5. **Backward Compatibility** - Desktop apps continue working unchanged

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Web Clients                          │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS + JWT
┌────────────────────▼────────────────────────────────────┐
│              ClassicAPI (Security Layer)                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  • Authentication & Authorization                │  │
│  │  • Input Validation & Sanitization              │  │
│  │  • Rate Limiting & Resource Management          │  │
│  │  • Audit Logging & Monitoring                   │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │ Validated Calls
┌────────────────────▼────────────────────────────────────┐
│              ClassicLib (Core Library)                  │
│         Modified with Security Enhancements             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│    Desktop Apps (Direct Access - Unchanged)             │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 1: Core Library Security Enhancements (Week 1-2)

### 1.1 Create Security Configuration Module

**File**: `ClassicLib/Security/config.py`

```python
from enum import Enum
from pathlib import Path
from typing import Optional, List
import os

class ExecutionContext(Enum):
    DESKTOP = "desktop"
    WEB_API = "web_api"

class SecurityConfig:
    """Global security configuration for ClassicLib"""

    def __init__(self, context: ExecutionContext = ExecutionContext.DESKTOP):
        self.context = context
        self.sandbox_enabled = context == ExecutionContext.WEB_API
        self.allowed_paths: List[Path] = []
        self.forbidden_paths: List[Path] = []
        self.allowed_executables: List[str] = []
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.enable_sql_validation = context == ExecutionContext.WEB_API

    def is_web_context(self) -> bool:
        return self.context == ExecutionContext.WEB_API

    def is_desktop_context(self) -> bool:
        return self.context == ExecutionContext.DESKTOP

# Global singleton
_security_config: Optional[SecurityConfig] = None

def get_security_config() -> SecurityConfig:
    global _security_config
    if _security_config is None:
        # Default to desktop for backward compatibility
        _security_config = SecurityConfig(ExecutionContext.DESKTOP)
    return _security_config

def set_security_context(context: ExecutionContext):
    global _security_config
    _security_config = SecurityConfig(context)
```

### 1.2 Implement Secure Database Layer

**File**: `ClassicLib/Security/database.py`

```python
from typing import Any, Dict, List, Optional
import sqlite3
from pathlib import Path

class SecureDatabase:
    """Secure database wrapper with SQL injection prevention"""

    # Whitelist of allowed table names
    ALLOWED_TABLES = {
        'Fallout4', 'SkyrimSE', 'Fallout4VR', 'SkyrimVR',
        'settings', 'cache', 'metadata'
    }

    # Whitelist of allowed operations
    ALLOWED_OPERATIONS = {
        'SELECT', 'INSERT', 'UPDATE', 'DELETE'
    }

    def __init__(self, db_path: Path, readonly: bool = False):
        self.db_path = db_path
        self.readonly = readonly
        self.connection: Optional[sqlite3.Connection] = None

    def validate_table_name(self, table: str) -> str:
        """Validate table name against whitelist"""
        if table not in self.ALLOWED_TABLES:
            raise ValueError(f"Invalid table name: {table}")
        return table

    def validate_column_names(self, columns: List[str]) -> List[str]:
        """Validate column names to prevent injection"""
        import re
        pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

        for col in columns:
            if not pattern.match(col):
                raise ValueError(f"Invalid column name: {col}")
        return columns

    async def execute_query(
        self,
        query_template: str,
        params: tuple = (),
        table_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute parameterized query with validation"""

        # If table name is dynamic, validate it first
        if table_name:
            table_name = self.validate_table_name(table_name)
            # Replace placeholder with validated table name
            query = query_template.replace("{table}", table_name)
        else:
            query = query_template

        # Execute with parameters (prevents SQL injection in values)
        cursor = self.connection.execute(query, params)

        # Convert to dict format
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self):
        if self.connection:
            self.connection.close()
```

### 1.3 Path Validation Module

**File**: `ClassicLib/Security/path_validator.py`

```python
from pathlib import Path
from typing import Optional, List
import os

class PathValidator:
    """Centralized path validation to prevent traversal attacks"""

    def __init__(self, sandbox_root: Optional[Path] = None):
        self.sandbox_root = sandbox_root
        self.forbidden_patterns = [
            '.ssh', '.aws', '.config', '.gnupg',
            'System32', 'Windows', '/etc', '/usr/bin'
        ]

    def is_safe_path(self, path: Path, base_path: Optional[Path] = None) -> bool:
        """Validate path is safe to access"""

        # Resolve to absolute path
        resolved = path.resolve()

        # Check if path exists (prevents some TOCTOU issues)
        if not resolved.exists():
            return False

        # Check against forbidden patterns
        path_str = str(resolved).lower()
        for forbidden in self.forbidden_patterns:
            if forbidden.lower() in path_str:
                return False

        # If base_path provided, ensure path is within it
        if base_path:
            base_resolved = base_path.resolve()
            try:
                resolved.relative_to(base_resolved)
            except ValueError:
                # Path is outside base_path
                return False

        # If sandboxed, ensure within sandbox
        if self.sandbox_root:
            try:
                resolved.relative_to(self.sandbox_root)
            except ValueError:
                return False

        return True

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal"""
        import re

        # Remove any path components
        filename = os.path.basename(filename)

        # Remove dangerous characters
        filename = re.sub(r'[^\w\s\-\.]', '', filename)

        # Prevent double extensions that might bypass filters
        parts = filename.split('.')
        if len(parts) > 2:
            # Keep only last extension
            filename = '.'.join(parts[:-1]).replace('.', '_') + '.' + parts[-1]

        return filename

    def create_safe_path(self, base: Path, user_input: str) -> Optional[Path]:
        """Create a safe path from user input"""

        # Sanitize the input
        safe_name = self.sanitize_filename(user_input)

        # Construct path
        target = base / safe_name

        # Validate it's safe
        if self.is_safe_path(target, base):
            return target

        return None
```

### 1.4 Input Sanitization Module

**File**: `ClassicLib/Security/sanitizer.py`

```python
import re
import html
from typing import Any, Dict, List, Union
import json

class InputSanitizer:
    """Comprehensive input sanitization for web inputs"""

    def __init__(self):
        self.max_string_length = 10000
        self.allowed_html_tags = []  # No HTML allowed by default

    def sanitize_string(self, value: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise TypeError("Expected string input")

        # Limit length
        max_len = max_length or self.max_string_length
        value = value[:max_len]

        # Remove null bytes
        value = value.replace('\x00', '')

        # Escape HTML
        value = html.escape(value)

        # Remove control characters
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')

        return value

    def sanitize_path_component(self, component: str) -> str:
        """Sanitize a path component"""
        # Remove directory traversal attempts
        component = component.replace('..', '')
        component = component.replace('/', '')
        component = component.replace('\\', '')

        # Remove special characters
        component = re.sub(r'[^\w\-\.]', '', component)

        return component

    def sanitize_sql_identifier(self, identifier: str) -> str:
        """Sanitize SQL identifier (table/column name)"""
        # Only allow alphanumeric and underscore
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            raise ValueError(f"Invalid SQL identifier: {identifier}")

        # Limit length
        if len(identifier) > 64:
            raise ValueError(f"SQL identifier too long: {identifier}")

        return identifier

    def sanitize_json(self, data: Union[str, dict]) -> dict:
        """Sanitize JSON input"""
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON input")

        if not isinstance(data, dict):
            raise TypeError("Expected JSON object")

        # Recursively sanitize all string values
        def clean_dict(d: dict) -> dict:
            cleaned = {}
            for key, value in d.items():
                # Sanitize key
                clean_key = self.sanitize_string(str(key), 100)

                # Sanitize value based on type
                if isinstance(value, str):
                    cleaned[clean_key] = self.sanitize_string(value)
                elif isinstance(value, dict):
                    cleaned[clean_key] = clean_dict(value)
                elif isinstance(value, list):
                    cleaned[clean_key] = [
                        self.sanitize_string(v) if isinstance(v, str) else v
                        for v in value[:1000]  # Limit array size
                    ]
                else:
                    cleaned[clean_key] = value

            return cleaned

        return clean_dict(data)
```

---

## Phase 2: API Layer Implementation (Week 2-3)

### 2.1 API Security Core

**File**: `ClassicAPI/core/security.py`

```python
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib
import hmac

class RateLimiter:
    """Rate limiting implementation"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[datetime]] = {}

    async def check_rate_limit(self, client_id: str) -> bool:
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        if client_id not in self.requests:
            self.requests[client_id] = []

        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]

        # Check limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False

        # Add current request
        self.requests[client_id].append(now)
        return True

class JWTAuthenticator:
    """JWT-based authentication"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.bearer = HTTPBearer()

    def create_token(self, user_id: str, permissions: List[str]) -> str:
        """Create JWT token"""
        payload = {
            "user_id": user_id,
            "permissions": permissions,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    async def verify_token(self, credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        token = credentials.credentials

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

class RequestValidator:
    """Validate incoming API requests"""

    def __init__(self):
        self.max_body_size = 10 * 1024 * 1024  # 10MB

    async def validate_request_size(self, request: Request):
        """Check request body size"""
        content_length = request.headers.get("content-length")

        if content_length:
            if int(content_length) > self.max_body_size:
                raise HTTPException(
                    status_code=413,
                    detail="Request body too large"
                )

    def validate_content_type(self, request: Request, expected: str = "application/json"):
        """Validate content type header"""
        content_type = request.headers.get("content-type", "")

        if expected not in content_type.lower():
            raise HTTPException(
                status_code=415,
                detail=f"Expected content-type: {expected}"
            )
```

### 2.2 API Endpoints with Security

**File**: `ClassicAPI/endpoints/scan_endpoints.py`

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import tempfile
from pathlib import Path

from ClassicAPI.core.security import JWTAuthenticator, RateLimiter, RequestValidator
from ClassicLib.Security.sanitizer import InputSanitizer
from ClassicLib.Security.path_validator import PathValidator

router = APIRouter()
auth = JWTAuthenticator(secret_key="your-secret-key")  # Use env variable in production
rate_limiter = RateLimiter()
sanitizer = InputSanitizer()
path_validator = PathValidator()

class ScanRequest(BaseModel):
    """Validated scan request model"""

    game_type: str = Field(..., regex="^(Fallout4|SkyrimSE)$")
    scan_type: str = Field(..., regex="^(crash|game|papyrus)$")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('options')
    def validate_options(cls, v):
        """Sanitize options dictionary"""
        if v:
            # Limit dictionary size
            if len(v) > 20:
                raise ValueError("Too many options provided")

            # Validate each option
            allowed_options = {
                'max_lines', 'include_mods', 'deep_scan',
                'timeout', 'output_format'
            }

            for key in v.keys():
                if key not in allowed_options:
                    raise ValueError(f"Unknown option: {key}")

        return v

class ScanResponse(BaseModel):
    """Scan response with sanitized data"""

    scan_id: str
    status: str
    results: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)

    @validator('errors')
    def sanitize_errors(cls, v):
        """Remove sensitive information from errors"""
        sanitized = []
        for error in v:
            # Remove absolute paths
            error = re.sub(r'[A-Z]:\\[^"\']*', '[PATH]', error)
            error = re.sub(r'/[^"\']*', '[PATH]', error)
            # Remove stack traces
            error = error.split('\n')[0]
            sanitized.append(error)
        return sanitized

@router.post("/api/v1/scan/upload")
async def upload_and_scan(
    file: UploadFile = File(...),
    scan_request: ScanRequest = Depends(),
    user = Depends(auth.verify_token),
    _rate_limit = Depends(rate_limiter.check_rate_limit)
):
    """Upload and scan a crash log with comprehensive validation"""

    # Check user permissions
    if "scan:write" not in user.get("permissions", []):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Validate file
    if file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=413, detail="File too large")

    # Validate file type
    if not file.filename.endswith(('.log', '.txt')):
        raise HTTPException(status_code=415, detail="Invalid file type")

    # Create secure temporary file
    with tempfile.TemporaryDirectory(prefix="classic_scan_") as temp_dir:
        temp_path = Path(temp_dir)

        # Sanitize filename
        safe_filename = path_validator.sanitize_filename(file.filename)
        file_path = temp_path / safe_filename

        # Save uploaded file
        content = await file.read()

        # Validate content doesn't contain malicious patterns
        content_str = content.decode('utf-8', errors='ignore')
        if len(content_str) > 1000000:  # 1MB text limit
            raise HTTPException(status_code=413, detail="File content too large")

        # Write to temp file
        file_path.write_bytes(content)

        # Perform scan with timeout and resource limits
        try:
            from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
            from ClassicLib.Security.config import set_security_context, ExecutionContext

            # Set security context for API calls
            set_security_context(ExecutionContext.WEB_API)

            # Create orchestrator with limited resources
            orchestrator = OrchestratorCore(
                max_workers=2,  # Limit concurrent operations
                timeout=30,     # 30 second timeout
                memory_limit=100 * 1024 * 1024  # 100MB memory limit
            )

            # Perform scan
            results = await orchestrator.scan_file(
                file_path,
                game_type=scan_request.game_type,
                options=scan_request.options
            )

            # Sanitize results before returning
            sanitized_results = sanitizer.sanitize_json(results)

            return ScanResponse(
                scan_id=generate_scan_id(),
                status="completed",
                results=sanitized_results
            )

        except Exception as e:
            # Log full error internally, return sanitized version
            logger.error(f"Scan failed: {e}")

            return ScanResponse(
                scan_id=generate_scan_id(),
                status="failed",
                errors=[sanitizer.sanitize_string(str(e), 200)]
            )
        finally:
            # Ensure cleanup
            if file_path.exists():
                file_path.unlink()
```

### 2.3 API Gateway Configuration

**File**: `ClassicAPI/main.py`

```python
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import uuid

from ClassicAPI.endpoints import scan_endpoints, info_endpoints
from ClassicAPI.core.security import RequestValidator
from ClassicAPI.core.logging import SecurityAuditLogger

app = FastAPI(
    title="Classic API",
    version="1.0.0",
    docs_url=None,  # Disable in production
    redoc_url=None
)

# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    # Remove sensitive headers
    response.headers.pop("Server", None)
    response.headers.pop("X-Powered-By", None)

    return response

# Request ID middleware for tracking
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response

# Audit logging middleware
audit_logger = SecurityAuditLogger()

@app.middleware("http")
async def audit_logging(request: Request, call_next):
    start_time = time.time()

    # Log request
    await audit_logger.log_request(
        request_id=request.state.request_id,
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host,
        user_agent=request.headers.get("User-Agent", "")
    )

    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    await audit_logger.log_response(
        request_id=request.state.request_id,
        status_code=response.status_code,
        process_time=process_time
    )

    return response

# CORS configuration (restrictive)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600
)

# Trusted host validation
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
)

# Include routers
app.include_router(scan_endpoints.router, prefix="/api/v1")
app.include_router(info_endpoints.router, prefix="/api/v1")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log full exception
    audit_logger.log_error(
        request_id=request.state.request_id,
        error=str(exc),
        traceback=traceback.format_exc()
    )

    # Return sanitized error
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request.state.request_id
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

---

## Phase 3: Infrastructure & Deployment (Week 3-4)

### 3.1 Container Security

**File**: `Dockerfile`

```dockerfile
# Use minimal base image
FROM python:3.12-slim-bookworm

# Run as non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /data /tmp/classic && \
    chown -R appuser:appuser /app /data /tmp/classic

# Install security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser ClassicLib ./ClassicLib
COPY --chown=appuser:appuser ClassicAPI ./ClassicAPI

# Set security environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CLASSIC_SECURITY_CONTEXT=web_api \
    CLASSIC_SANDBOX_PATH=/data

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "ClassicAPI.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100"]
```

### 3.2 Kubernetes Deployment

**File**: `k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: classic-api
  labels:
    app: classic-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: classic-api
  template:
    metadata:
      labels:
        app: classic-api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      # Security context
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault

      containers:
      - name: classic-api
        image: classic-api:latest
        imagePullPolicy: Always

        # Container security
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL

        # Resource limits
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

        # Environment variables from secrets
        envFrom:
        - secretRef:
            name: classic-api-secrets

        # Volume mounts
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: data
          mountPath: /data

        # Probes
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10

        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

      volumes:
      - name: tmp
        emptyDir: {}
      - name: data
        emptyDir: {}
```

---

## Phase 4: Security Testing & Monitoring (Week 4)

### 4.1 Security Test Suite

**File**: `tests/security/test_security.py`

```python
import pytest
from fastapi.testclient import TestClient
import jwt
from datetime import datetime, timedelta

from ClassicAPI.main import app
from ClassicAPI.core.security import JWTAuthenticator

client = TestClient(app)

class TestSecurityFeatures:
    """Comprehensive security testing"""

    def test_sql_injection_prevention(self):
        """Test SQL injection is blocked"""
        malicious_input = "'; DROP TABLE users; --"

        response = client.post(
            "/api/v1/scan",
            json={"game_type": malicious_input}
        )

        assert response.status_code == 422  # Validation error
        assert "DROP TABLE" not in str(response.json())

    def test_path_traversal_prevention(self):
        """Test path traversal is blocked"""
        malicious_path = "../../../etc/passwd"

        response = client.post(
            "/api/v1/file/read",
            json={"path": malicious_path}
        )

        assert response.status_code in [400, 403]
        assert "passwd" not in str(response.json())

    def test_command_injection_prevention(self):
        """Test command injection is blocked"""
        malicious_command = "test.log; rm -rf /"

        response = client.post(
            "/api/v1/scan/upload",
            files={"file": ("test.log", b"content", "text/plain")},
            data={"filename": malicious_command}
        )

        assert response.status_code in [400, 422]

    def test_rate_limiting(self):
        """Test rate limiting works"""
        # Make many rapid requests
        responses = []
        for i in range(100):
            response = client.get("/api/v1/info")
            responses.append(response.status_code)

        # Should have some 429 (Too Many Requests) responses
        assert 429 in responses

    def test_jwt_expiration(self):
        """Test expired JWT is rejected"""
        auth = JWTAuthenticator(secret_key="test-key")

        # Create expired token
        payload = {
            "user_id": "test",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        expired_token = jwt.encode(payload, "test-key", algorithm="HS256")

        response = client.get(
            "/api/v1/protected",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401

    def test_xss_prevention(self):
        """Test XSS is prevented"""
        xss_payload = "<script>alert('XSS')</script>"

        response = client.post(
            "/api/v1/scan",
            json={"notes": xss_payload}
        )

        # Check response doesn't contain unescaped script
        assert "<script>" not in str(response.json())
        assert "&lt;script&gt;" in str(response.json()) or response.status_code == 422
```

### 4.2 Security Monitoring

**File**: `ClassicAPI/monitoring/security_monitor.py`

```python
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import logging
from typing import Dict, List

class SecurityMonitor:
    """Real-time security monitoring and alerting"""

    def __init__(self):
        self.events: Dict[str, List[datetime]] = defaultdict(list)
        self.alerts = []
        self.logger = logging.getLogger("security")

    async def detect_brute_force(self, user_id: str, failed_attempts: int = 5):
        """Detect brute force attempts"""
        key = f"failed_login:{user_id}"
        now = datetime.utcnow()

        # Add current attempt
        self.events[key].append(now)

        # Clean old events
        cutoff = now - timedelta(minutes=5)
        self.events[key] = [e for e in self.events[key] if e > cutoff]

        # Check threshold
        if len(self.events[key]) >= failed_attempts:
            await self.raise_alert(
                "BRUTE_FORCE",
                f"Multiple failed login attempts for user: {user_id}"
            )
            return True

        return False

    async def detect_scanning(self, client_ip: str, threshold: int = 50):
        """Detect vulnerability scanning"""
        key = f"404_errors:{client_ip}"
        now = datetime.utcnow()

        self.events[key].append(now)

        # Check for scanning pattern
        cutoff = now - timedelta(minutes=1)
        recent_404s = [e for e in self.events[key] if e > cutoff]

        if len(recent_404s) >= threshold:
            await self.raise_alert(
                "SCANNING",
                f"Possible vulnerability scanning from IP: {client_ip}"
            )
            return True

        return False

    async def detect_sql_injection_attempt(self, request_data: str):
        """Detect SQL injection patterns"""
        sql_patterns = [
            "' OR '1'='1",
            "'; DROP TABLE",
            "UNION SELECT",
            "/**/",
            "xp_cmdshell",
            "EXEC sp_",
            "EXECUTE sp_"
        ]

        for pattern in sql_patterns:
            if pattern.lower() in request_data.lower():
                await self.raise_alert(
                    "SQL_INJECTION",
                    f"SQL injection attempt detected: {pattern}"
                )
                return True

        return False

    async def raise_alert(self, alert_type: str, message: str):
        """Raise security alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": self.get_severity(alert_type)
        }

        self.alerts.append(alert)
        self.logger.warning(f"SECURITY ALERT: {alert}")

        # Send to monitoring system (e.g., PagerDuty, Slack)
        await self.send_to_monitoring(alert)

    def get_severity(self, alert_type: str) -> str:
        """Get alert severity"""
        severity_map = {
            "SQL_INJECTION": "CRITICAL",
            "COMMAND_INJECTION": "CRITICAL",
            "BRUTE_FORCE": "HIGH",
            "SCANNING": "MEDIUM",
            "RATE_LIMIT": "LOW"
        }
        return severity_map.get(alert_type, "MEDIUM")

    async def send_to_monitoring(self, alert: dict):
        """Send alert to external monitoring"""
        # Implement integration with monitoring service
        pass
```

---

## Implementation Timeline

### Week 1: Foundation
- [ ] Implement security configuration module
- [ ] Create secure database wrapper
- [ ] Implement path validation
- [ ] Add input sanitization

### Week 2: Core Security
- [ ] Fix critical vulnerabilities in ClassicLib
- [ ] Add security context switching
- [ ] Implement authentication system
- [ ] Create rate limiting

### Week 3: API Development
- [ ] Build FastAPI application
- [ ] Implement secure endpoints
- [ ] Add request validation
- [ ] Create API documentation

### Week 4: Deployment & Testing
- [ ] Create Docker container
- [ ] Set up Kubernetes deployment
- [ ] Implement security testing
- [ ] Add monitoring and alerting

### Week 5: Hardening
- [ ] Penetration testing
- [ ] Performance optimization
- [ ] Security audit
- [ ] Documentation completion

---

## Desktop Compatibility Considerations

### Maintaining Desktop Functionality

1. **Security Context Switching**
   ```python
   # Desktop app initialization
   from ClassicLib.Security.config import set_security_context, ExecutionContext

   # For desktop apps
   set_security_context(ExecutionContext.DESKTOP)

   # For web API
   set_security_context(ExecutionContext.WEB_API)
   ```

2. **Conditional Security Checks**
   ```python
   from ClassicLib.Security.config import get_security_config

   config = get_security_config()

   if config.is_web_context():
       # Apply strict validation
       validate_path(user_path)
   else:
       # Desktop mode - less restrictive
       pass
   ```

3. **Backward Compatibility**
   - All existing desktop code continues to work
   - Security features are opt-in via context
   - No breaking changes to existing API

### Migration Path for Desktop Apps

1. **Phase 1**: No changes required
2. **Phase 2**: Optional security enhancements
3. **Phase 3**: Gradual adoption of security features

---

## Security Checklist

### Pre-Deployment
- [ ] All critical vulnerabilities fixed
- [ ] Authentication system implemented
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention verified
- [ ] Path traversal protection tested
- [ ] Command injection blocked
- [ ] YAML safe loading implemented

### Deployment
- [ ] HTTPS only with valid certificates
- [ ] Security headers configured
- [ ] CORS properly restricted
- [ ] Secrets in environment variables
- [ ] Container running as non-root
- [ ] Resource limits configured
- [ ] Network policies in place
- [ ] Monitoring and alerting active

### Post-Deployment
- [ ] Penetration testing completed
- [ ] Security audit performed
- [ ] Incident response plan created
- [ ] Regular security updates scheduled
- [ ] Backup and recovery tested

---

## Conclusion

This implementation plan provides a comprehensive security layer for ClassicLib that:

1. **Maintains backward compatibility** for desktop applications
2. **Adds robust security** for web deployment
3. **Provides defense in depth** with multiple security layers
4. **Enables gradual migration** from desktop to web
5. **Includes comprehensive testing** and monitoring

The modular design allows teams to implement security features incrementally while maintaining existing desktop functionality. The API layer acts as a security boundary, ensuring that web requests are properly validated while desktop applications can continue to use ClassicLib directly.

Total estimated implementation time: **4-5 weeks** with a dedicated team.
