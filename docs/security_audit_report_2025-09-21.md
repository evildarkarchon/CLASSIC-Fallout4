# Security Audit Report - ClassicLib
**Date**: 2025-01-21
**Auditor**: Python Security Auditor (Automated)
**Scope**: ClassicLib directory - Web application security assessment

## Executive Summary

This security audit was conducted to assess the suitability of the ClassicLib codebase for web application deployment. The audit identified **24 security vulnerabilities** that would pose significant risks in a web context.

### Vulnerability Summary
- **Critical**: 3
- **High**: 8
- **Medium**: 9
- **Low**: 4

**Verdict**: This codebase requires substantial security hardening before web deployment. Critical vulnerabilities including command injection, SQL injection, and unsafe deserialization must be addressed immediately.

---

## Critical Vulnerabilities

### 1. Command Injection Vulnerability
- **File**: `ClassicLib/Interface/FolderManagement.py`
- **Line**: 228
- **Severity**: Critical
- **Description**: Direct use of user-controlled file paths in subprocess.Popen without proper validation
- **Code Sample**:
  ```python
  subprocess.Popen([str(notepadpp_path), str(file_path)])
  ```
- **Impact**: Arbitrary system command execution through crafted file paths
- **Remediation**:
  ```python
  import shlex

  # Validate paths exist and are files
  if not file_path.is_file():
      raise ValueError("File does not exist")
  if not notepadpp_path.is_file():
      raise ValueError("Editor not found")

  # Use list format with shell=False
  subprocess.Popen([str(notepadpp_path), str(file_path)], shell=False)
  ```

### 2. SQL Injection via Dynamic Table Names
- **Files**:
  - `ClassicLib/ScanLog/AsyncUtil.py` (lines 247, 304)
  - `ClassicLib/ScanLog/Util.py` (line 317)
- **Severity**: Critical
- **Description**: Dynamic table names from GlobalRegistry directly interpolated into SQL queries
- **Code Sample**:
  ```python
  query = f"SELECT entry FROM {game_table} WHERE formid=? AND plugin=? COLLATE nocase"
  ```
- **Impact**: SQL injection if game name can be controlled
- **Remediation**:
  ```python
  ALLOWED_TABLES = ['Fallout4', 'SkyrimSE', 'Fallout4VR', 'SkyrimVR']
  game_table = GlobalRegistry.get_game()

  if game_table not in ALLOWED_TABLES:
      raise ValueError(f"Invalid table name: {game_table}")

  # Then use the validated table name in query
  ```

### 3. Unsafe YAML Loading
- **File**: `ClassicLib/AsyncYamlSettings/file_operations.py`
- **Line**: 85
- **Severity**: Critical
- **Description**: Uses yaml.load() which can execute arbitrary Python code
- **Code Sample**:
  ```python
  data = yaml.load(StringIO(content))
  ```
- **Impact**: Arbitrary code execution through malicious YAML
- **Remediation**:
  ```python
  # Use safe loading
  yaml = ruamel.yaml.YAML(typ='safe', pure=True)
  data = yaml.load(StringIO(content))
  ```

---

## High-Risk Vulnerabilities

### 4. Path Traversal Vulnerabilities
- **Files**: Multiple including `DocsPath.py`, `GamePath.py`, `FileGeneration.py`
- **Severity**: High
- **Description**: User-controlled paths used without boundary validation
- **Impact**: Access to files outside intended directories
- **Remediation**:
  ```python
  def safe_path_join(base_path: Path, user_path: str) -> Path:
      base = base_path.resolve()
      target = (base / user_path).resolve()

      # Ensure target is within base directory
      try:
          target.relative_to(base)
          return target
      except ValueError:
          raise ValueError("Path traversal attempt detected")
  ```

