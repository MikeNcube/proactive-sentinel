# Security Test Checklist — Proactive Sentinel
# For management review and penetration testing

## Authentication Tests
[ ] Attempt login with wrong password 10 times — account must lock
[ ] Attempt login with expired token — must return 401
[ ] Attempt to use token from different tenant — must return 403
[ ] Attempt to access admin endpoint as regular user — must return 403
[ ] Attempt SQL injection in login form — must be rejected
[ ] Attempt XSS in all input fields — must be sanitized

## Tenant Isolation Tests
[ ] Log in as Tenant A, attempt to read Tenant B data — must fail
[ ] Attempt to modify tenant ID in request — must be rejected
[ ] Attempt to access another tenant dashboard URL — must redirect

## API Security Tests
[ ] Call every endpoint without authentication — all must return 401
[ ] Call every endpoint with expired JWT — all must return 401
[ ] Exceed rate limit — must return 429 with retry header
[ ] Send oversized payload (10MB+) — must return 413
[ ] Send malformed JSON — must return 400 with safe message
[ ] Attempt path traversal in file parameters — must be rejected

## Data Protection Tests
[ ] Confirm PII fields are masked in logs
[ ] Confirm database passwords are not in any log
[ ] Confirm API keys are not in any response
[ ] Confirm audit log captures all admin actions
[ ] Confirm audit log cannot be deleted by non-IT

## Availability Tests
[ ] Simulate 1000 concurrent requests — service must stay up
[ ] Kill and restart the service — must recover in under 60 seconds
[ ] Send 10000 events in 10 seconds — must queue correctly
[ ] Test health endpoint under load — must always return 200
