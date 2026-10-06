from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from autopost_api.categories_allowlist import ALLOWED_CATEGORIES
from autopost_api.db.models import Category, User


OPERATOR_EMAIL = "operator@localhost"


def seed_if_empty(db: Session) -> None:
    user = db.scalar(select(User).where(User.email == OPERATOR_EMAIL))
    if user is None:
        user = User(email=OPERATOR_EMAIL, timezone="Asia/Seoul")
        db.add(user)
        db.flush()

    existing = {c.slug for c in db.scalars(select(Category)).all()}
    for item in ALLOWED_CATEGORIES:
        if item["slug"] in existing:
            continue
        db.add(
            Category(
                user_id=user.id,
                name=item["name"],
                slug=item["slug"],
                description=item["description"],
                adsense_slot_hint=item["adsense_slot_hint"],
                is_active=True,
            )
        )
    db.commit()