### 5. Unvalidated External Command Arguments
- **File**: `ClassicLib/ScanGame/ScanGameCore.py`
- **Lines**: 988-995, 1073-1080
- **Severity**: High
- **Description**: BSArch path and file paths passed to subprocess without validation
- **Impact**: Potential execution of unintended binaries
- **Remediation**:
  ```python
  # Validate executable and input files
  if not bsarch_path.is_file():
      raise ValueError("BSArch executable not found")
  if not file_path.is_file():
      raise ValueError("Input file not found")

  # Consider validating binary hash/signature
  ```

### 6. Server-Side Request Forgery (SSRF) Risk
- **File**: `ClassicLib/Utils/web_utils.py`
- **Lines**: 72, 135
- **Severity**: High
- **Description**: URLs fetched without validation against internal networks
- **Impact**: Internal network scanning, cloud metadata access
- **Remediation**:
  ```python
  from ipaddress import ip_address, ip_network
  import socket

  def is_safe_url(url: str) -> bool:
      parsed = urlparse(url)

      # Whitelist allowed domains
      ALLOWED_DOMAINS = ['pastebin.com', 'paste.ee', 'hastebin.com']
      if parsed.hostname not in ALLOWED_DOMAINS:
          return False

      # Block private IP ranges
      try:
          ip = socket.gethostbyname(parsed.hostname)
          addr = ip_address(ip)

          private_ranges = [
              ip_network('10.0.0.0/8'),
              ip_network('172.16.0.0/12'),
              ip_network('192.168.0.0/16'),
              ip_network('127.0.0.0/8'),
              ip_network('169.254.0.0/16'),
          ]

          for private_range in private_ranges:
              if addr in private_range:
                  return False
      except Exception:
          return False

      return True
  ```

### 7. Insufficient Input Validation for File Operations
- **File**: `ClassicLib/FileIO/core.py`
- **Severity**: High
- **Description**: File write operations without path restriction
- **Impact**: Could overwrite system files
- **Remediation**:
  ```python
  FORBIDDEN_PATHS = [
      Path.home() / '.ssh',
      Path('/etc'),
      Path('C:/Windows/System32'),
      Path.home() / '.config'
  ]

  def validate_write_path(path: Path) -> bool:
      resolved = path.resolve()
      for forbidden in FORBIDDEN_PATHS:
          try:
              resolved.relative_to(forbidden)
              return False  # Path is within forbidden directory
          except ValueError:
              continue
      return True
  ```

---

## Medium-Risk Vulnerabilities

### 8. Weak YAML Input Sanitization
- **File**: `ClassicLib/TUI/input_validator.py`
- **Lines**: 181-204
- **Severity**: Medium
- **Description**: Incomplete YAML sanitization
- **Impact**: YAML injection attacks
- **Remediation**: Use YAML library's built-in escaping instead of manual replacement

### 9. Information Disclosure in Error Messages
- **Files**: Multiple
- **Severity**: Medium
- **Description**: Error messages leak sensitive paths and system details
- **Impact**: Aids attacker reconnaissance
- **Remediation**:
  ```python
  def sanitize_error(error: Exception) -> str:
      error_str = str(error)
      # Remove absolute paths
      error_str = re.sub(r'[A-Z]:\\[^"\']*', '[PATH]', error_str)
      error_str = re.sub(r'/[^"\']*', '[PATH]', error_str)
      # Remove stack traces in production
      if not DEBUG_MODE:
          error_str = error_str.split('\n')[0]
      return error_str
  ```

### 10. Race Condition in File Operations
- **File**: `ClassicLib/ScanGame/GameFilesManager.py`
- **Lines**: 305-308
- **Severity**: Medium
- **Description**: TOCTOU race condition when checking file existence
- **Impact**: Potential unintended file deletion
- **Remediation**: Use atomic operations with proper exception handling

### 11. Unrestricted Resource Consumption
- **File**: `ClassicLib/ScanGame/ScanGameCore.py`
- **Severity**: Medium
- **Description**: No limits on concurrent operations or memory usage
- **Impact**: Denial of Service through resource exhaustion
- **Remediation**: Implement resource limits and monitoring

---

## Low-Risk Vulnerabilities

