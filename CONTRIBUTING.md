# Contributing to Icarus

Thank you for your interest in contributing to Icarus! This document provides guidelines and instructions for contributing to the project.

## 🎯 Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## 🚀 Getting Started

### Prerequisites
- Python 3.13+
- Node.js 18+
- Git
- SQLite3

### Development Setup
1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/icarus.git
   cd icarus
   ```
3. Set up Python environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Set up frontend:
   ```bash
   cd client
   npm install
   cd ..
   ```
5. Initialize database:
   ```bash
   python -c "from app_bootstrap import bootstrap; bootstrap()"
   ```

## 📝 Development Workflow

### Branch Strategy
- `main`: Stable production code
- `develop`: Integration branch for features
- `feature/*`: New features
- `bugfix/*`: Bug fixes
- `docs/*`: Documentation updates

### Creating a Feature
1. Create a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
2. Make your changes
3. Write or update tests
4. Ensure code quality standards are met
5. Commit with descriptive messages
6. Push to your fork
7. Create a Pull Request

### Commit Message Convention
We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:
```
feat(api): add REST endpoint for sleep analytics

• Add POST /api/sleep/analytics endpoint
• Implement sleep pattern detection
• Add unit tests for new functionality

Closes #123
```

## 🧪 Testing

### Python Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_session_service.py

# Run with coverage
pytest --cov=.

# Run with verbose output
pytest -v
```

### Frontend Tests
```bash
cd client
npm test
```

### Test Structure
- Unit tests in `tests/` directory
- Test files mirror source structure
- Use descriptive test names
- Each test should be independent

## 🎨 Code Quality

### Python Standards
- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints where appropriate
- Write docstrings for public functions/classes
- Keep functions focused and small

### Frontend Standards
- Follow Svelte best practices
- Use TailwindCSS for styling
- Keep components focused and reusable
- Write clean, maintainable JavaScript

### Code Formatting
```bash
# Format Python code
black .
isort .

# Lint Python code
flake8
mypy .

# Format frontend code
cd client
npm run format
```

### Pre-commit Hooks
Consider setting up pre-commit hooks:
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

## 📁 Project Structure

### Backend Architecture
```
core/           # Domain models and business logic
services/       # Business logic services
storage/        # Data persistence layer
api/            # Flask REST API
ui/             # Tkinter desktop GUI
cli/            # Command-line interface
tests/          # Python tests
```

### Frontend Architecture
```
client/
├── src/
│   ├── lib/           # Reusable components
│   ├── stores/        # Svelte stores
│   └── utils/         # Utility functions
└── tests/             # Frontend tests
```

## 🐛 Reporting Issues

### Bug Reports
When reporting bugs, please include:
1. Clear description of the issue
2. Steps to reproduce
3. Expected vs actual behavior
4. Environment details (OS, Python version, etc.)
5. Relevant logs or error messages

### Feature Requests
When requesting features, please:
1. Describe the problem you're trying to solve
2. Explain your proposed solution
3. Provide use cases or examples
4. Consider edge cases

## 🔧 Pull Request Process

1. **Ensure tests pass**: All tests must pass before submitting
2. **Update documentation**: Update README, docs, or comments as needed
3. **Follow coding standards**: Adhere to project style guidelines
4. **Keep changes focused**: One feature/fix per PR
5. **Add tests**: Include tests for new functionality
6. **Update changelog**: Note changes in PR description
7. **Request review**: Assign appropriate reviewers

### PR Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guidelines
- [ ] Commit messages follow convention
- [ ] No breaking changes (unless intentional)
- [ ] All checks pass

## 📚 Documentation

### Writing Documentation
- Use clear, concise language
- Include code examples where helpful
- Keep documentation up-to-date with code changes
- Use Markdown formatting consistently

### Documentation Locations
- `README.md`: Project overview and getting started
- `docs/`: Detailed documentation and guides
- Code docstrings: API documentation
- `CONTRIBUTING.md`: This file

## 🏆 Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes
- Project documentation (if significant contributions)

## ❓ Getting Help

- Check existing documentation first
- Search existing issues
- Ask in PR discussions
- Be respectful and patient

## 📄 License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

---

Thank you for contributing to Icarus! Your help makes this project better for everyone. 🚀