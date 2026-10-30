"""
Inventory router — /api/inventory

Endpoints (spec §7.4):
  GET    /api/inventory              list items (paginated, with filters)
  POST   /api/inventory              add item
  GET    /api/inventory/{id}         get item detail
  PUT    /api/inventory/{id}         update item
  DELETE /api/inventory/{id}         delete item

Optional query parameters (spec §7.4):
  search     — substring match on lot_number
  product_id — filter by product reference
  lot_number — exact lot match (case-insensitive)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pymongo.database import Database

from app.dependencies import get_db
from app.schemas.inventory import InventoryCreate, InventoryOut, InventoryUpdate
from app.schemas.pagination import PaginatedResponse
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=PaginatedResponse[InventoryOut])
def list_inventory(
    search: Optional[str] = Query(default=None, description="Substring search on lot number"),
    product_id: Optional[str] = Query(default=None, description="Filter by product id"),
    lot_number: Optional[str] = Query(default=None, description="Exact lot number match"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Database = Depends(get_db),
):
    items, total = inventory_service.list_inventory_items(
        db,
        search=search,
        product_id=product_id,
        lot_number=lot_number,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse[InventoryOut](items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=InventoryOut, status_code=status.HTTP_201_CREATED)
def create_inventory_item(data: InventoryCreate, db: Database = Depends(get_db)):
    return inventory_service.create_inventory_item(db, data)


@router.get("/{item_id}", response_model=InventoryOut)
def get_inventory_item(item_id: str, db: Database = Depends(get_db)):
    return inventory_service.get_inventory_item(db, item_id)


@router.put("/{item_id}", response_model=InventoryOut)
def update_inventory_item(item_id: str, data: InventoryUpdate, db: Database = Depends(get_db)):
    return inventory_service.update_inventory_item(db, item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(item_id: str, db: Database = Depends(get_db)):
    inventory_service.delete_inventory_item(db, item_id)
