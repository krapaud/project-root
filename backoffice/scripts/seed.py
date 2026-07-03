"""Initialize the Backoffice database with baseline data.

Run with: python -m scripts.seed
Safe to re-run: skips creation of rows that already exist (by unique key).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, SessionLocal, engine
from app.models import Branch, Stock, User, UserRole
from app.security import hash_password

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "ChangeMe123!")

BRANCHES = ["Downtown", "Airport"]

SAMPLE_STOCK = [
    ("Downtown", "prod-001", 25),
    ("Downtown", "prod-002", 10),
    ("Airport", "prod-001", 5),
    ("Airport", "prod-003", 40),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        branches_by_name = {}
        for name in BRANCHES:
            branch = db.query(Branch).filter_by(name=name).one_or_none()
            if branch is None:
                branch = Branch(name=name)
                db.add(branch)
                db.flush()
            branches_by_name[name] = branch

        admin = db.query(User).filter_by(username=ADMIN_USERNAME).one_or_none()
        if admin is None:
            admin = User(
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                branch_id=None,
                is_active=True,
            )
            db.add(admin)

        for branch_name, product_id, quantity in SAMPLE_STOCK:
            branch = branches_by_name[branch_name]
            stock = (
                db.query(Stock)
                .filter_by(branch_id=branch.id, product_id=product_id)
                .one_or_none()
            )
            if stock is None:
                db.add(Stock(branch_id=branch.id, product_id=product_id, quantity=quantity))

        db.commit()
        print("Seed complete.")
        print(f"Admin username: {ADMIN_USERNAME}")
        print(
            "Admin password: "
            f"{ADMIN_PASSWORD if os.getenv('SEED_ADMIN_PASSWORD') else '(default) ' + ADMIN_PASSWORD}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
