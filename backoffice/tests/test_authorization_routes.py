from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Branch, User, UserRole
from app.security import hash_password


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)

    session = session_local()
    branch = Branch(name="Downtown")
    session.add(branch)
    session.commit()
    session.refresh(branch)

    admin = User(
        username="admin",
        password_hash=hash_password("AdminPass1!"),
        role=UserRole.ADMIN,
        branch_id=None,
        is_active=True,
    )
    common = User(
        username="alice",
        password_hash=hash_password("AlicePass1!"),
        role=UserRole.COMMON,
        branch_id=branch.id,
        is_active=True,
    )
    session.add_all([admin, common])
    session.commit()
    session.close()

    def override_get_db():
        s = session_local()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _login(client, username, password):
    return client.post("/login", data={"username": username, "password": password})


def test_admin_cannot_access_stock_routes(client):
    _login(client, "admin", "AdminPass1!")
    response = client.get("/stock")
    assert response.status_code == 403


def test_common_user_cannot_access_admin_routes(client):
    _login(client, "alice", "AlicePass1!")
    response = client.get("/admin/users")
    assert response.status_code == 403


def test_anonymous_request_redirected_to_login(client):
    response = client.get("/stock", follow_redirects=False)
    assert response.status_code in (303, 401)


def test_common_user_can_add_stock_to_own_branch(client):
    _login(client, "alice", "AlicePass1!")
    with patch("app.services.stock_service.get_product", return_value={"id": "prod-001"}):
        response = client.post("/stock/add", data={"product_id": "prod-001", "quantity": "5"})
    assert response.status_code == 200
    assert "prod-001" in response.text


def test_deleted_user_login_rejected(client):
    # deactivate alice directly through admin flow, then confirm login fails
    _login(client, "admin", "AdminPass1!")
    users_page = client.get("/admin/users")
    assert "alice" in users_page.text

    from app.services.user_service import soft_delete_user  # noqa: E402

    # reuse the same in-memory engine via dependency override session
    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    alice = db.query(User).filter_by(username="alice").one()
    soft_delete_user(db, alice.id)

    response = _login(client, "alice", "AlicePass1!")
    assert "Invalid username or password" in response.text
