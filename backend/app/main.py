from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import get_db
from app.models import User
from app.routers import admin, auth, funds, tags, users
from app.security import get_password_hash


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_db_override = app.dependency_overrides.get(get_db, get_db)
    with contextmanager(get_db_override)() as db:
        if (
            settings.INITIAL_ADMIN_USERNAME
            and settings.INITIAL_ADMIN_PASSWORD
            and db.query(User).count() == 0
        ):
            db.add(
                User(
                    username=settings.INITIAL_ADMIN_USERNAME,
                    hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                    role="admin",
                )
            )
            db.commit()
    yield


app = FastAPI(title="Fund Evaluation API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(funds.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(users.router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