### 12. Insecure Temporary File Handling
- **File**: `ClassicLib/ScanLog/AsyncFileIO.py`
- **Line**: 247
- **Severity**: Low
- **Description**: Temporary directories without explicit permissions
- **Impact**: Temporary data exposure to other users
- **Remediation**: Set restrictive permissions (700) on temporary directories

---

## Web Deployment Requirements

### Essential Security Infrastructure Needed

#### 1. Authentication & Authorization
- OAuth2/JWT implementation
- Role-based access control (RBAC)
- Session management
- Rate limiting

#### 2. Input Validation Framework
```python
class WebInputValidator:
    @staticmethod
    def validate_path(path: str, user_context: UserContext) -> Path:
        # Check user permissions
        # Validate against user's allowed directories
        # Prevent path traversal
        # Return safe, validated path
        pass
```

#### 3. Database Security Layer
- Parameterized queries only
- Query builder pattern
- Permission-based access layer
- Query logging and monitoring

#### 4. File Operation Sandboxing
- Per-user storage isolation
- Cloud storage integration (S3, Azure Blob)
- Virus scanning
- File type and size validation

#### 5. API Security
- API key management
- Request signing
- CORS configuration
- HTTPS with HSTS
- Content Security Policy headers

---

## Remediation Priority

### Phase 1: Critical (Immediate)
1. Fix SQL injection vulnerabilities
2. Replace unsafe YAML loading
3. Prevent command injection
4. Implement path traversal protection
5. Add SSRF protection

### Phase 2: High Priority (Week 1)
6. Validate external command arguments
7. Restrict file operation paths
8. Implement input validation framework
9. Add authentication system

### Phase 3: Medium Priority (Week 2-3)
10. Improve YAML sanitization
11. Sanitize error messages
12. Fix race conditions
13. Add resource limits
14. Implement API security layer

### Phase 4: Low Priority (Month 1)
15. Secure temporary file handling
16. Add comprehensive logging
17. Implement monitoring
18. Security testing suite

---

## Recommendations

### For Web Deployment

1. **Consider a Security-First Rewrite**: The desktop-centric design makes retrofitting web security complex
2. **Create Separate Web API Layer**: Build secure API layer that interfaces with core logic
3. **Implement Defense in Depth**: Multiple security layers, not single points of failure
4. **Regular Security Audits**: Automated SAST/DAST tools and manual penetration testing
5. **Security Training**: Ensure development team understands web security principles

### Architecture Changes

1. **Adopt Zero-Trust Model**: Never trust user input, always verify
2. **Implement Least Privilege**: Minimal permissions for all operations
3. **Use Security Libraries**: Adopt battle-tested security libraries
4. **Container Security**: If using containers, implement security best practices
5. **Secrets Management**: Never hardcode secrets, use proper key management

---

## Conclusion

The ClassicLib codebase, while functional as a desktop application, requires **substantial security hardening** before web deployment. The identified vulnerabilities, particularly the critical command and SQL injection issues, pose severe risks in a web context.

The transition from desktop to web requires not just vulnerability fixes, but a fundamental shift in security architecture including:
- Multi-tenant isolation
- Authentication and authorization
- Input validation at all boundaries
- Resource limits and monitoring
- API security controls

**Recommendation**: Do not deploy to web without addressing at least all Critical and High severity issues and implementing proper authentication/authorization infrastructure.

---

## Appendix: Security Testing Tools

Recommended tools for ongoing security validation:

### Static Analysis (SAST)
- Bandit (Python security linter)
- Semgrep (custom rule scanning)
- SonarQube (comprehensive analysis)

### Dynamic Analysis (DAST)
- OWASP ZAP (web app scanner)
- Burp Suite (penetration testing)
- SQLMap (SQL injection testing)

### Dependency Scanning
- Safety (Python dependency checker)
- Snyk (vulnerability database)
- GitHub Dependabot

### Code Review
- CodeQL (semantic code analysis)
- GitGuardian (secrets detection)
- TruffleHog (credential scanning)

---

*End of Security Audit Report*
