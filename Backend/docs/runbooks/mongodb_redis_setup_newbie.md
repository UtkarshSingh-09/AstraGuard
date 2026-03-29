# MongoDB + Redis Setup (Beginner Guide)

## 1) MongoDB Atlas
1. Create account: https://www.mongodb.com/atlas
2. Create free cluster (M0).
3. Create DB user (`Database Access`).
4. Add IP allowlist (`Network Access`) - for dev, allow current IP.
5. Copy connection string.
6. In `.env` set:
   - `MONGODB_URI=<atlas-connection-string>`
   - `MONGODB_DB_NAME=astraguard`

## 2) Redis
Option A (local):
1. Install redis locally.
2. Start redis server (`redis-server`).
3. Set `.env`: `REDIS_URL=redis://localhost:6379/0`

Option B (Redis Cloud):
1. Create free instance.
2. Copy redis URL.
3. Set `.env` accordingly.

## 3) Install dependencies
```bash
cd /Users/theankit/Documents/AK/AstraGuard/services/backend
pip install -r requirements.txt
```

## 4) Run backend
```bash
uvicorn app.main:app --reload
```

## 5) Verify health
Open:
`GET /health`

Expected:
- `mongo_ready=true` if Mongo connected
- `redis_ready=true` if Redis connected

## 6) Collections auto-used
- `users`
- `sessions`
- `audit_logs`
- `interventions`
