# DSA Autograder ✨

DSA Autograder is an autonomous, scalable grading platform for Python Data Structures and Algorithms (DSA) assignments. It combines AST static analysis, sandboxed dynamic execution, and an **AI-Agent Professor** module to provide instantaneous, human-like feedback to students.

## 🚀 Key Features

- **Unified Launcher (`main.py`)**: One-click startup script that checks dependencies, orchestrates database connections, boots the backend, and mounts the compiled frontend UI safely under a single port.
- **AI-Agent Professor Model**: Integrated with `google-generativeai` (Gemini Flash). The AI doesn't just grade—it acts as an empathetic professor, providing actionable suggestions to improve algorithmic thinking and code safety.
- **Premium UX & Interaction System**: Features an infinitely smooth UI powered by an optimized **Framer Motion** engine. Includes zero-latency system toasts with spring physics and context-aware variants (Success, Destructive, Warning).
- **Safety Guardrails**: Intelligent destructive action guards for file revocation, featuring high-visibility visual alerts (Red Triangle indicators) to prevent accidental student data loss.
- **Next.js + Tailwind Dashboard**: A beautiful, highly-responsive frontend panel seamlessly integrated and served by the FastAPI runtime (served via `frontend/out`).
- **In-Memory & Persistent Caching**: Employs auto-clearing idempotency caches and local event busses to eliminate repetitive compute costs.
- **Security & Sandbox Isolation**: Dynamic executions are hard-limited by `psutil`, restricting infinite loops, malicious file I/O operations, and timeout-based deadlocks.

## 📁 Repository Architecture

```text
DSA_Fusion_Final/
├── backend/            # FastAPI backend, Agents, and Grading Orchestrator
│   ├── app/            # Domain logic, AI integration, AST static analysis
│   ├── data/           # SQLite databases & JSON fixture sets
│   └── requirements.txt# Backend Dependencies
├── frontend/           # Next.js UI Application
│   ├── src/            # React Components, Hooks, and API integrations
│   └── package.json    # Frontend Dependencies
└── main.py             # Single-entry Unified Launcher
```

## 🛠 Quick Start

### 1. Unified Setup (Recommended)
You only need to install Python dependencies once.

```bash
# Install backend requirements
pip install -r backend/requirements.txt

# Start the unified server
python main.py
```
> The launcher will automatically start the server on `http://127.0.0.1:8000`. The Next.js frontend must be built beforehand using `npm run build` inside the `frontend` directory.

### 2. Manual Development Mode

If you wish to develop the backend and frontend separately:

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## ⚙️ Environment Configuration (`.env`)

At the root directory (or `backend/.env`), ensure the following critical variables are set:

```ini
ENVIRONMENT=development
PORT=8000

# AI Configuration
AI_PROVIDER=gemini
AI_MODEL_NAME=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_api_key_here

# Security (SetRATE_LIMIT_ENABLED=false for local development to prevent 429s)
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MINUTE=600  

# Database
SQL_SERVER_URL=DRIVER={ODBC Driver 17 for SQL Server};SERVER=...;UID=...;PWD=...
DB_NAME=Data_PersonalizedSystem
```

## 🛡️ Security & Validations

- **Unicode Handling**: System safely wraps `sys.stdout` UTF-8 reconfiguration to circumvent common Windows ASCII console encoding crashes.
- **Process Spawning**: Substituted raw OS syscalls with robust `subprocess.run` to guarantee space path interpolation under Windows environments.
- **Rate Limiting**: Native token-bucket rate limiting logic on inbound request paths (configurable via `.env`).
