# TimeComply — System Specification

High-level requirements as understood by the product owner. This document captures *what* the system does, not *how* it is built.

---

## Authentication & Access

- Users can create an account with an email address and password
- Users can log in with a Google Workspace account (single sign-on)
- Users can log in with a Microsoft 365 account (single sign-on)
- Invited users who don't have an account are taken to a sign-up page, not a login page
- Password reset is available via email

---

## Companies (Tenants)

- A company is the root of all data — nothing is shared across companies
- A new company is created by registering through the app
- Company admins can update their company name and settings
- Each company has its own independent set of users, projects, and timesheets

---

## Users & Roles

Every user belongs to exactly one company. Permissions are **independent flags** — a user can hold any combination of them, or none at all. There is no single "role" that a user must have.

| Permission | What it enables |
|---|---|
| **Employee** | Required to fill out and submit timesheets. Not all users need this — e.g. a third-party admin consultant never fills out a timesheet. |
| **Approver** | Can approve or reject timesheets. Which timesheets they can approve is controlled by explicit approver relationships (see Approval Workflow), not by this flag alone. |
| **Admin** | Can manage users, projects, labor categories, and company settings. An admin may have no employee or approver responsibilities. |
| **Period Manager** | Can open and close pay periods. Could be a human, an automated process, or an AI agent — no timesheet requirement. |

