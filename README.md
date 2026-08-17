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
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

数据库迁移使用 Alembic 管理。首次启动前请运行 `alembic upgrade head` 创建表结构。

如需自动创建初始管理员，可设置环境变量 `INITIAL_ADMIN_USERNAME` 与 `INITIAL_ADMIN_PASSWORD`，应用启动时会自动创建该账号。留空则不创建任何默认用户。

> **Note:** Do not use weak credentials in production. Set a strong `SECRET_KEY` and use a unique initial admin password.

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
| GET    | `/api/funds?q=...&tag=...&tier=...` | Filter funds by keyword/tag/tier |
| GET    | `/api/funds/{id}` | Fund detail |
| GET    | `/api/funds/{id}/nav` | NAV history |
| GET    | `/api/funds/compare?ids=...` | Compare selected funds |

### Admin Endpoints

All admin endpoints require a user with `role=admin`.

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/admin/users` | List all users |
| POST   | `/api/admin/users` | Create user |
| PUT    | `/api/admin/users/{id}` | Update user info / role / status |
| POST   | `/api/admin/users/{id}/reset-password` | Reset user password |
| DELETE | `/api/admin/users/{id}` | Delete user (cannot delete self) |
| GET    | `/api/admin/tags` | List tags |
| POST   | `/api/admin/tags` | Create tag |
| PUT    | `/api/admin/tags/{id}` | Update tag / activate / deactivate |
| DELETE | `/api/admin/tags/{id}` | Permanently delete tag |
| GET    | `/api/admin/funds/lookup?code=...&market=...` | Lookup fund basic info from Tushare |
| GET    | `/api/admin/funds` | List all funds in product pool |
| POST   | `/api/admin/funds` | Create a new fund |
| GET    | `/api/admin/funds/{id}` | Fund detail (admin) |
| PUT    | `/api/admin/funds/{id}` | Update fund info |
| DELETE | `/api/admin/funds/{id}` | Delete fund and related data |
| POST   | `/api/admin/funds/{id}/sync` | Sync NAV history from Tushare |
| GET    | `/api/admin/funds/{id}/tier` | Get current/suggested tier |
| PUT    | `/api/admin/funds/{id}/tier` | Adjust tier (with reason, locks 30 days) |
| POST   | `/api/admin/funds/{id}/tier/clear-lock` | Clear manual lock and resume auto tiering |

---

## Frontend Routes

| Route | View | Access |
|-------|------|--------|
| `/login` | LoginView | public |
| `/overview` | OverviewView | authenticated |
| `/detail/:id` | DetailView | authenticated |
| `/compare` | CompareView | authenticated |
| `/admin` | AdminLayout → redirect to `/admin/funds` | admin only |
| `/admin/funds` | FundManagementView | admin only |
| `/admin/tags` | TagManagementView | admin only |
| `/admin/users` | UserManagementView | admin only |

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
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed frontend origins |
| `INITIAL_ADMIN_USERNAME` | `""` | Optional initial admin username |
| `INITIAL_ADMIN_PASSWORD` | `""` | Optional initial admin password |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `""` | API base URL (e.g. `https://api.example.com`). Leave blank in local dev to use Vite proxy. |

---

## Railway Deployment

This project is configured for **separate backend + frontend deployment** on Railway.

### 1. Create Project and Services

1. Create a new Railway project.
2. Add a **PostgreSQL** service. Railway will create `DATABASE_URL` automatically.
3. Add a **backend service** from the same GitHub repo:
   - Root Directory: `/backend`
   - Config Path: `/backend/railway.toml`
4. Add a **frontend empty service** from the same GitHub repo:
   - Root Directory: `/frontend`
   - Config Path: `/frontend/railway.toml`

The frontend service uses `serve` to serve the static build output, so Railway's install phase runs `npm ci` and the build command runs `npm run build`.

### 2. Environment Variables

**Backend service:**

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | (auto-populated by Railway PostgreSQL) |
| `SECRET_KEY` | Generate a strong random string |
| `CORS_ORIGINS` | `https://<your-frontend-domain>.up.railway.app` |
| `INITIAL_ADMIN_USERNAME` | Your desired admin username |
| `INITIAL_ADMIN_PASSWORD` | Strong unique password |
| `TUSHARE_TOKEN` | (optional) Tushare Pro API token for NAV sync |

**Frontend service:**

| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | `https://<your-backend-domain>.up.railway.app` |

### 3. Deploy

Push to `main`. Railway will build and deploy both services. The backend start command runs `alembic upgrade head` before starting Uvicorn, so database tables are created automatically on first deploy.

After deploy, verify the backend health check at `https://<backend-domain>/health`.

---

## Notes

- Alembic migrations are managed under `backend/alembic/`. Run `alembic upgrade head` to apply migrations locally.
- Admin users can manage the fund product pool at `/admin/funds`: create, edit, delete funds, lookup basic info from Tushare, trigger per-fund NAV sync, and adjust tier ratings.
- Admin users can manage tags at `/admin/tags` and user accounts at `/admin/users`.
- The tier system supports four levels: 主推 / 备选 / 替代 / 观察. Adjustments require a reason and automatically lock the fund tier for 30 days.
- Each fund code stores a `market` field (`OF`, `SH`, or `SZ`) so Tushare `ts_code` can be built correctly, e.g. `000001.OF`, `510300.SH`, `165509.SZ`.
- Fund NAV and daily return values are stored per fund code in `fund_performances`.
