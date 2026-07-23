# 🎙️ AI Interviewer (InterviewAI)

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.org/)
[![Python](https://img.shields.io/badge/Python_3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

An enterprise-grade, full-stack platform for AI-assisted technical interviews. Built with a robust **FastAPI** backend and a responsive **React (TypeScript + Vite)** frontend, **AI Interviewer** supports real-time conversation simulation, speech-to-text / text-to-speech interaction, dynamic vision evaluation, multi-model AI profile switching, and candidate analytics.

---

## ✨ Features

- 🔐 **Authentication & Authorization**:
  - Secure JWT authentication (Access & Refresh tokens).
  - Multi-provider Social OAuth login (Google, GitHub, X/Twitter, Apple).
- 🤖 **AI-Powered Technical Interviews**:
  - Live conversational audio/video interview simulation.
  - Multi-model profile support (dynamically select between fast & smart LLMs).
  - Real-time speech recognition (Whisper) & TTS voice responses (OpenAI TTS).
  - Vision evaluation support (evaluating code on screen/whiteboard snapshots).
- 📊 **Candidate & Interview Analytics**:
  - Performance scoring, feedback breakdown, and strengths/weaknesses summary.
- ⚡ **Modern Architecture**:
  - Async FastAPI backend with SQLAlchemy & Alembic database migrations.
  - State management & clean UI components built with React & TypeScript.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+) |
| **Database & ORM** | [PostgreSQL](https://www.postgresql.org/) / [SQLite](https://www.sqlite.org/) + [SQLAlchemy 2.0](https://www.sqlalchemy.org/) |
| **Database Migrations**| [Alembic](https://alembic.sqlalchemy.org/) |
| **Authentication** | PyJWT, OAuth2 (Google, GitHub, X, Apple) |
| **AI Integration** | OpenAI API (GPT-4.1, GPT-4o-mini, Whisper STT, TTS-1) |
| **Frontend Framework**| [React 18](https://reactjs.org/) + [TypeScript](https://www.typescriptlang.org/) |
| **Build Tool & Server**| [Vite](https://vitejs.org/) |
| **Styling** | Modern Vanilla CSS & Design Tokens |

---

## 📁 Directory Structure

```text
ai-interviewer/
├── backend/
│   ├── alembic/              # Database migration scripts
│   ├── app/
│   │   ├── api/              # API Versioned Routers (v1)
│   │   │   └── v1/
│   │   │       └── routers/  # Auth, OAuth, AI, Interviews, Users
│   │   ├── core/             # Security, Config & Paths
│   │   ├── db/               # Database session setup
│   │   ├── models/           # SQLAlchemy Data Models
│   │   ├── schemas/          # Pydantic Schemas
│   │   ├── services/         # Business logic (AI, Live Interview, OAuth, Auth)
│   │   └── utils/            # Helper utilities & dependencies
│   ├── alembic.ini           # Alembic configuration
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/              # Axios/Fetch API clients
│   │   ├── components/       # Reusable UI components
│   │   ├── context/          # React Context providers (Auth, Theme)
│   │   ├── features/         # Feature modules (Interview live view, Dashboard)
│   │   ├── hooks/            # Custom React hooks
│   │   ├── pages/            # Application pages
│   │   └── types/            # TypeScript definitions
│   ├── package.json          # Node dependencies
│   ├── tsconfig.json         # TypeScript configuration
│   └── vite.config.ts        # Vite configuration
├── .env.example              # Central environment variables template
├── .gitignore                # Git ignore rules
└── README.md                 # Project documentation
```

---

## 🚀 Quickstart & Installation

### Prerequisites

- **Python**: `3.11+`
- **Node.js**: `18.x+` & `npm`
- **Git**

---

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-interviewer.git
cd ai-interviewer
```

---

### 2️⃣ Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment configuration
copy ..\.env.example .env   # On Windows
# cp ../.env.example .env    # On macOS/Linux

# Apply database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

The API server will run at `http://localhost:8000`.  
Interactive API Docs (Swagger UI) are available at `http://localhost:8000/docs`.

---

### 3️⃣ Frontend Setup

```bash
# Navigate to frontend directory (from project root)
cd frontend

# Install Node dependencies
npm install

# Create environment file
copy ..\.env.example .env   # On Windows
# cp ../.env.example .env    # On macOS/Linux

# Start Vite dev server
npm run dev
```

The frontend application will run at `http://localhost:5173`.

---

## 🔑 Environment Variables

Key configuration variables in `.env`:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy Connection URI | `sqlite:///./dev.db` |
| `SECRET_KEY` | JWT Secret Key | *Set a long random string* |
| `OPENAI_API_KEY` | OpenAI API Key for AI interviewers | `""` |
| `OPENAI_MODEL` | Default LLM model | `gpt-4.1-mini` |
| `VITE_API_BASE_URL` | Frontend API Base Endpoint | `http://localhost:8000/api/v1` |

*(See [.env.example](.env.example) for complete list including OAuth & SMTP settings)*

---

## 📡 API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user account |
| `POST` | `/api/v1/auth/login` | Authenticate & issue JWT tokens |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `GET` | `/api/v1/auth/me` | Fetch current user profile |
| `GET` | `/api/v1/oauth/login/{provider}` | Initiate Social OAuth login |
| `GET` | `/api/v1/oauth/callback/{provider}` | Process OAuth callback |
| `GET` | `/api/v1/ai/profiles` | List available AI interviewer profiles |
| `POST` | `/api/v1/interviews/` | Create a new interview session |
| `POST` | `/api/v1/interviews/{id}/live` | Live voice/video interaction endpoint |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: add AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
