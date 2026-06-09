import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from main import app

# StaticPool ensures all connections share one in-memory SQLite instance;
# without it each new connection gets an empty database and tables vanish.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Reusable factory helpers ───────────────────────────────────────────────

def make_category(client, *, name="Groceries", type="expense", color="#ef4444", icon="🛒"):
    r = client.post("/api/categories/", json={"name": name, "type": type, "color": color, "icon": icon})
    assert r.status_code == 201
    return r.json()


def make_transaction(client, category_id, *, amount=50.0, description="Test tx",
                     date="2026-06-01", type="expense"):
    r = client.post("/api/transactions/", json={
        "amount": amount, "description": description,
        "date": date, "type": type, "category_id": category_id,
    })
    assert r.status_code == 201
    return r.json()


def make_budget(client, category_id, *, amount=200.0, month=6, year=2026):
    r = client.post("/api/budgets/", json={
        "category_id": category_id, "amount": amount, "month": month, "year": year,
    })
    assert r.status_code == 201
    return r.json()
