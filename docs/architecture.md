# TimeComply Architecture

## System Overview

TimeComply is a multi-tenant SaaS application. Each customer is a **Company** (tenant). Users belong to one company and all data is isolated by company. The system is deployed on Railway using PostgreSQL.

---

## Application Layer Structure

```
apps/
├── accounts/       User identity, social OAuth, profiles, invitations
├── companies/      Company (tenant) lifecycle, membership, settings
├── projects/       Charge codes, projects, contract types
├── timesheets/     Time entry, weekly timesheet lifecycle, pay period management
├── approvals/      Approval workflow engine, approver assignments
├── audit/          Immutable audit log (all data changes)
├── billing/        SaaS subscription, trial management, sales pricing overrides
└── api/            DRF REST API, OpenAPI schema, serializers, routers
```

---

## Data Model

### Core Entities

#### `companies.Company`
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| name | CharField | Display name |
| slug | SlugField | Unique URL-safe identifier |
| is_active | BooleanField | Soft-disable whole tenant |
| settings | JSONField | Company-level config: `period_type` (weekly/biweekly/semimonthly/monthly), `auto_close_hours` (nullable), `timezone` |
| created_at | DateTimeField | Auto |
| updated_at | DateTimeField | Auto |

Default settings: `{"period_type": "weekly", "auto_close_hours": null, "timezone": "America/New_York"}`

#### `companies.CompanyMembership`
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| user | OneToOneField → User | One company per user |
| company | FK → Company | |
| role | CharField | choices: `admin`, `approver`, `employee` |
| is_period_manager | BooleanField | Additive flag — can open/close pay periods |
| is_active | BooleanField | |
| invited_by | FK → User | nullable |

A user can only belong to **one** company (OneToOneField).

#### `accounts.UserProfile`
Extended user data linked 1:1 to Django's `auth.User`.
| Field | Type | Notes |
|-------|------|-------|
| user | OneToOneField → User | |
| company | FK → Company | Denormalized for convenience |
| timezone | CharField | User's local timezone |
| phone | CharField | nullable |

#### `approvals.ApproverRelationship`
Defines who approves whose timesheets.
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| employee | FK → User | The person being approved |
| company | FK → Company | For scoping |
| primary_approver | FK → User | Required |
| is_active | BooleanField | |

#### `approvals.BackupApprover`
| Field | Type | Notes |
|-------|------|-------|
| relationship | FK → ApproverRelationship | |
| approver | FK → User | |
| priority | IntegerField | Order of fallback |

#### `projects.Project`
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| company | FK → Company | |
| code | CharField | e.g. "P001", "OVERHEAD" |
| name | CharField | |
| contract_type | CharField | choices: `cost_plus`, `fixed_price`, `t_m`, `overhead`, `leave` |
| is_active | BooleanField | |
| is_billable | BooleanField | |

#### `timesheets.TimePeriod`
Defines pay period boundaries. Period type varies by company (weekly/biweekly/semimonthly/monthly).
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| company | FK → Company | |
| start_date | DateField | |
| end_date | DateField | |
| period_type | CharField | choices: `weekly`, `biweekly`, `semimonthly`, `monthly` |
| status | CharField | choices: `open`, `closed` |
| auto_close_hours | IntegerField | nullable; N hours after last approval → auto-close |

#### `timesheets.Timesheet`
One timesheet per employee per period.
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| employee | FK → User | |
| company | FK → Company | |
| period | FK → TimePeriod | |
| status | CharField | See state machine below |
| submitted_at | DateTimeField | nullable |
| approved_by | FK → User | nullable |
| approved_at | DateTimeField | nullable |
| rejection_reason | TextField | nullable |

Unique constraint: `(employee, period)`.

#### `timesheets.TimeEntry`
Individual time records within a timesheet.
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| timesheet | FK → Timesheet | |
| project | FK → Project | |
| date | DateField | Must be within timesheet's period |
| hours | DecimalField | max_digits=5, decimal_places=2; non-negative |
| notes | TextField | nullable; required for certain project types |
| is_correction | BooleanField | True if this replaced a previous entry |

#### `timesheets.CorrectionRequest`
Documents corrections to approved timesheets.
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| original_entry | FK → TimeEntry | |
| new_hours | DecimalField | |
| reason_code | CharField | choices: see DCAA reason codes |
| reason_notes | TextField | |
| status | CharField | choices: `pending`, `approved`, `rejected` |
| requested_by | FK → User | |
| reviewed_by | FK → User | nullable |

