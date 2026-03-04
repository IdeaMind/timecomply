---
name: AI-Implementable Feature
about: A well-specified feature designed to be implemented by Claude Code via GitHub Actions
title: "[FEATURE] "
labels: ["type:feature", "ready-for-ai"]
assignees: []
---

## Summary
<!-- One paragraph describing the feature and why it's needed -->


## Acceptance Criteria
<!-- What must be true for this issue to be considered complete? Be specific and testable. -->
- [ ]
- [ ]
- [ ]

## Technical Scope
<!-- Which files/apps will be created or modified? -->

**Apps affected:**
- `apps/` <!-- list relevant apps -->

**New files to create:**
-

**Files to modify:**
-

## Implementation Notes
<!-- Detailed technical guidance for Claude Code. Include: model names, field names, view patterns, URL patterns, template paths, test patterns. The more specific, the better. -->

### Models
<!-- Describe any new or modified models -->

### Views / URLs
<!-- Describe any new views and their URL patterns -->

### Templates
<!-- Describe any new templates needed -->

### API Endpoints
<!-- If this adds API endpoints, describe them here -->

### Tests Required
<!-- List the specific tests that must be written -->
- `tests/.../test_models.py` — test that...
- `tests/.../test_views.py` — test that...

## Human Testing Notes
<!--
IMPORTANT: These notes are surfaced in the PR and tell a human what to manually verify.
Include step-by-step instructions for manual testing in a browser or via API.
-->

### Before Implementation
<!-- Any setup the tester should do before the AI runs -->
-

### After Implementation — Manual Verification Steps
1.
2.
3.

### Edge Cases to Verify
-

### Rollback / Cleanup
<!-- How to undo this if something goes wrong -->
- Run `uv run python manage.py migrate --fake <app> <previous_migration>` if migration rollback needed

---

**Milestone:** <!-- M0 | M1 | M2 | M3 | M4 | M5 | M6 -->
**Size:** <!-- XS | S | M | L | XL -->
