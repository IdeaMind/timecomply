# TimeComply - Claude Code Project Instructions

## Project Overview
TimeComply is a DCAA-compliant timesheet SaaS application for small government contractors. It enables companies to track employee time, manage charge codes, enforce DCAA compliance rules, and streamline timesheet approval workflows.

## Tech Stack
- **Framework**: Django (Python 3.12+)
- **Package Manager**: `uv` — NEVER use `pip install` globally. Always use `uv add` or `uv run`.
- **Database**: PostgreSQL (provided by Railway)
- **Auth**: `django-allauth` (email/password + Google Workspace + Microsoft 365 OAuth)
- **REST API**: Django REST Framework + `drf-spectacular` (OpenAPI 3.0 schema generation)
- **CSS**: [Milligram](https://milligram.io/) — a minimal CSS framework (~2KB). Use it for layout, typography, and form styling. Do not add Bootstrap, Tailwind, or other CSS frameworks. Custom styles go in `static/css/main.css` layered on top of Milligram.
- **JavaScript**: Vanilla JS only — no React, Vue, jQuery, or other frameworks
- **Testing**: `pytest-django` with `pytest-cov` — extensive unit tests required
- **Linting/Formatting**: `ruff` (both linting and formatting)
- **Deployment**: Railway (staging + production environments)

## Project Structure
```
timecomply/                    ← git root
├── config/                    ← Django project package
│   ├── settings/
│   │   ├── base.py            ← Shared settings
│   │   ├── development.py     ← Dev overrides
│   │   └── production.py      ← Prod overrides (Railway env vars)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/              ← User auth, social login, user profiles
│   ├── companies/             ← Multi-tenant company management
│   ├── projects/              ← Charge codes, contract types, projects
│   ├── timesheets/            ← Time entries, weekly timesheet lifecycle
│   ├── approvals/             ← Approval workflow engine
│   ├── audit/                 ← Immutable audit log
│   └── api/                   ← DRF viewsets, serializers, OpenAPI router
├── templates/                 ← Django HTML templates
│   ├── base.html
│   ├── accounts/
│   ├── companies/
│   ├── timesheets/
│   └── approvals/
├── static/
│   ├── css/main.css
│   └── js/main.js
├── tests/                     ← All tests live here, mirroring apps/ structure
│   ├── conftest.py
│   ├── accounts/
│   ├── companies/
│   ├── projects/
│   ├── timesheets/
│   ├── approvals/
│   ├── audit/
│   └── api/
├── docs/                      ← Technical documentation
├── .github/
│   ├── workflows/
│   │   ├── ci.yml             ← PR checks: lint, test, coverage
│   │   ├── cd.yml             ← Deploy on merge/tag
│   │   └── ai-implement.yml   ← AI-driven issue implementation
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── CLAUDE.md                  ← This file
├── pyproject.toml             ← uv project config, ruff config, pytest config
└── railway.json               ← Railway deployment config
```

## Development Commands
```bash
# Install dependencies
uv sync

# Run development server
uv run python manage.py runserver

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=apps --cov-report=term-missing

# Lint and format check
uv run ruff check .
uv run ruff format --check .

# Auto-fix lint issues
uv run ruff check --fix .
uv run ruff format .

# Create migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser
```

## Environment Variables
All secrets are provided via environment variables. Never hardcode secrets. Key variables:
```
DJANGO_SETTINGS_MODULE=config.settings.production  # or development
SECRET_KEY=...
DATABASE_URL=...  # PostgreSQL connection string from Railway
ALLOWED_HOSTS=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
```

## Coding Standards

### General Rules
- Follow existing patterns in the codebase before inventing new ones
- Every new model must have a corresponding migration
- Every new view or serializer must have unit tests
- Never commit secrets or environment-specific values
- Keep functions small and single-purpose
- Use Django's built-in utilities before third-party packages

### Models
- All models inherit from `TimeStampedModel` (provides `created_at`, `updated_at`)
- All models have a `__str__` method
- Use `UUIDField` as primary key for all public-facing models
- Company-scoped models must have a ForeignKey to `Company` and include company in their `Meta.constraints`

### Tests
- Test files mirror the app structure under `tests/`
- Use `pytest` fixtures defined in `tests/conftest.py`
- Use `factory_boy` for test data factories
- Test both happy path and error conditions
- Minimum 80% coverage required; 90%+ preferred
- API tests must test authentication, authorization, and data isolation between companies

### API (REST)
- All API endpoints require authentication (no anonymous access except auth endpoints)
- All endpoints are company-scoped (users only see their company's data)
- Use DRF's `ModelViewSet` where appropriate
- Document all serializer fields
- OpenAPI schema must be kept accurate (drf-spectacular decorators as needed)

### Templates
- Extend `base.html`
- Use Django's template tags and filters
- Milligram is loaded via CDN in `base.html`; custom overrides go in `static/css/main.css`
- No inline styles
- Minimal JS: only for UX polish (form validation feedback, etc.)

## DCAA Compliance Context
DCAA (Defense Contract Audit Agency) has specific requirements for timekeeping:
1. **Daily recording**: Employees must record time daily, not reconstruct later
2. **All time accounted for**: Time for the full workday must be entered (including non-billable)
3. **Supervisory approval**: Timesheets require supervisor review and approval
4. **Immutable audit trail**: All changes must be logged with original values
5. **Corrections documented**: Any correction to approved time needs a reason code
6. **Locking**: Timesheets are locked after approval; corrections require a new process
7. **No negative time**: Time entries cannot be negative

## Multi-Tenancy
- Data is isolated per `Company` using ForeignKey relationships
- All querysets in views and APIs must be filtered by `request.user.company`
- Company middleware injects the user's company into every request
- No cross-company data leakage is acceptable — this is a security requirement

## AI Implementation Workflow
When implementing a GitHub issue:
1. Read the issue carefully, especially Acceptance Criteria and Implementation Notes
2. Write failing tests first (TDD where practical)
3. Implement the feature to make tests pass
4. Run `uv run ruff check . && uv run ruff format .` to fix lint/format
5. Run `uv run pytest` to confirm all tests pass
6. Update migrations if models changed
7. Do not create unnecessary abstractions or over-engineer
8. Keep PRs focused: one issue = one PR
