# Failure Matrix (Integration Bug Pass)

## API and Service Failure Behavior

1. FIRE engine error
- Code: `invalid_fire_input` or `fire_engine_failed`
- Behavior: structured error envelope, no crash

2. Tax engine error
- Code: `invalid_tax_input` or `tax_engine_failed`
- Behavior: structured error envelope, no crash

3. Portfolio invalid payload
- Code: `invalid_portfolio_input`
- Behavior: job marked failed and poll endpoint returns error payload

4. Missing job
- Code: `job_not_found`
- Behavior: 404

5. Missing user for intervention
- Code: `user_not_found`
- Behavior: 404

6. Missing audit trace
- Code: `audit_not_found`
- Behavior: 404

7. Mongo/Redis unavailable
- Behavior: API still responds, persistence skipped, `/health` flags readiness

8. AI narration unavailable
- Behavior: deterministic response unaffected; narration fallback can return “Narration unavailable”
