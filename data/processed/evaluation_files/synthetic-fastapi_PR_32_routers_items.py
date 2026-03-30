"""
routers/items.py

This module defines an APIRouter for item resources, providing CRUD endpoints
with support for pagination and filtering via query parameters.

Endpoints:
- GET /items: List items with pagination and filtering
- GET /items/{item_id}: Retrieve an item by ID
- POST /items: Create a new item
- PUT /items/{item_id}: Update an existing item
- DELETE /items/{item_id}: Delete an item

"""

from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/items",
    tags=["items"],
)


class Item(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    price: float
    in_stock: bool = True
    category: Optional[str] = None


class ItemCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=300)
    price: float = Field(..., gt=0)
    in_stock: bool = True
    category: Optional[str] = Field(None, max_length=50)


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=300)
    price: Optional[float] = Field(None, gt=0)
    in_stock: Optional[bool] = None
    category: Optional[str] = Field(None, max_length=50)


# In-memory storage for demonstration
_items_db: List[Item] = []


@router.get(
    "",
    response_model=List[Item],
    summary="List items with pagination and filtering"
)
def list_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(10, ge=1, le=100, description="Max items to return"),
    name: Optional[str] = Query(None, description="Filter by item name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    in_stock: Optional[bool] = Query(None, description="Filter by stock status"),
) -> List[Item]:
    """
    Retrieve a list of items with optional pagination and filtering.
    """
    filtered_items = _items_db

    if name:
        filtered_items = [item for item in filtered_items if name.lower() in item.name.lower()]
    if category:
        filtered_items = [item for item in filtered_items if item.category == category]
    if min_price is not None:
        filtered_items = [item for item in filtered_items if item.price >= min_price]
    if max_price is not None:
        filtered_items = [item for item in filtered_items if item.price <= max_price]
    if in_stock is not None:
        filtered_items = [item for item in filtered_items if item.in_stock == in_stock]

    return filtered_items[skip:skip + limit]


@router.get(
    "/{item_id}",
    response_model=Item,
    summary="Get an item by ID"
)
def getItem(item_id: UUID) -> Item:
    """
    Retrieve a single item by its ID.
    """
    for item in _items_db:
        if item.id == item_id:
            return item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Item not found"
    )


@router.post(
    "",
    response_model=Item,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new item"
)
def createItem(item: ItemCreate) -> Item:
    """
    Create a new item and add it to the database.
    """
    new_item = Item(**item.dict())
    _items_db.append(new_item)
    return new_item


@router.put(
    "/{item_id}",
    response_model=Item,
    summary="Update an existing item"
)
def updateItem(item_id: UUID, item_update: ItemUpdate) -> Item:
    """
    Update an existing item by its ID.
    """
    for idx, item in enumerate(_items_db):
        if item.id == item_id:
            updated_data = item.dict()
            update_fields = item_update.dict(exclude_unset=True)
            updated_data.update(update_fields)
            updated_item = Item(**updated_data)
            _items_db[idx] = updated_item
            return updated_item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Item not found"
    )


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item"
)
def deleteItem(item_id: UUID) -> None:
    """
    Delete an item by its ID.
    """
    for idx, item in enumerate(_items_db):
        if item.id == item_id:
            del _items_db[idx]
            return
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Item not found"
    )