Examples of valid combinations:
- A staff accountant at a government contractor: Employee + Admin (fills out time AND manages the system)
- A third-party time-keeping consultant: Admin only (sets up the system, never charges hours)
- A senior engineer: Employee + Approver (fills out their own time AND approves their team's)
- An automated period management bot: Period Manager only
- A new invite with no permissions yet assigned: none (pending admin configuration)

All invitations create users with no permissions by default; an admin assigns permissions after the user joins.

---

## User Invitations

- Company admins can invite new users by email address
- An invitation generates a unique signup link sent to the invitee
- Admins can revoke a pending invitation before it is accepted
- Accepting an invitation creates an account and adds the user to the company as an employee

---

## Projects & Labor Categories

- Admins define the projects and labor categories employees can charge time against
- Each entry has a unique alphanumeric timekeeping code specific to the company
- Each entry has an optional Chart of Accounts (COA) code for accounting integration
- Labor categories follow a hierarchical tree structure (parent/child relationships) to support DCAA Total Labor Accounting
- The system provides a default labor type tree out of the box (see below), which companies can customize
- Certain categories are automatically pre-loaded onto every employee's timesheet (e.g. Holiday, Vacation, Sick/Jury Duty, Administrative)
- Admins can deactivate (archive) a project or labor category; archived items are hidden from time entry but can be reactivated by an admin
- Admins can permanently delete a project or labor category (separate from archive)
- Project codes must be unique within a company; duplicate name+category+billable combinations should warn the user
- After creating a project, the user is returned to the edit form to review. After editing a project, the user is returned to the project list

### Default Labor Type Tree

```
Total Labor Hours
├── Direct Labor
│   └── (company-defined contract projects go here)
├── Indirect Labor
│   ├── Fringe
│   │   ├── Holiday                     [auto-add to timesheets]
│   │   ├── Vacation                    [auto-add to timesheets]
│   │   └── Sick Leave / Jury Duty      [auto-add to timesheets]
│   ├── Overhead
│   │   ├── Technical Training
│   │   ├── Internal Lab Maintenance
│   │   └── Supervision of Technical Staff
│   └── G&A
│       ├── Accounting & Payroll Processing
│       ├── Administrative               [auto-add to timesheets]
│       ├── Training
│       ├── B&P (Bid & Proposal)
│       └── IR&D (Independent R&D)
└── Other Labor (unallowable)
    ├── Internal Morale and Welfare
    └── Entertainment Planning
```

---

## Pay Periods

- The company's pay period type (weekly, biweekly, semimonthly, or monthly) is a **company-level setting**, configured in Company Settings — not chosen each time a period is created
- When creating a new pay period, only the **start date** is entered; the end date is automatically calculated from the start date and the company's period type
- **Auto-close** (automatically close the period after all timesheets are approved) is a company-level setting, not a per-period field
- **Auto-open**: a company can enable automatic opening of future periods. When enabled, periods can be pre-created and are visible to employees as a read-only calendar view before they officially open. Employees cannot add or edit entries until the period opens.
- New periods begin in **future** state — visible to employees but not editable — and transition to **open** at their start date (manually by a Period Manager, or automatically if auto-open is enabled)
- Pay periods can be opened and closed manually by a Period Manager
- A Period Manager or admin can **delete** a pay period that was created in error, provided it contains no timesheet entries
- The pay period management page shows the company's period type for reference but does not allow changing it there — period type changes happen in Company Settings

---

## Time Entry

- Time entry is presented as an **editable weekly grid**: rows are labor categories, columns are the days of the pay period, cells contain hours
- Each cell specifies an hour amount only — notes are not part of time entry
- Hours cannot be negative; a single entry cannot exceed 24 hours
- Hours in a cell must fall within the current open pay period's dates
- Leave time (vacation, sick, holiday) is entered just like any other charge code — no balance tracking in v1
- An **Add Row** button at the bottom of the grid opens a picker so employees can add another labor category to their timesheet
- **Preset categories**: every employee has a personal list of preset labor categories that automatically appear as rows in their timesheet grid. Admins can configure presets for any employee; employees can manage their own presets (limited to non-archived categories). Pre-populated auto-add categories (Holiday, Vacation, etc.) are separate from and in addition to personal presets.
- **Timesheet navigation**: employees can move between pay periods using Previous, Current, and Next buttons. Past timesheets — regardless of state (draft, submitted, approved, locked) — are viewable in a read-only format. Future periods in **future** state show a read-only view. The Current button always navigates to the open period's timesheet.
- When no pay period is open, the employee sees a friendly message rather than an error

---

## Timesheet Lifecycle

- A timesheet is automatically created the first time an employee enters time for a pay period
- Timesheet states: Draft → Submitted → Approved → Locked (or Rejected → Draft)
- States are never skipped
- Employees can edit entries only while the timesheet is in Draft status
- Rejected timesheets return to Draft so the employee can make corrections

---

## Timesheet Submission & Certification

- Employees review their completed timesheet and certify accuracy before submitting
- Certification statement: *"I certify that the hours recorded on this timesheet are accurate and complete to the best of my knowledge."*
- Once submitted, the timesheet is locked for editing until approved or rejected

---

## Approval Workflow

- Each employee has a designated primary approver and optionally one or more backup approvers
- Approvers see a queue of submitted timesheets for their direct reports
- Approvers can approve or reject; rejection requires a written reason
- An employee cannot approve their own timesheet

### Approver Setup UI

- The approver setup interface is **supervisor-centric**: an admin selects a supervisor, then sees all employees they can approve and uses a multi-select list to quickly assign or remove multiple employees at once
- This replaces the employee-centric approach of configuring one approver per employee individually

### Backup Approver Inheritance

- An admin can create a **backup approver rule** that designates a backup approver for all employees under a given supervisor (e.g. the COO is backup for all supervisors under them)
- When this rule exists:
  - Every employee currently assigned to the supervisor automatically has the backup approver added
  - When a new employee is later assigned to the supervisor, they **immediately** inherit the backup approver — no additional admin action required
  - When an employee is removed from the supervisor's group, the inherited backup approver is **automatically removed**
- Rules are permanent until explicitly deleted by an admin
- Multiple backup approver rules can stack (an employee can inherit backups from multiple rules)

---

## Timesheet Locking

- Approved timesheets are automatically locked — no further edits are possible
- Locking is enforced at the data level, not just the UI

---

## Corrections (DCAA Requirement)

- If a locked timesheet contains an error, the employee submits a formal correction request
- Correction requests include a DCAA reason code
- The original entry is always preserved — corrections create a new entry, never overwrite the original
- Correction requests go through the same approval workflow as timesheets

---

## Audit Log (DCAA Requirement)

- Every change to time data is recorded in an append-only audit log
- The log captures: who made the change, what changed, the original value, the new value, and the timestamp
- Audit records cannot be edited or deleted

---

## REST API

- A REST API is available for integrations and accounting system connections
- The API covers: company info, members, projects/labor categories, timesheets, and time entries
- All API data is scoped to the authenticated user's company
- API documentation is auto-generated and browsable at `/api/schema/swagger-ui/`

---

## SaaS Billing (Planned — M7)

- Billing is per user per month
- New companies receive a 90-day free trial
- No free tier after trial
- Sales staff can apply custom pricing overrides per company
