"""
Products router — /api/products

Thin handler layer. All database logic lives in product_service.py.

Endpoints (spec §7.3):
  GET    /api/products           list products (paginated, searchable)
  POST   /api/products           create product
  GET    /api/products/{id}      get product detail
  PUT    /api/products/{id}      update product
  DELETE /api/products/{id}      delete product (blocked if inventory exists)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pymongo.database import Database

from app.dependencies import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductOut])
def list_products(
    search: Optional[str] = Query(default=None, description="Substring search"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Database = Depends(get_db),
):
    items, total = product_service.list_products(db, search=search, skip=skip, limit=limit)
    return PaginatedResponse[ProductOut](items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, db: Database = Depends(get_db)):
    return product_service.create_product(db, data)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db: Database = Depends(get_db)):
    return product_service.get_product(db, product_id)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: str, data: ProductUpdate, db: Database = Depends(get_db)):
    return product_service.update_product(db, product_id, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: str, db: Database = Depends(get_db)):
    product_service.delete_product(db, product_id)
