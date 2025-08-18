# Contributing to TodoList Backend

Welcome! We're excited that you want to contribute to the TodoList Backend project. This document provides guidelines and information for contributors.

## 🚀 Quick Start

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/todolist-be.git
   cd todolist-be
   ```

2. **Set up development environment**
   ```bash
   ./scripts/setup-dev.sh
   ```

3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make your changes and commit**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📋 Development Guidelines

### Code Style

We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **Ruff**: Fast Python linter
- **MyPy**: Type checking
- **Bandit**: Security linting

Run these before committing:
```bash
# Format code
black app/ tests/
isort app/ tests/

# Lint code
ruff check app/ tests/

# Type check
mypy app/

# Security check
bandit -r app/
```

### Pre-commit Hooks

Install pre-commit hooks to automatically run checks:
```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(todo): add AI-powered subtask generation
fix(auth): resolve token validation issue
docs: update API documentation
test(user): add unit tests for user service
```

## 🧪 Testing

### Running Tests

```bash
# All tests
python run_tests.py --all

# Specific test types
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --api
python run_tests.py --e2e

# With coverage
python run_tests.py --unit --coverage
```

### Writing Tests

1. **Unit Tests**: Test individual functions/methods in isolation
   - Location: `tests/unit/`
   - Use mocks for external dependencies
   - Fast execution

2. **Integration Tests**: Test service interactions
   - Location: `tests/integration/`
   - Use test database
   - Test cross-service workflows

3. **API Tests**: Test HTTP endpoints
   - Location: `tests/api/`
   - Use test client
   - Test request/response handling

4. **E2E Tests**: Test complete workflows
   - Location: `tests/e2e/`
   - Test user scenarios
   - Include error handling

### Test Requirements

- Minimum 80% code coverage
- All new features must have tests
- Bug fixes should include regression tests
- Tests should be fast and reliable

## 🏗️ Architecture Guidelines

### Project Structure

```
app/
├── main.py              # FastAPI application entry point
├── core/                # Core functionality (config, dependencies, security)
├── domains/             # Business logic organized by domain
│   ├── user/           # User management
│   ├── todo/           # Todo management
│   ├── ai/             # AI integration
│   └── file/           # File handling
├── schemas/            # Pydantic models for API
├── exceptions/         # Custom exception classes
└── shared/            # Shared utilities
```

### Adding New Features

1. **Create domain structure** (if new domain)
   ```
   app/domains/your_domain/
   ├── __init__.py
   ├── controller.py    # FastAPI routes
   └── service.py       # Business logic
   ```

2. **Add database models** in `models/`
3. **Create Pydantic schemas** in `schemas/`
4. **Add custom exceptions** in `exceptions/`
5. **Write comprehensive tests**
6. **Update documentation**

### Database Changes

1. **Create Alembic migration**
   ```bash
   alembic revision --autogenerate -m "description"
   ```

2. **Review generated migration**
3. **Test migration up and down**
4. **Update model classes**
5. **Add/update tests**

## 📖 Documentation

### API Documentation

- FastAPI auto-generates docs at `/docs`
- Add docstrings to all endpoints
- Include request/response examples
- Document error responses

### Code Documentation

- Use Google-style docstrings
- Document complex business logic
- Include type hints
- Add inline comments for tricky code

### README Updates

- Update installation instructions
- Document new environment variables
- Add usage examples
- Update feature list

## 🔒 Security Guidelines

### General Security

- Never commit secrets or API keys
- Use environment variables for configuration
- Validate all user inputs
- Implement proper authentication/authorization
- Follow OWASP security guidelines

### Security Tools

Our CI pipeline runs these security checks:
- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanner
- **Semgrep**: Static analysis security scanner
- **detect-secrets**: Secrets detection

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Steps to reproduce** the problem
3. **Expected vs actual behavior**
4. **Environment details** (OS, Python version, etc.)
5. **Error messages** or logs
6. **Screenshots** if applicable

Use our bug report template when creating issues.

## 💡 Feature Requests

For new features:

1. **Check existing issues** first
2. **Describe the problem** you're trying to solve
3. **Propose a solution** if you have one
4. **Consider backwards compatibility**
5. **Discuss implementation** approach

## 🎯 Pull Request Process

### Before Submitting

- [ ] Tests pass locally
- [ ] Code is properly formatted
- [ ] No linting errors
- [ ] Documentation updated
- [ ] Commit messages follow convention

### PR Requirements

- [ ] Clear description of changes
- [ ] Link to related issues
- [ ] Screenshots/demos for UI changes
- [ ] Breaking changes documented
- [ ] Security implications considered

### Review Process

1. **Automated checks** must pass
2. **Code review** by maintainers
3. **Testing** in staging environment
4. **Documentation** review
5. **Final approval** and merge

## 🏷️ Issue Labels

We use labels to categorize issues:

- `type::bug` - Bug reports
- `type::feature` - Feature requests
- `type::docs` - Documentation improvements
- `priority::high` - High priority items
- `priority::medium` - Medium priority items
- `priority::low` - Low priority items
- `status::needs-review` - Needs review
- `status::in-progress` - Being worked on

## 🤝 Getting Help

- **Documentation**: Check project docs first
- **Issues**: Search existing issues
- **Discussions**: Use GitHub Discussions for questions
- **Contact**: Reach out to maintainers

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## 🙏 Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to TodoList Backend! 🎉