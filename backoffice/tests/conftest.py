import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Branch, User, UserRole
from app.security import hash_password


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def downtown(db):
    branch = Branch(name="Downtown")
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@pytest.fixture()
def airport(db):
    branch = Branch(name="Airport")
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@pytest.fixture()
def admin_user(db):
    user = User(
        username="admin",
        password_hash=hash_password("AdminPass1!"),
        role=UserRole.ADMIN,
        branch_id=None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def common_user(db, downtown):
    user = User(
        username="alice",
        password_hash=hash_password("AlicePass1!"),
        role=UserRole.COMMON,
        branch_id=downtown.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
