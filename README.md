# AI Interviewer (InterviewAI)

AI Interviewer is a full-stack SaaS starter for AI-assisted technical interviews. The MVP includes JWT authentication, profile endpoints, a clean FastAPI backend, and a modern React frontend wired for auth and future interview flows.

## Project Structure

```text
ai-interviewer/
  backend/
    alembic/
    app/
      api/v1/routers/
      core/
      db/
      models/
      schemas/
      services/
      utils/
    alembic.ini
    requirements.txt
  frontend/
    src/
      components/
      features/
      lib/
      stores/
      types/
    package.json
    vite.config.ts
  .env.example
  .gitignore
```

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env
```

Create a PostgreSQL database named `ai_interviewer`, update `DATABASE_URL` if needed, then run:

```bash
alembic revision --autogenerate -m "create users"
alembic upgrade head
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`, with docs at `http://localhost:8000/docs`.

## Frontend Setup

```bash
cd frontend
npm install
copy ..\.env.example .env
npm run dev
```

The app runs at `http://localhost:5173`.

## Auth Endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

## AI Provider Design

`AIService` exposes provider-neutral methods and currently ships with OpenAI support. Add another provider by implementing the same service methods and switching the provider in the service factory.
