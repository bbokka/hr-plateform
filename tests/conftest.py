import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from fastapi.testclient import TestClient

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Fresh tables for every single test, torn down after."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient wired to the test DB instead of the real one,
    and pre-authenticated: registers a throwaway test user and logs in.
    TestClient automatically persists cookies across requests within the
    same instance, so no manual header handling is needed -- the login
    response's Set-Cookie is stored and sent on every subsequent request.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)

    test_client.post("/auth/register", json={
        "email": "test.user@example.com",
        "password": "testpassword123",
    })
    test_client.post("/auth/login", data={
        "username": "test.user@example.com",
        "password": "testpassword123",
    })

    yield test_client
    app.dependency_overrides.clear()