#### `audit.AuditLog`
Immutable record of all data changes.
| Field | Type | Notes |
|-------|------|-------|
| id | BigAutoField | Sequential for ordering |
| company | FK → Company | nullable (for system events) |
| user | FK → User | Who made the change; nullable for system |
| action | CharField | choices: `create`, `update`, `delete` |
| model_name | CharField | e.g. "timesheets.Timesheet" |
| object_id | CharField | String PK of changed object |
| changes | JSONField | `{"field": [old, new]}` |
| timestamp | DateTimeField | auto_now_add, indexed |
| ip_address | GenericIPAddressField | nullable |

AuditLog is **append-only**. No updates or deletes ever.

---

## Timesheet State Machine

```
DRAFT ──submit──► SUBMITTED ──approve──► APPROVED ──auto/admin──► LOCKED
                       │                     │
                    reject                 correction
                       │                   request
                       ▼                     │
                     DRAFT ◄─────────────────┘
```

| State | Description |
|-------|-------------|
| `draft` | Employee is entering time; editable |
| `submitted` | Sent to approver; read-only for employee |
| `approved` | Approved by supervisor; triggers auto-lock timer |
| `locked` | Immutable; corrections require CorrectionRequest |
| `rejected` | Returned to employee with reason; employee can edit and resubmit |

---

## Authentication & Multi-Tenancy

### Auth Flow
1. New user registers with email or social OAuth (Google/Microsoft)
2. If social login, allauth handles token exchange
3. Post-signup: user is redirected to "create or join company" flow
4. If joining via invitation, the invite token links them to the company
5. All subsequent requests have `request.user.profile.company` available via middleware

### Social Providers
- **Google Workspace**: `allauth.socialaccount.providers.google` — restrict to workspace domains in settings
- **Microsoft 365**: `allauth.socialaccount.providers.microsoft` — restrict to org tenant

### Company Middleware
`CompanyMiddleware` attaches `request.company` on every authenticated request. All views and API viewsets use `self.request.company` to scope querysets.

---

## REST API Design

Base URL: `/api/v1/`

| Resource | Endpoint | Methods |
|----------|----------|---------|
| Companies | `/api/v1/companies/` | GET, PATCH |
| Members | `/api/v1/members/` | GET, POST, DELETE |
| Projects | `/api/v1/projects/` | CRUD |
| Time Periods | `/api/v1/periods/` | GET, POST |
| Timesheets | `/api/v1/timesheets/` | GET, POST |
| Time Entries | `/api/v1/timesheets/{id}/entries/` | CRUD |
| Approvals | `/api/v1/timesheets/{id}/approve/` | POST |
| Rejections | `/api/v1/timesheets/{id}/reject/` | POST |
| Corrections | `/api/v1/corrections/` | CRUD |
| Audit Log | `/api/v1/audit/` | GET (read-only) |
| OpenAPI Schema | `/api/schema/` | GET |
| Swagger UI | `/api/docs/` | GET |

All endpoints require authentication. All responses are scoped to the user's company.

---

## Deployment Architecture

```
GitHub ──push──► GitHub Actions (CI) ──pass──► Railway (staging)
                                                     │
                       git tag ────────────────► Railway (production)
```

### Railway Services
- **Web**: Django app (Gunicorn)
- **Database**: PostgreSQL (managed by Railway)
- **Static files**: Served via WhiteNoise (no separate CDN needed initially)

---

## Frontend Approach

### CSS — Milligram
[Milligram](https://milligram.io/) is the chosen CSS framework. It is ~2KB minified, provides clean typography, a simple flexbox grid, and sensible form styles — enough to produce a professional-looking UI without framework bloat.

- Milligram is loaded via CDN link in `templates/base.html`
- Custom overrides and app-specific styles live in `static/css/main.css`
- Do **not** add Bootstrap, Tailwind, Bulma, or any other CSS framework
- Milligram can be replaced with a richer framework later if needed — keeping it minimal now avoids lock-in and keeps templates clean

### JavaScript
- Vanilla JS only (`static/js/main.js`)
- No React, Vue, jQuery, Alpine, or HTMX in v1
- JS is limited to UX polish: client-side form validation feedback, simple show/hide interactions

### Environment Config
- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `DATABASE_URL` — injected by Railway
- `SECRET_KEY` — Railway environment variable
- `ALLOWED_HOSTS` — Railway domain

---

## Security Considerations
- CSRF protection enabled on all form-based views
- API uses token authentication (DRF TokenAuth or SessionAuth)
- Company data isolation enforced at queryset level (not just view level)
- Audit log is append-only (no delete permission in any role)
- Social OAuth tokens are not stored beyond what allauth needs
- `DEBUG=False` enforced in production settings
- `SECURE_SSL_REDIRECT=True` in production
- `ALLOWED_HOSTS` strictly set per environment
