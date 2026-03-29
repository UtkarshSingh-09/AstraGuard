# Env Contract for Utkarsh Integration

Share via secret manager, not git.

## Required
- `MONGODB_URI` (Atlas `mongodb+srv://...`)
- `MONGODB_DB_NAME`
- `REDIS_URL`
- `SEBI_DISCLAIMER`

## For AI Layer
- `GROQ_API_KEY`
- `GROQ_BASE_URL` (optional, default `https://api.groq.com/openai/v1`)
- `GROQ_MODEL` (optional, default `llama-3.3-70b-versatile`)
- `GROQ_TIMEOUT_SECONDS` (optional, default `20`)
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_WHATSAPP_FROM`
- `CHROMADB_PERSIST_DIR` (if using regulator RAG)

## Validation
- `/health` should show:
  - `mongo_ready=true`
  - `redis_ready=true`
  - `atlas_configured=true`
