# CLAUDE.md — AI Implementation Guide for TimeComply

TimeComply is a DCAA-compliant timesheet SaaS for small government contractors. Multi-tenant: all data is scoped to a `Company`.

## Commands

```bash
uv run python manage.py runserver     # dev server
uv run python manage.py migrate       # apply migrations
uv run python manage.py makemigrations <app>
uv run pytest                         # run tests
uv run pytest --cov --cov-report=term-missing
uv run ruff check --fix --unsafe-fixes . && uv run ruff format .   # lint + format (run before committing)
```

## Rules

- **Always use `uv`** — never `pip install`, never `python` directly, never global installs
- **Always `uv add`** to add dependencies, `uv add --dev` for dev-only
- **Run `ruff check --fix --unsafe-fixes . && ruff format .`** before every commit — `--unsafe-fixes` is required to catch all fixable errors (e.g. F841)
- **Never commit secrets** — `.env*` files are gitignored
- **Never squash migrations** that have already been applied to staging or production
- **No Bootstrap, Tailwind, or JS frameworks** — CSS is Milligram (CDN) + `static/css/main.css`, JS is vanilla only

## Tech Stack

| Concern | Tool |
|---|---|
| Framework | Django 5.x, Python 3.12 |
| Package manager | `uv` |
| Auth | `django-allauth` (email + Google + Microsoft) |
| API | Django REST Framework + `drf-spectacular` |
| Database | PostgreSQL via `psycopg[binary]` |
| CSS | Milligram (CDN) + custom overrides |
| Testing | `pytest-django` + `factory-boy` |
| Lint/Format | `ruff` |
| Static files | WhiteNoise |
| Deploy | Railway (staging = main branch, production = version tags) |

## Project Structure

```
apps/
  accounts/       # User model extensions
  companies/      # Company + CompanyMembership (tenant root)
  projects/       # Charge codes / projects
  timesheets/     # Time entries + pay periods
  approvals/      # Approval workflow
  audit/          # Append-only audit log
  api/            # DRF API views + routers
config/
  settings/
    base.py       # Shared settings
    development.py
    production.py
    test.py
  urls.py
  wsgi.py
tests/            # Mirror apps/ structure: tests/companies/, tests/timesheets/, etc.
docs/
  developer-guide.md
static/css/main.css
templates/
```

## Architecture Patterns

**Multi-tenancy:** Every model (except `Company` itself) has a FK to `Company`. Never return querysets without filtering by company. A `CompanyMiddleware` (to be implemented) injects `request.company` on every authenticated request.

**Authentication:** allauth handles all auth — email/password login, Google Workspace OAuth, and Microsoft 365 OAuth. Do not build custom auth flows. The underlying user is Django's built-in `auth.User` (no custom user model).

**Roles:** Stored as `role = CharField(choices=ROLE_CHOICES)` on `CompanyMembership`. A user holds exactly one role. `is_period_manager` is an additive boolean flag that can be set independently of role.

| Role | `role` value | Can do |
|---|---|---|
| Employee | `"employee"` | Enter and submit their own timesheets |
| Approver | `"approver"` | Approve/reject timesheets for their reports |
| Admin | `"admin"` | Manage users, charge codes, company settings |
| Period Manager | any role + `is_period_manager=True` | Open and close pay periods |

**Timesheet state machine:** `draft → submitted → approved → locked` (rejected goes back to draft). Never skip states.

**Audit log:** `AuditLog` is append-only — it raises on update or delete if the pk already exists. Do not add `update()` or `delete()` logic to it.

**Corrections:** DCAA requires original entries to be preserved. Use `CorrectionRequest` with a DCAA reason code; never overwrite the original `TimeEntry`.

**Charge codes:** Fully customer-defined. No enforced format.

**Leave tracking:** Not in scope for v1 — modeled as a charge code.

## Settings Selection

| Environment | `DJANGO_SETTINGS_MODULE` |
|---|---|
| Local dev | `config.settings.development` |
| CI | `config.settings.test` |
| Railway staging + prod | `config.settings.production` |

## Views

- Use **function-based views (FBV)** by default — simpler and more readable
- Only use class-based views if there is a strong reason (e.g. a generic list/detail that maps directly to a CBV with no custom logic)
- Templates extend `templates/base.html` using `{% block content %}`
- Keep views thin — business logic belongs in model methods or service functions, not views

## Handling Ambiguity

When implementing an issue and something is underdefined: make a reasonable decision, implement it, and document the decision clearly in the PR description. Do not stop and wait for input.

UI designs may be attached to the issue as HTML mockups. If one is present, follow it. If not, implement a clean, functional UI using Milligram conventions and document what you built in the PR.

## Testing Conventions

- Tests live in `tests/`, mirroring `apps/` (e.g. `tests/companies/test_models.py`)
- Use `factory-boy` for test data — no raw `Model.objects.create()` in tests
- Use `pytest` fixtures, not `unittest.TestCase`
- Aim for 80%+ coverage; CI enforces this
- Use `APIClient` from DRF for API tests (fixture already in `tests/conftest.py`)

## API Conventions

- All endpoints under `/api/`
- OpenAPI schema auto-generated via `drf-spectacular` — add `@extend_schema` decorators when default output is insufficient
- Authentication: session-based (cookie); no JWT
- All list endpoints must be company-scoped

## GitHub Workflow

- Feature branches: `feature/issue-{number}-{short-description}`
- Bug fix branches: `fix/issue-{number}-{short-description}`
- PRs target `main`; CI must pass before merge
- Issues labeled `ready-for-ai` are auto-implemented via `ai-implement.yml`
- Release tags `v{major}.{minor}.{patch}` trigger production deploys
