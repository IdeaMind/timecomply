# DCAA Timekeeping Requirements

## What is DCAA?
The Defense Contract Audit Agency (DCAA) audits government contractors to ensure labor costs charged to government contracts are accurate and allowable. Companies with government contracts must maintain timekeeping systems that satisfy DCAA audit standards.

## Key DCAA Timekeeping Requirements

### 1. Daily Time Recording
- Employees **must** record time **daily** — not reconstructed from memory after the fact
- The system should track when entries are created (timestamp) to demonstrate daily recording
- Late entries should be flagged or require a supervisor acknowledgment

### 2. All Time Must Be Accounted For
- The full workday must be entered — not just billable hours
- Common charge codes include: direct labor, overhead/G&A, B&P (bid and proposal), IR&D, leave (vacation, sick, holiday)
- The sum of time entries for a day does not need to equal exactly 8 hours, but gaps in a workday should be flagged

### 3. Employee Certification
- Employees must certify their timesheet before submission, attesting the hours are accurate

### 4. Supervisory Review and Approval
- A designated supervisor must review and approve each timesheet
- The approver should be a different person than the employee (self-approval must be blocked)
- Backup approvers must be configured so no timesheet is stuck without an approver

### 5. Immutable Audit Trail
- **Every** change to time data must be logged: who changed it, when, what was the original value, what is the new value
- The audit log must be append-only — no entries can ever be deleted or modified
- Audit records must include the IP address of the actor

### 6. Corrections Must Be Documented
- Once a timesheet is approved, time entries cannot simply be edited
- Corrections require a formal **Correction Request** with:
  - Reason code (e.g., `ERRONEOUS_CHARGE`, `WRONG_PROJECT`, `MISSING_HOURS`, `SYSTEM_ERROR`)
  - Written explanation
  - Supervisor re-approval
- Correction requests are themselves audited

### 7. Timesheet Locking
- Approved timesheets are **locked** — no direct edits allowed
- The system must physically prevent modification of locked timesheets, not just warn
- Locking should happen automatically after approval or after a configurable grace period

### 8. No Retroactive Changes Without Documentation
- Employees cannot backdate entries silently
- Any entry entered after the close of a period must be flagged
- Supervisors are notified of any late or retroactive entries

### 9. Unique Identification
- Each timesheet must be uniquely identifiable (UUID)
- Each time entry must be uniquely identifiable
- The system must maintain an unbroken chain of entries

### 10. Access Controls
- Only the employee can enter their own time
- Only designated approvers can approve (not the employee themselves)
- Company admins can override in exceptional cases but must have audit trail
- System administrators cannot manipulate time data without leaving an audit record

---

## Implementation in TimeComply

| DCAA Requirement | TimeComply Implementation |
|------------------|--------------------------|
| Daily recording | `created_at` timestamps on `TimeEntry`; late-entry flagging |
| All time accounted | Validation rules checking for unallocated time periods |
| Employee certification | Submission confirmation step with checkbox attestation |
| Supervisory approval | `ApproverRelationship` model; `Timesheet.status` workflow |
| Audit trail | `audit.AuditLog` — append-only, all model changes captured |
| Corrections documented | `timesheets.CorrectionRequest` with reason codes |
| Timesheet locking | `status=locked`; model-level save() override prevents changes |
| Unique identification | UUID primary keys on all relevant models |
| Access controls | Role-based permissions enforced in views and API |

---

## DCAA Reason Codes for Corrections

| Code | Description |
|------|-------------|
| `ERRONEOUS_CHARGE` | Time was charged to the wrong project/contract |
| `MISSING_HOURS` | Hours were accidentally omitted |
| `DUPLICATE_ENTRY` | Same time was entered twice |
| `WRONG_DATE` | Entry was placed on the wrong date |
| `SYSTEM_ERROR` | System malfunction caused incorrect entry |
| `EMPLOYEE_ERROR` | General employee keying error |
| `CONTRACT_CHANGE` | Contract number changed retroactively |
| `OTHER` | Other — detailed notes required |

---

## References
- FAR 31.201-2: Determining allowability
- FAR 31.201-3: Determining reasonableness
- DCAA Audit Manual Chapter 6: Incurred Cost Audits
- DCAA Audit Manual Chapter 5: Internal Controls
- DCAA Information for Contractors (pamphlet 7641.90)
