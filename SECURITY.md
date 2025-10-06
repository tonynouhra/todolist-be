# Security Policy

## Supported Versions

We actively maintain security updates for the latest version of the TodoList Backend API.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please email us at security@todolist.dev. We will respond within 48 hours.

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Security Updates

### Recently Fixed (2025-10-06)

#### ✅ CVE-2025-59420 (authlib) - FIXED
- **Package**: authlib 1.6.1 → 1.6.5
- **Vulnerability**: GHSA-9ggr-2464-2j32
- **Severity**: HIGH
- **Issue**: JWS verification accepts tokens with unknown critical header parameters
- **Impact**: Split-brain verification in mixed-language environments can lead to policy bypass
- **Fix**: Upgraded to authlib 1.6.5
- **Status**: ✅ RESOLVED

### Known Issues (Awaiting Upstream Fix)

#### ⏳ CVE-2025-8869 (pip) - AWAITING PATCH
- **Package**: pip 25.2
- **Vulnerability**: GHSA-4xh5-x5gv-qwph
- **Severity**: MODERATE
- **Issue**: Fallback tar extraction doesn't validate symbolic link targets
- **Impact**: Malicious source distributions can overwrite arbitrary files during installation
- **Mitigation**:
  - Only install packages from trusted sources (PyPI, internal repositories)
  - Avoid installing from untrusted URLs or custom package indexes
  - Use Python interpreters that implement PEP 706 safe extraction
- **Upstream Fix**: Pending in pip 25.3 ([PR #13550](https://github.com/pypa/pip/pull/13550))
- **Status**: ⏳ AWAITING UPSTREAM RELEASE
- **Last Checked**: 2025-10-06

## Security Best Practices

### Development Environment
1. Always use virtual environments
2. Regularly run `pip-audit` to check for vulnerabilities
3. Keep dependencies updated with `pip install --upgrade`
4. Review security advisories in `requirements.txt`

### Production Deployment
1. Use environment variables for secrets (never commit to git)
2. Enable HTTPS/TLS for all API endpoints
3. Configure proper CORS settings
4. Use rate limiting on authentication endpoints
5. Implement proper logging and monitoring
6. Regular security audits with `safety`, `bandit`, and `pip-audit`

### Dependency Management
- Pin exact versions in `requirements.txt` for reproducible builds
- Document security fixes in comments
- Subscribe to security advisories for critical dependencies:
  - FastAPI/Starlette
  - SQLAlchemy
  - Pydantic
  - Cryptography
  - JWT libraries

## Security Scanning

We use multiple security scanning tools:

```bash
# Check for known vulnerabilities
pip-audit

# Static security analysis
bandit -r app/

# Dependency safety check
safety check

# Code quality with security rules
ruff check app/ --select=S
```

## CI/CD Exception Handling

Our CI/CD pipeline is configured to allow documented, low-risk vulnerabilities to pass while blocking new/unknown issues. See [.github/CI-EXCEPTIONS.md](.github/CI-EXCEPTIONS.md) for details on how the pipeline handles known vulnerabilities.

**Current CI Exceptions**:
- pip 25.2 (GHSA-4xh5-x5gv-qwph) - Documented above, awaiting upstream fix

## Contact

For security concerns, contact: security@todolist.dev

For general issues, use GitHub Issues: https://github.com/todolist/todolist-be/issues
