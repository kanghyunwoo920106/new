from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from autopost_api.api.schemas import CategoryOut
from autopost_api.categories_allowlist import is_blocked_category_name
from autopost_api.db.models import Category
from autopost_api.db.session import get_db

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[Category]:
    rows = db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name)).all()
    return [c for c in rows if not is_blocked_category_name(c.name)]


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: str, db: Session = Depends(get_db)) -> Category:
    cat = db.get(Category, category_id)
    if cat is None or not cat.is_active or is_blocked_category_name(cat.name):
        raise HTTPException(status_code=404, detail="Category not found or blocked")
    return cat
