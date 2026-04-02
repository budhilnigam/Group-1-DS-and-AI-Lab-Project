"""
Pytest tests for FastAPI item endpoints.

Tests:
    - test_create_item: POST /items
    - test_get_items: GET /items
    - test_filter_items: GET /items?name=...
"""

from typing import Any, Dict, List

import pytest
from fastapi import status
from httpx import AsyncClient

from app.main import app


@pytest.fixture
async def async_client() -> AsyncClient:
    """
    Fixture providing an AsyncClient for FastAPI app.
    """
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def sample_items(async_client: AsyncClient, sample_items: List[Dict[str, Any]] = []) -> List[Dict[str, Any]]:
    """
    Creates sample items for testing.
    """
    items = [
        {"name": "Book", "description": "A fantasy novel", "price": 12.5},
        {"name": "Pen", "description": "Blue ink", "price": 1.2},
        {"name": "Notebook", "description": "Ruled pages", "price": 3.5},
    ]
    created = []
    for item in items:
        response = await async_client.post("/items", json=item)
        assert response.status_code == status.HTTP_201_CREATED
        created.append(response.json())
    return created


@pytest.mark.asyncio
async def test_create_item(async_client: AsyncClient) -> None:
    """
    Test creating an item via POST /items.
    """
    item_payload = {
        "name": "Pencil",
        "description": "HB graphite pencil",
        "price": 0.99,
    }
    response = await async_client.post("/items", json=item_payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert "id" in data
    assert data["name"] == item_payload["name"]
    assert data["description"] == item_payload["description"]
    assert data["price"] == item_payload["price"]


@pytest.mark.asyncio
async def test_get_items(async_client: AsyncClient, sample_items: List[Dict[str, Any]] = []) -> None:
    """
    Test retrieving all items via GET /items.
    """
    response = await async_client.get("/items")
    assert response.status_code == status.HTTP_200_OK

    items = response.json()
    assert isinstance(items, list)
    sample_names = {item["name"] for item in sample_items}
    returned_names = {item["name"] for item in items}
    assert sample_names.issubset(returned_names)


@pytest.mark.asyncio
async def test_filter_items(async_client: AsyncClient, sample_items: List[Dict[str, Any]] = []) -> None:
    """
    Test filtering items by name via GET /items?name=...
    """
    filter_name = "Pen"
    response = await async_client.get("/items", params={"name": filter_name})
    assert response.status_code == status.HTTP_200_OK

    items = response.json()
    assert isinstance(items, list)
    assert all(item["name"] == filter_name for item in items)
    assert len(items) == 1
    assert items[0]["description"] == "Blue ink"
    assert items[0]["price"] == 1.2


@pytest.mark.asyncio
async def test_create_item_missing_fields(async_client: AsyncClient) -> None:
    """
    Test creating an item with missing required fields.
    """
    incomplete_payload = {
        "description": "No name",
        "price": 5.0,
    }
    response = await async_client.post("/items", json=incomplete_payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_get_items_empty(async_client: AsyncClient) -> None:
    """
    Test retrieving items when no items exist.
    """
    response = await async_client.get("/items")
    assert response.status_code == status.HTTP_200_OK
    items = response.json()
    assert isinstance(items, list)
    assert items == []


@pytest.mark.asyncio
async def test_filter_items_no_match(async_client: AsyncClient, sample_items: List[Dict[str, Any]] = []) -> None:
    """
    Test filtering items by a name that does not exist.
    """
    response = await async_client.get("/items", params={"name": "Nonexistent"})
    assert response.status_code == status.HTTP_200_OK
    items = response.json()
    assert items == []