import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.fund import Fund, FundCode
from app.models.performance import FundPerformance
from app.models.user import User
from app.security import create_access_token, get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
def auth_user(db):
    user = User(username="tester", hashed_password=get_password_hash("pass"), role="sales")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(auth_user):
    token = create_access_token({"sub": str(auth_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_user(db):
    user = User(username="admin", hashed_password=get_password_hash("pass"), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def admin_headers(admin_user):
    token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def sample_funds(db):
    fund_a = Fund(name="基金 A", category="混合型", risk_level="中", manager="张三")
    fund_b = Fund(name="基金 B", category="股票型", risk_level="高", manager="李四")
    db.add_all([fund_a, fund_b])
    db.commit()
    db.refresh(fund_a)
    db.refresh(fund_b)

    code_a = FundCode(fund_id=fund_a.id, code="000001", is_primary=True)
    code_b = FundCode(fund_id=fund_b.id, code="000002", is_primary=True)
    db.add_all([code_a, code_b])
    db.commit()
    db.refresh(code_a)
    db.refresh(code_b)

    performances = [
        FundPerformance(fund_code_id=code_a.id, date=date(2026, 8, 1), nav=1.1000, daily_return=0.0100),
        FundPerformance(fund_code_id=code_a.id, date=date(2026, 8, 2), nav=1.1100, daily_return=0.0091),
        FundPerformance(fund_code_id=code_b.id, date=date(2026, 8, 1), nav=2.2000, daily_return=-0.0050),
        FundPerformance(fund_code_id=code_b.id, date=date(2026, 8, 2), nav=2.1900, daily_return=-0.0045),
    ]
    db.add_all(performances)
    db.commit()

    return {"fund_a": fund_a, "fund_b": fund_b, "code_a": code_a, "code_b": code_b}
