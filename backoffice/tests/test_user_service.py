import pytest

from app.services.user_service import (
    UserValidationError,
    change_password,
    create_common_user,
    soft_delete_user,
)


def test_admin_can_create_common_user(db, downtown):
    user = create_common_user(db, "bob", "BobPass1!", downtown.id)
    assert user.username == "bob"
    assert user.branch_id == downtown.id
    assert user.role.value == "common"


def test_cannot_create_duplicate_username(db, downtown, common_user):
    with pytest.raises(UserValidationError, match="already taken"):
        create_common_user(db, "alice", "SomePass1!", downtown.id)


def test_admin_can_soft_delete_user(db, common_user):
    soft_delete_user(db, common_user.id)
    assert common_user.is_active is False


def test_soft_delete_does_not_remove_user_row(db, common_user):
    user_id = common_user.id
    soft_delete_user(db, user_id)
    assert db.get(type(common_user), user_id) is not None


def test_cannot_soft_delete_admin_through_user_management(db, admin_user):
    with pytest.raises(UserValidationError, match="Admin users cannot be managed"):
        soft_delete_user(db, admin_user.id)


def test_admin_can_change_common_user_password(db, common_user):
    old_hash = common_user.password_hash
    change_password(db, common_user.id, "NewPass1!")
    assert common_user.password_hash != old_hash
