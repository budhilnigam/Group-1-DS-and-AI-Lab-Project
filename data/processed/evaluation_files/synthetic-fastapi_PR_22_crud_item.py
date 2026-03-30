"""
crud/item.py

CRUD operations for Item model in a FastAPI project.
Provides functions to retrieve, create, and update Item instances,
with support for owner-based filtering.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from models.item import Item
from schemas.item import ItemCreate, ItemUpdate


def getItem(db: Session, item_id: int, owner_id: Optional[int] = None) -> Optional[Item]:
    """
    Retrieve a single Item by its ID, optionally filtering by owner_id.

    Args:
        db (Session): SQLAlchemy database session.
        item_id (int): ID of the item to retrieve.
        owner_id (Optional[int]): Optional owner ID to filter.

    Returns:
        Optional[Item]: The Item instance or None if not found.
    """
    query = db.query(Item).filter(Item.id == item_id)
    if owner_id is not None:
        query = query.filter(Item.owner_id == owner_id)
    return query.first()


def getItems(
    db: Session,
    owner_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Item]:
    """
    Retrieve a list of Items, optionally filtered by owner_id.

    Args:
        db (Session): SQLAlchemy database session.
        owner_id (Optional[int]): Optional owner ID to filter.
        skip (int): Number of records to skip.
        limit (int): Maximum number of records to return.

    Returns:
        List[Item]: List of Item instances.
    """
    query = db.query(Item)
    if owner_id is not None:
        query = query.filter(Item.owner_id == owner_id)
    return query.offset(skip).limit(limit).all()


def createItem(db: Session, item_data: ItemCreate, owner_id: int) -> Item:
    """
    Create a new Item instance for a specific owner.

    Args:
        db (Session): SQLAlchemy database session.
        item_data (ItemCreate): Data for the new Item.
        owner_id (int): ID of the owner for the Item.

    Returns:
        Item: The created Item instance.
    """
    item = Item(**item_data.dict(), owner_id=owner_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def updateItem(
    db: Session,
    item_id: int,
    item_data: ItemUpdate,
    owner_id: Optional[int] = None
) -> Optional[Item]:
    """
    Update an existing Item instance, optionally filtering by owner_id.

    Args:
        db (Session): SQLAlchemy database session.
        item_id (int): ID of the Item to update.
        item_data (ItemUpdate): Data to update the Item.
        owner_id (Optional[int]): Optional owner ID to filter.

    Returns:
        Optional[Item]: The updated Item instance or None if not found.
    """
    query = db.query(Item).filter(Item.id == item_id)
    if owner_id is not None:
        query = query.filter(Item.owner_id == owner_id)
    item = query.first()
    if item is None:
        return None

    update_fields = item_data.dict(exclude_unset=True)
    for key, value in update_fields.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item