from app.auth import authenticate_user
from app.services.user_service import soft_delete_user


def test_authenticate_user_with_correct_credentials(db, common_user):
    user = authenticate_user(db, "alice", "AlicePass1!")
    assert user is not None
    assert user.username == "alice"


def test_authenticate_user_with_wrong_password(db, common_user):
    assert authenticate_user(db, "alice", "WrongPassword") is None


def test_authenticate_user_unknown_username(db):
    assert authenticate_user(db, "ghost", "whatever") is None


def test_deleted_user_cannot_authenticate(db, common_user):
    soft_delete_user(db, common_user.id)
    assert authenticate_user(db, "alice", "AlicePass1!") is None
