from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, get_db
from app.models import User
from app.routers import auth, funds
from app.security import get_password_hash


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_db_override = app.dependency_overrides.get(get_db, get_db)
    with contextmanager(get_db_override)() as db:
        Base.metadata.create_all(bind=db.get_bind())
        if db.query(User).count() == 0:
            db.add_all(
                [
                    User(username="admin", hashed_password=get_password_hash("admin"), role="admin"),
                    User(username="sales", hashed_password=get_password_hash("sales"), role="sales"),
                ]
            )
            db.commit()
    yield


app = FastAPI(title="Fund Evaluation API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(funds.router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
