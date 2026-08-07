# Fund Evaluation System

A full-stack fund evaluation platform with a FastAPI backend and a Vue 3 + Tailwind frontend.

---

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** Vue 3, Vite, Tailwind CSS v4, Pinia, Vue Router, Chart.js
- **Data Sync:** Tushare (optional)

---

## Project Structure

```
fund-evaluation-system/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   ├── schemas.py
│   │   ├── models/
│   │   └── routers/
│   ├── alembic/
│   ├── requirements.txt
│   └── .env
├── frontend/                # Vue 3 SPA
│   ├── src/
│   │   ├── main.js
│   │   ├── router.js
│   │   ├── stores/
│   │   ├── views/
│   │   └── style.css
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## Local Development

### 1. Start PostgreSQL

Create a database named `fundeval` (or set `DATABASE_URL` in `backend/.env`).

```bash
createdb fundeval
```

### 2. Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/fundeval
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_DAYS=7
TUSHARE_TOKEN=
```

Run the server:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

On first startup, the app creates all SQLAlchemy tables and seeds two default users:

| Username | Password | Role  |
|----------|----------|-------|
| `admin`  | `admin`  | admin |
| `sales`  | `sales`  | sales |

> **Note:** Change these credentials before deploying to production.

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api` requests to the backend.

To build for production:

```bash
npm run build
```

---

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/health` | Health check |
| POST   | `/api/auth/login` | Login |
| GET    | `/api/funds` | List/search funds |
| GET    | `/api/funds/{id}` | Fund detail |
| GET    | `/api/funds/{id}/nav` | NAV history |

---

## Frontend Routes

| Route | View | Access |
|-------|------|--------|
| `/login` | LoginView | public |
| `/overview` | OverviewView | authenticated |
| `/detail/:id` | DetailView | authenticated |
| `/compare` | CompareView | authenticated |
| `/admin` | AdminLayout | admin only |

---

## Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://user:pass@localhost/fundeval` | PostgreSQL connection string |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `TUSHARE_TOKEN` | `""` | Tushare API token for data sync |
| `CORS_ORIGINS` | `http://localhost:5173, http://localhost:3000` | Allowed frontend origins |

---

## Notes

- Tables are auto-created on startup via `Base.metadata.create_all()` for local development. Alembic migrations will be added in a future iteration.
- The compare and admin views are currently placeholders.
- Fund NAV and daily return values are stored per fund code in `fund_performances`.
