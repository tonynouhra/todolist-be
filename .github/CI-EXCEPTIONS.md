# CI/CD Exception Handling

This document describes how the CI/CD pipeline handles known security vulnerabilities and exceptions.

## Overview

The CI/CD pipeline includes security scanning tools that may detect vulnerabilities. Some vulnerabilities are known, documented, and have accepted risk due to:
- Awaiting upstream fixes
- Low/moderate severity with adequate mitigations
- No available patches yet

## Current Exceptions

### Dependency Analysis Job

The `dependency-check` job uses `pip-audit` to scan for package vulnerabilities. It has been configured to allow specific known exceptions while still failing on new/unknown vulnerabilities.

#### Exception: pip GHSA-4xh5-x5gv-qwph (CVE-2025-8869)

**Status**: ✅ ALLOWED TO PASS
**Package**: pip 25.2
**Severity**: MODERATE
**Issue**: Fallback tar extraction doesn't validate symbolic link targets
**Risk**: Malicious source distributions can overwrite files during installation

**Why This Exception Exists**:
- No patched version available yet (fix planned for pip 25.3)
- Impact requires installing malicious packages from untrusted sources
- Project only installs from PyPI and internal trusted sources
- Documented in `SECURITY.md` with mitigation strategies

**CI Behavior**:
- ✅ **PASS**: If only this vulnerability is detected
- ❌ **FAIL**: If any additional vulnerabilities are found

**Mitigation Strategies**:
1. Only install packages from trusted sources (PyPI)
2. Avoid installing from unknown URLs or package indexes
3. Monitor for pip 25.3 release and upgrade immediately
4. Use Python interpreters implementing PEP 706 safe extraction

**Review Schedule**: Check monthly for upstream fix availability

## How It Works

### Single Known Vulnerability (PASS)
```bash
# pip-audit output
Found 1 known vulnerability in 1 package
Name Version ID                  Fix Versions
---- ------- ------------------- ------------
pip  25.2    GHSA-4xh5-x5gv-qwph

# CI Result: ✅ PASS
# Only the documented pip vulnerability - continue pipeline
```

### Multiple Vulnerabilities (FAIL)
```bash
# pip-audit output
Found 2 known vulnerabilities in 2 packages
Name     Version ID                  Fix Versions
----     ------- ------------------- ------------
pip      25.2    GHSA-4xh5-x5gv-qwph
authlib  1.6.1   GHSA-9ggr-2464-2j32 1.6.4

# CI Result: ❌ FAIL
# Additional vulnerability detected - must fix before merging
```

### Unknown Vulnerabilities (FAIL)
```bash
# pip-audit output with no pip vulnerability
Found 1 known vulnerability in 1 package
Name     Version ID                  Fix Versions
----     ------- ------------------- ------------
requests 2.28.0  GHSA-xxxx-xxxx-xxxx 2.31.0

# CI Result: ❌ FAIL
# Unknown vulnerability - must fix before merging
```

## Adding New Exceptions

**⚠️ WARNING**: Adding exceptions reduces security posture. Only add exceptions when absolutely necessary.

### Requirements for Adding an Exception

1. **Document in SECURITY.md**:
   - CVE/Advisory ID
   - Severity level
   - Impact assessment
   - Mitigation strategies
   - Expected resolution date

2. **Update CI Workflow** (`.github/workflows/ci.yml`):
   - Add the new vulnerability ID to the check logic
   - Update vulnerability counting if needed
   - Document the exception in comments

3. **Risk Assessment**:
   - Severity: HIGH → Requires immediate workaround/mitigation
   - Severity: MODERATE → Acceptable with documented mitigations
   - Severity: LOW → May be acceptable temporarily

4. **Review and Approval**:
   - Requires security team review
   - Document business justification
   - Set review/remediation date

### Exception Template

```markdown
#### Exception: [Package] [Advisory-ID] ([CVE])

**Status**: [ALLOWED/TEMPORARY/REVIEW-NEEDED]
**Package**: [name version]
**Severity**: [HIGH/MODERATE/LOW]
**Issue**: [Brief description]
**Risk**: [Actual impact]

**Why This Exception Exists**:
- [Reason 1]
- [Reason 2]

**CI Behavior**: [How CI handles this]

**Mitigation Strategies**:
1. [Strategy 1]
2. [Strategy 2]

**Review Schedule**: [Date or frequency]
```

## Removing Exceptions

When a vulnerability is fixed:

1. **Update Dependencies**:
   ```bash
   pip install --upgrade [package]
   pip freeze > requirements.txt
   ```

2. **Update CI Workflow**:
   - Remove the exception check from `.github/workflows/ci.yml`
   - Remove related comments

3. **Update Documentation**:
   - Move from "Known Issues" to "Recently Fixed" in `SECURITY.md`
   - Remove from this document

4. **Verify CI Passes**:
   ```bash
   pip-audit  # Should now pass with 0 vulnerabilities
   ```

## Monitoring and Review

### Regular Reviews
- **Weekly**: Check for new vulnerabilities with `pip-audit`
- **Monthly**: Review all documented exceptions for fixes
- **Quarterly**: Full security audit and exception justification

### Automation
- GitHub Dependabot alerts for new vulnerabilities
- Scheduled workflow runs for security scanning
- Notification on new pip-audit findings

## Emergency Procedures

### Critical Vulnerability Detected

If pip-audit detects a CRITICAL severity vulnerability:

1. **Immediate Actions**:
   - Assess impact on production systems
   - Check if patch/workaround available
   - Consider temporary service restrictions

2. **Exception Process**:
   - CRITICAL vulnerabilities should NOT be added as exceptions
   - If no patch available, implement immediate mitigations:
     - Disable affected functionality
     - Network segmentation
     - Enhanced monitoring

3. **Communication**:
   - Notify security team immediately
   - Update SECURITY.md with alert status
   - Document incident and response

## Related Documents

- [SECURITY.md](../SECURITY.md) - Security policy and vulnerability status
- [requirements.txt](../requirements.txt) - Dependency versions and security notes
- [CI/CD Pipeline](.github/workflows/ci.yml) - Automated security checks

## Contact

For questions about CI exceptions:
- Security Team: security@todolist.dev
- DevOps Team: devops@todolist.dev
- GitHub Issues: https://github.com/todolist/todolist-be/issues

---

**Last Updated**: 2025-10-06
**Next Review**: 2025-11-06
