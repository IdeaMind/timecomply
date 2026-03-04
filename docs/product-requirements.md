# TimeComply Product Requirements

This document captures product decisions made during planning. It is the source of truth for key business rules.

---

## Workweek and Pay Period Configuration

### Default Workweek
- **Default**: Monday through Friday
- **Hours**: No fixed daily/weekly hour requirement from DCAA's perspective — DCAA only requires accurate logging, not a minimum
- **Configurable**: Companies can adjust the number of working days and expected hours per week in their company settings (future enhancement — start with Mon–Fri default)

### Pay Period Types
Companies choose one of four pay period types when setting up their account:

| Type | Description |
|------|-------------|
| `weekly` | 7 days; starts on Monday by default |
| `biweekly` | 14 days; starts on Monday by default |
| `semimonthly` | Twice a month: 1st–15th and 16th–last-day |
| `monthly` | Full calendar month |

The pay period type is stored on the `Company` settings. The system uses it to auto-generate periods.

### Pay Period Open/Close Management
Two modes, configurable per company:

**Manual mode (default)**: A designated "Period Manager" user opens and closes periods from the `/periods/` management screen. This role can be assigned to any company member.

**Automatic mode**:
- Period **opens** automatically on the first day of the period (midnight company timezone)
- Period **closes** automatically N hours after the last timesheet in the period is approved (N is configurable, default = 24 hours)
- If not all timesheets are submitted/approved by the expected close date, period remains open and the Period Manager is notified

### Period Manager Role
A new company role: `period_manager`. Can be assigned alongside employee/approver role (additive). Responsible for opening/closing periods in manual mode and handling late submissions.

---

## Charge Codes / Projects

### Customer-Defined Codes
Companies define their own charge codes. TimeComply does not impose a specific format or numbering scheme. A charge code has:
- **Code**: Free-form string (e.g., "P001", "GS-12345-CONTRACT-A", "OVH", "LEAVE")
- **Name**: Human-readable description
- **Contract type**: DCAA category (cost_plus, fixed_price, t_m, overhead, leave, bid_proposal, ir_d)

The "code" field is what employees select when entering time. Companies that use contract numbers will use those. Companies that use accounting system codes will use those. TimeComply is agnostic.

---

## Approval Structure

### Default Approver
The default approver for an employee is their supervisor. The approver is configured by a company admin when an employee is onboarded (or whenever the supervisor changes).

### Backup Approvers
- Each employee can have one or more backup approvers (ordered by priority)
- The system does not automatically escalate to backup approvers — the backup is available in the UI for the approver to delegate, or for the admin to reassign
- An approver can approve timesheets for any employee assigned to them — no per-contract restrictions

### Self-Approval
Strictly forbidden. The system must prevent an approver from approving their own timesheet at every level (model, view, API).

---

## Leave Tracking
**Out of scope** for initial release. Leave (vacation, sick, holiday) is handled as a charge code in the timesheet system only — employees charge hours to leave charge codes. No leave balance, accrual, or request management in v1.

---

## Certification Language
When an employee submits a timesheet, they must affirm a certification statement. **Placeholder** (to be finalized by legal/compliance):

> *"I certify that the hours recorded on this timesheet are accurate and complete to the best of my knowledge, and accurately reflect the time I worked on the specified projects and activities during this pay period."*

This will be updated before the first customer goes live.

---

## SaaS Billing Model

### Pricing Structure
- **Per-user pricing**: Billed monthly per active user in a company
- **No free tier**: All customers pay (after trial)
- **Trial period**: Default 90 days free trial from account creation date
- **Sales overrides**: Sales staff can customize pricing per customer:
  - Override price per user
  - Set override duration (specific end date) or make it permanent
  - Add notes documenting the deal

### Billing Models Needed

#### `billing.Subscription`
| Field | Type | Notes |
|-------|------|-------|
| company | OneToOneField → Company | |
| trial_end | DateField | Null = no trial |
| billing_start | DateField | When billing kicks in |
| base_price_per_user | DecimalField | Default per-user monthly price |
| is_active | BooleanField | If False, company is suspended |
| created_at | DateTimeField | |

#### `billing.PricingOverride`
| Field | Type | Notes |
|-------|------|-------|
| subscription | FK → Subscription | |
| price_per_user | DecimalField | Override price |
| override_start | DateField | |
| override_end | DateField | Null = permanent |
| set_by | FK → User | Staff/sales user |
| notes | TextField | Deal notes |

### Sales Staff
Sales staff are system-level users (not company-scoped) who can:
- View all companies and their subscription status
- Set pricing overrides
- Extend trial periods
- Suspend/reactivate companies

This requires a `is_staff` or `is_sales` flag on the User model, and a dedicated sales admin interface.

### Billing Milestone
This feature set is scoped to **M7: SaaS Billing** (to be prioritized after core functionality is validated).

---

## Decisions Still Needed
- [ ] Exact certification language (legal review)
- [ ] Default price per user per month
- [ ] Payment processor (Stripe recommended — future issue)
- [ ] Whether to send billing invoices or integrate with external billing software
- [ ] Whether to implement usage-based metering (e.g., per active user per month) or flat per-seat
