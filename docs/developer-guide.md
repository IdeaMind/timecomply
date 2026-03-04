# Developer Guide

## Prerequisites
- Python 3.12+
- `uv` installed globally (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- PostgreSQL (or use Railway's database via `DATABASE_URL`)
- GitHub CLI (`gh`) for issue management

## Getting Started

### 1. Clone and install dependencies
```bash
git clone git@github.com:adamrenner/timecomply.git
cd timecomply
uv sync
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your local settings
```

Minimum `.env` for local development:
```
DJANGO_SETTINGS_MODULE=config.settings.development
SECRET_KEY=local-dev-only-secret-key
DATABASE_URL=postgres://localhost/timecomply_dev
```

### 3. Set up the database
```bash
# Create local database
createdb timecomply_dev

# Run migrations
uv run python manage.py migrate

# Create a superuser
uv run python manage.py createsuperuser
```

### 4. Run the development server
```bash
uv run python manage.py runserver
```

Visit http://localhost:8000

## Running Tests

```bash
# All tests
uv run pytest

# With coverage report
uv run pytest --cov=apps --cov-report=term-missing

# Specific app
uv run pytest tests/timesheets/

# Specific test file
uv run pytest tests/timesheets/test_models.py

# Verbose output
uv run pytest -v
```

## Linting and Formatting

```bash
# Check for lint errors
uv run ruff check .

# Check formatting (without changing files)
uv run ruff format --check .

# Fix lint errors automatically
uv run ruff check --fix .

# Apply formatting
uv run ruff format .

# Run both (do this before committing)
uv run ruff check --fix . && uv run ruff format .
```

## Working with Migrations

```bash
# Create migrations for an app
uv run python manage.py makemigrations accounts

# Create migrations for all apps
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Show migration status
uv run python manage.py showmigrations

# Squash migrations (do not squash already-applied migrations in production)
uv run python manage.py squashmigrations accounts 0001 0005
```

## Adding a New App

```bash
# Create the app directory
mkdir apps/myapp
uv run python manage.py startapp myapp apps/myapp

# Add to INSTALLED_APPS in config/settings/base.py
# 'apps.myapp',

# Create test directory
mkdir -p tests/myapp
touch tests/myapp/__init__.py
```

## Adding a Dependency

```bash
# Add a production dependency
uv add django-allauth

# Add a development-only dependency
uv add --dev pytest-django

# Update all dependencies
uv sync --upgrade
```

## AI-Driven Development Workflow

Issues labeled `ready-for-ai` can be implemented automatically via GitHub Actions.

### Triggering AI Implementation
1. Find an issue in the `ready-for-ai` state
2. The `ai-implement.yml` workflow will pick it up
3. Claude Code will implement the feature in a new branch
4. A PR will be opened automatically
5. CI runs (lint, test, coverage)
6. The PR description includes "Human Testing Notes" from the original issue

### Writing AI-Ready Issues
Issues must include:
- Clear **Acceptance Criteria** (what done looks like)
- **Implementation Notes** (technical approach, which files to create/modify)
- **Human Testing Notes** (what a human tester must verify manually)

See `.github/ISSUE_TEMPLATE/ai-feature.md` for the template.

## Branch Strategy

- `main` — stable, deployable code; auto-deploys to staging
- Feature branches: `feature/issue-{number}-{short-description}`
- Bug fix branches: `fix/issue-{number}-{short-description}`
- Release tags: `v{major}.{minor}.{patch}` — auto-deploys to production

## Environment-Specific Settings

| Setting | Development | Production |
|---------|-------------|------------|
| `DEBUG` | True | False |
| `ALLOWED_HOSTS` | localhost, 127.0.0.1 | Railway domain |
| Database | Local PostgreSQL | Railway PostgreSQL |
| Static files | Django dev server | WhiteNoise |
| Email backend | Console | SMTP (Railway) |
| `SECURE_SSL_REDIRECT` | False | True |

## Useful Admin URLs (Development)

- http://localhost:8000/admin/ — Django admin
- http://localhost:8000/api/docs/ — Swagger UI (OpenAPI)
- http://localhost:8000/api/schema/ — OpenAPI schema download
- http://localhost:8000/accounts/login/ — Login page
