# Branch Protection Setup Guide

This guide explains how to set up branch protection rules in GitHub to ensure code quality and security.

## 🛡️ Branch Protection Rules

### Main Branch Protection

To protect your `main` branch, follow these steps:

1. **Go to Repository Settings**
   - Navigate to your repository on GitHub
   - Click "Settings" tab
   - Click "Branches" in the left sidebar

2. **Add Branch Protection Rule**
   - Click "Add rule"
   - Enter `main` as the branch name pattern

3. **Configure Protection Settings**

#### Required Settings:
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: 1
  - ✅ Dismiss stale PR approvals when new commits are pushed
  - ✅ Require review from code owners (if you have CODEOWNERS file)

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - **Required status checks:**
    - `test` (Run Tests)
    - `code-quality` (Code Quality Checks)
    - `security` (Security Checks)
    - `dependency-check` (Dependency Analysis)

- ✅ **Require conversation resolution before merging**

- ✅ **Require signed commits** (recommended)

- ✅ **Require linear history** (optional, but recommended)

- ✅ **Do not allow bypassing the above settings**

#### Administrative Settings:
- ❌ Allow force pushes (keep disabled)
- ❌ Allow deletions (keep disabled)

### Develop Branch Protection (if using GitFlow)

For `develop` branch:
- Same settings as main, but with relaxed approval requirements
- Require approvals: 1 (can be 0 for development)
- Allow force pushes for maintainers (optional)

## 📋 Status Check Configuration

The following GitHub Actions workflows provide status checks:

### 1. CI Pipeline (`.github/workflows/ci.yml`)
**Required Checks:**
- `test` - Runs full test suite
- `code-quality` - Runs linting and formatting checks
- `security` - Runs security scans
- `dependency-check` - Checks for vulnerable dependencies

### 2. PR Quality Checks (`.github/workflows/pr-checks.yml`)
**Additional Checks:**
- `pr-quality` - Validates PR quality and size
- Code formatting verification
- Breaking change detection

### 3. Release Pipeline (`.github/workflows/release.yml`)
- Runs on tagged releases
- Full security and quality validation
- Builds and publishes artifacts

## 🔧 Setting Up Status Checks

1. **Push the workflow files** to your repository
2. **Trigger the workflows** by:
   - Creating a test PR
   - Pushing to main/develop branch
3. **Wait for workflows to complete**
4. **Go to Branch Protection settings**
5. **Add the status checks** listed above

## 👥 Code Owners (Optional)

Create a `.github/CODEOWNERS` file to automatically request reviews:

```
# Global owners
* @your-username @team-lead

# Domain-specific owners
app/domains/ai/ @ai-team-member
app/domains/auth/ @security-team-member
docs/ @documentation-team

# Infrastructure and CI
.github/ @devops-team
docker/ @devops-team
scripts/ @devops-team

# Database and migrations
migrations/ @database-admin
alembic/ @database-admin
```

## 🚫 Bypass Permissions

**Who can bypass protection:**
- Repository administrators (only in emergencies)
- Users with "Maintain" role (with restrictions)

**When to bypass:**
- Critical security hotfixes
- Emergency production issues
- CI/CD failures blocking releases

## ⚡ Emergency Procedures

### Hotfix Process
1. **Create hotfix branch** from main
2. **Apply minimal fix** 
3. **Request emergency review** from 2+ maintainers
4. **Use admin bypass** if critical
5. **Create follow-up PR** to add tests and documentation

### CI Failure Bypass
1. **Verify the failure** is in CI, not code
2. **Document the reason** in PR description
3. **Get approval** from maintainer
4. **Merge with admin override**
5. **Fix CI issue** in follow-up PR

## 📊 Monitoring and Metrics

### Branch Protection Metrics to Track:
- PR approval time
- Status check failure rate
- Bypass frequency
- Security scan findings
- Code coverage trends

### GitHub Insights:
- Go to repository "Insights" tab
- Check "Pulse" for activity overview
- Review "Contributors" for contribution patterns
- Monitor "Traffic" for repository usage

## 🔄 Automation Rules

### Auto-merge for Dependabot PRs
Add this to your repository settings:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    reviewers:
      - "your-username"
    assignees:
      - "your-username"
```

### Auto-assign Reviewers
Use GitHub's auto-assign feature or add to PR template:

```yaml
# .github/auto-assign.yml
reviewers:
  - your-username
  - team-member-1
  - team-member-2

numberOfReviewers: 1
numberOfAssignees: 1
```

## 🎯 Best Practices

### For Contributors:
1. **Keep PRs small** (< 500 lines of changes)
2. **Write descriptive commits** following conventional commits
3. **Add tests** for new features
4. **Update documentation** as needed
5. **Respond to review feedback** promptly

### For Maintainers:
1. **Review PRs within 24 hours**
2. **Provide constructive feedback**
3. **Test significant changes locally**
4. **Approve only when confident**
5. **Use squash and merge** for clean history

### For Security:
1. **Never bypass security checks**
2. **Review dependency updates carefully**
3. **Validate external contributions thoroughly**
4. **Monitor for suspicious activity**
5. **Keep access tokens secure**

## 📚 Additional Resources

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [CODEOWNERS Documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)

## 🆘 Troubleshooting

### Status Checks Not Appearing
1. Ensure workflows have run at least once
2. Check workflow syntax in Actions tab
3. Verify branch names match in protection rules
4. Check if workflows are disabled

### PRs Can't Be Merged
1. Verify all required checks have passed
2. Check if branch is up to date
3. Ensure PR has required approvals
4. Look for conversation threads that need resolution

### Bypass Not Working
1. Confirm admin permissions
2. Check if bypass is enabled in protection settings
3. Verify you're not trying to bypass required checks incorrectly

## ✅ Verification Checklist

After setting up branch protection:

- [ ] Main branch is protected
- [ ] Required status checks are configured
- [ ] PR approval requirements are set
- [ ] Conversation resolution is required
- [ ] Force pushes are disabled
- [ ] Deletions are disabled
- [ ] Code owners file is created (if needed)
- [ ] Team members understand the process
- [ ] Emergency procedures are documented
- [ ] Status checks are working in test PR

Your repository is now secured with proper branch protection! 🎉