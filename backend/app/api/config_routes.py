"""
Configuration API Router for NagarSetu
Exposes read-only municipal department and category taxonomy configurations.
"""

import json
from fastapi import APIRouter, status
from app.core.config import settings

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get(
    "/departments",
    status_code=status.HTTP_200_OK,
    summary="Get official municipal department taxonomy"
)
def get_departments_config():
    """Returns the registered municipal departments, codes, SLAs, and keywords."""
    dept_file = settings.CONFIG_DIR / "departments.json"
    with open(dept_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get(
    "/categories",
    status_code=status.HTTP_200_OK,
    summary="Get official category and subcategory taxonomy"
)
def get_categories_config():
    """Returns the official complaint categories, department mappings, and typical SLAs."""
    cat_file = settings.CONFIG_DIR / "categories.json"
    with open(cat_file, "r", encoding="utf-8") as f:
        return json.load(f)
