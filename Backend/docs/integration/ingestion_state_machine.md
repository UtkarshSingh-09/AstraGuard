# Ingestion Agent State Machine (CAMS + Form16)

## States
- `queued`
- `running`
- `awaiting_user_step`
- `downloaded`
- `parsed`
- `complete`
- `failed`

## Allowed Transitions
1. `queued -> running`
2. `running -> awaiting_user_step`
3. `awaiting_user_step -> running`
4. `running -> downloaded`
5. `downloaded -> parsed`
6. `parsed -> complete`
7. `running -> complete`
8. `running -> failed`
9. `awaiting_user_step -> failed`

## Timeout Policy
- portal action timeout: 90s
- user-step timeout: 300s
- retries: 3 attempts with backoff

## Error Policy
- deterministic `error.code` + `error.message`
- never leak secrets in error payload
- always preserve `job_id` for frontend polling continuity

## Fallback Policy
- Any fetch failure -> suggest upload fallback with same workflow context.
