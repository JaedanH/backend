# EthixAI Backend

This repository contains a production‑ready backend for **EthixAI**, a platform
that evaluates, scores and tracks the ethical performance of companies. It
exposes a simple REST API built with FastAPI, stores data in Supabase
(PostgreSQL), and uses OpenAI’s GPT‑3.5 model to compute daily ethics scores.

## Table of Contents

- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Readdy Integration](#readdy-integration)
- [Deployment](#deployment)
- [Cron Scheduling](#cron-scheduling)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Readdy Frontend                      │
│            (consumes JSON from FastAPI backend)           │
└──────────────────────────────────────────────────────────────────┘
                │            ▲              ▲
                │            │              │
                ▼            │              │
┌───────────────────────────────────────────────────────┐
│                   FastAPI Backend (this repo)              │
│ ┌────────────────────────────────────────────────┐ │
│ │        app/main.py – API routes and middleware         │ │
│ │        app/auth.py – API key auth & rate limiting      │ │
│ │        app/supabase.py – REST client for Supabase      │ │
│ │        app/scoring.py – GPT‑3.5 based scoring logic    │ │
│ │        app/models.py – Pydantic schemas                │ │
│ └────────────────────────────────────────────────┘ │
│                      ▲            │                        │
│                      │            │ (async HTTP)           │
└────────────────────────────────────────────────┐
                       │            │
                       ▼            ▼
                 Supabase REST     OpenAI GPT‑3.5
                  (Postgres)        (daily scoring)
```

## Getting Started

1. **Clone the repository** and change into the directory:

   ```sh
   git clone https://github.com/your-user/ethixai-backend.git
   cd ethixai-backend
   ```

2. **Create a Python virtual environment** (optional but recommended):

   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```sh
   pip install -r requirements.txt
   ```

4. **Configure environment variables**. Copy `.env.example` to `.env` and edit
   values, or export the variables in your shell. See [Environment Variables](#environment-variables) for details.

5. **Create the database schema**. Run the SQL file against your Supabase
   project. You can execute it via the SQL editor in the Supabase dashboard or
   via psql:

   ```sh
   psql "$SUPABASE_CONNECTION_URI" -f sql/001_create_tables.sql
   ```

6. **Run the API locally**:

   ```sh
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Navigate to `http://localhost:8000/docs` to see the interactive API docs.

## Environment Variables

The backend relies on several environment variables. These can be placed in a
`.env` file or configured in your deployment platform. Required variables:

| Variable          | Purpose                                                 |
| ----------------- | ------------------------------------------------------- |
| `SUPABASE_URL`    | Base URL of your Supabase project (e.g. `https://xyz.supabase.co`) |
| `SUPABASE_KEY`    | Service role key for Supabase REST (keep secret)       |
| `OPENAI_API_KEY`  | OpenAI API key with access to GPT‑3.5                  |
| `API_KEY`         | Private API key used to authorize admin endpoints       |
| `CORS_ALLOW_ORIGINS` | Comma‑separated list of allowed origins for CORS (default `*`) |

Example `.env` file:

```env
SUPABASE_URL=https://project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
OPENAI_API_KEY=sk-...
API_KEY=supersecretadminkey
CORS_ALLOW_ORIGINS=https://your-readdy-site.com
```

## Database Schema

The Supabase schema is defined in `sql/001_create_tables.sql` and replicated here for reference:

```sql
CREATE TABLE public.companies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  ticker text,
  ethics_score int,
  source_reason text,
  last_updated timestamptz DEFAULT now()
);
CREATE INDEX ON public.companies (name);
```

You can optionally preload data (e.g., S&P 500 companies) with empty scores. Use the Supabase dashboard or CSV import tools.

## API Endpoints

### Public Endpoints

| Method | Path        | Description                                        |
|-------:|------------:|----------------------------------------------------|
| GET    | `/health`   | Returns `{status: "ok"}`. Health check.           |
| GET    | `/companies` | Returns a list of companies. Supports `q` (search on name/ticker), `order` (e.g. `-ethics_score`), `limit`, `offset`. |

### Protected Endpoints

All protected endpoints require an `x-api-key` header matching your `API_KEY`.

| Method | Path                    | Description                                |
|-------:|------------------------:|--------------------------------------------|
| POST   | `/score/{company_id}`   | Rescore a single company via GPT and update the record. |
| POST   | `/score/cron`           | Rescore all companies (used by cron job).  |
| PATCH  | `/companies/{id}`       | Update arbitrary fields on a company (admin only). |

The FastAPI automatic docs are available at `/docs`.

## Readdy Integration

Your Readdy frontend can fetch data from either the FastAPI backend or
directly from Supabase’s REST API.

### Using the FastAPI Backend

Configure a data source in Readdy with:

- **URL**: `https://<API_BASE>/companies?limit=200&order=-ethics_score`
- **Method**: GET
- **Headers**: none (unless you choose to expose a public API key)

This will return an array of company objects with `name`, `ticker`, `ethics_score`, `source_reason`, and `last_updated` fields.

### Using Supabase Directly

Alternatively, you can connect Readdy directly to Supabase. Use the anon key
for read‑only access:

- **URL**: `https://<SUPABASE_URL>/rest/v1/companies?select=name,ethics_score,source_reason&order=ethics_score.desc`
- **Headers**:
  - `apikey: <anon_key>`
  - `Authorization: Bearer <anon_key>`

If you opt for this method, you can bypass the FastAPI backend for read‑only
queries; however, you will still need the backend for scoring and updates.

## Deployment

The backend is designed to run on platforms like **Render**, **Railway** or
any service that supports Python and Uvicorn. Below is a Render example.

### Render (or Railway)

1. **Create a new Web Service** on your platform and connect it to this GitHub
   repository.
2. Set the **Build Command** to:
   ```sh
   pip install -r requirements.txt
   ```
3. Set the **Start Command** to:
   ```sh
   uvicorn app.main:app --host 0.0.0.0 --port 10000
   ```
4. **Configure environment variables** in the service settings (see above).
5. **Optional**: Add a `render.yaml` at the project root to automate these settings.

Once deployed, your API will be available at a URL like `https://ethixai.onrender.com`.

## Cron Scheduling

The daily re‑scoring job is defined in `.github/workflows/schedule.yml`. This
GitHub Action triggers the `/score/cron` endpoint at 02:00 UTC every day.

To enable it:

1. In your GitHub repository settings, add the following **Repository Secrets**:
   - `API_BASE_URL`: The base URL of your deployed API (e.g. `https://ethixai.onrender.com`).
   - `API_KEY`: Your backend private key.
2. Commit and push to GitHub. GitHub Actions will automatically schedule the
   workflow.

When the cron runs, it will call the `/score/cron` endpoint which
rescans all companies using GPT‑3.5 and updates their scores.

---

Please replace placeholder values in configuration files with your actual
project identifiers and keys. If you have any questions or encounter
issues, feel free to open an issue or submit a pull request.
