"""
SQLAlchemy Item model definition for FastAPI project.

Defines the Item class with fields: id, title, description, price, and owner_id.
Establishes a foreign key relationship to the User model.
"""

import os
import sys
import re

from typing import Optional

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

# Assuming declarative_base() is used for SQLAlchemy models
Base = declarative_base()

class Item(Base):
  """
  SQLAlchemy model for items in the application.

  Attributes:
      id (int): Primary key for the item.
      title (str): Title of the item.
      description (str): Description of the item.
      price (float): Price of the item.
      owner_id (int): Foreign key referencing the user who owns the item.
      owner (User): Relationship to the User model.
  """
  __tablename__ = 'items'

  id: int = Column(Integer, primary_key=True, index=True)
  title: str = Column(String(128), nullable=False, index=True)
  description: Optional[str] = Column(String(512), nullable=True)
  price: float = Column(Float, nullable=False)
  owner_id: int = Column(Integer, ForeignKey('users.id'), nullable=False)

  owner = relationship('User', back_populates='items')