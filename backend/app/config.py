from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:pass@localhost/fundeval"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    TUSHARE_TOKEN: str = ""
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = "http://localhost:5173"
    RISK_FREE_RATE: float = 0.025
    INITIAL_ADMIN_USERNAME: str = ""
    INITIAL_ADMIN_PASSWORD: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
