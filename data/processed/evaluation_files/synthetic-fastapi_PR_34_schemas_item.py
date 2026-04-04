"""
Pydantic schemas for Item models in FastAPI project.

Defines ItemCreate, ItemUpdate, and ItemResponse data structures
with field validation and example data.
"""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field, validator


class ItemBase(BaseModel):
    """
    Base schema for Item with shared fields and validators.
    """
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        example="Wireless Mouse",
        description="Name of the item"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        example="A high-quality wireless mouse with ergonomic design.",
        description="Detailed description of the item"
    )
    price: float = Field(
        ...,
        gt=0,
        lt=10000,
        example=29.99,
        description="Price of the item"
    )
    in_stock: int = Field(
        ...,
        ge=0,
        le=10000,
        example=150,
        description="Number of items available in stock"
    )

    @validator('name')
    def name_mustNotBeBlank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Item name must not be blank')
        return value

    @validator('description')
    def description_strip(cls, value: Optional[str]) -> Optional[str]:
        if value:
            return value.strip()
        return value

    @validator('price')
    def price_mustHaveTwoDecimals(cls, value: float) -> float:
        if round(value, 2) != value:
            raise ValueError('Price must have at most two decimal places')
        return value


class ItemCreate(ItemBase):
    """
    Schema for creating a new Item.
    """
    pass


class ItemUpdate(BaseModel):
    """
    Schema for updating an Item. All fields optional.
    """
    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        example="Bluetooth Keyboard"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        example="A slim Bluetooth keyboard with rechargeable battery."
    )
    price: Optional[float] = Field(
        None,
        gt=0,
        lt=10000,
        example=45.50
    )
    in_stock: Optional[int] = Field(
        None,
        ge=0,
        le=10000,
        example=75
    )

    @validator('name')
    def nameNotBlank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError('Item name must not be blank')
        return value

    @validator('description')
    def description_strip(cls, value: Optional[str]) -> Optional[str]:
        if value:
            return value.strip()
        return value

    @validator('price')
    def priceTwoDecimals(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and round(value, 2) != value:
            raise ValueError('Price must have at most two decimal places')
        return value


class ItemResponse(ItemBase):
    """
    Schema for Item response with id and timestamps.
    """
    id: int = Field(
        ...,
        example=1,
        description="Unique identifier for the item"
    )
    created_at: datetime = Field(
        ...,
        example="2024-06-11T12:34:56Z",
        description="Timestamp when the item was created"
    )
    updated_at: datetime = Field(
        ...,
        example="2024-06-11T13:00:00Z",
        description="Timestamp when the item was last updated"
    )

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "name": "Wireless Mouse",
                "description": "A high-quality wireless mouse with ergonomic design.",
                "price": 29.99,
                "in_stock": 150,
                "created_at": "2024-06-11T12:34:56Z",
                "updated_at": "2024-06-11T13:00:00Z"
            }
        }