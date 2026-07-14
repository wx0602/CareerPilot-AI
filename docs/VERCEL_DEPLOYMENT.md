# Vercel deployment

The public deployment uses two Vercel projects from the same repository.

## 1. Provision Postgres

Create a Neon or Supabase Postgres database from the Vercel Marketplace and connect it to the backend project. Copy its pooled connection string and expose it as:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Run the migrations once from the repository root before serving traffic:

```powershell
$env:APP_ENV="production"
$env:DATABASE_URL="postgresql+psycopg://..."
npm run db:migrate
```

## 2. Deploy the backend project

Create a Vercel project with the repository root as its Root Directory. The root `app.py`, `requirements.txt`, and `vercel.json` are the backend entrypoint and deployment configuration.

Add every variable from `backend/.env.vercel.example` under Project Settings -> Environment Variables. At minimum, replace:

- `DATABASE_URL`
- `CORS_ORIGINS`
- `DEMO_PASSWORD`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

The question database, Chroma directory, and uploaded source files use `/tmp` on Vercel. They are disposable runtime files. User accounts, parsed material contexts, answers, favorites, and reports are persisted in Postgres.

After deployment, verify:

```text
https://YOUR_BACKEND_DOMAIN/health
https://YOUR_BACKEND_DOMAIN/docs
```

## 3. Deploy the frontend project

Create or update the frontend Vercel project with `frontend` as its Root Directory. Add:

```text
VITE_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
```

Redeploy after changing the variable. Do not put database credentials or LLM keys in any `VITE_` variable because Vite exposes them to browsers.

## 4. CORS and uploads

Set `CORS_ORIGINS` to the exact production frontend origin without a trailing slash. Multiple origins are comma-separated. `CORS_ORIGIN_REGEX` is optional and should only be used for trusted preview-domain patterns.

Vercel Function request bodies are limited to 4.5 MB, so the production template limits uploads to 4 MB. Larger uploads require direct-to-object-storage uploads such as Vercel Blob or S3.
