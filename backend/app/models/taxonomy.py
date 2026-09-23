"""
Department and Category Relational Models for NagarSetu.
Enables fully configurable municipal taxonomy without hardcoding department logic into code.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

# Import Base from db.base
from app.db.base import Base


class Department(Base):
    """
    Configurable municipal department records.
    Pre-seeded with Roads, Water, Sanitation, Sewerage, Electrical, Parks, Public Health, Other.
    """
    __tablename__ = "departments"

    department_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    default_sla_hours = Column(Integer, nullable=True)
    escalation_contact = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    categories = relationship("Category", back_populates="department", cascade="all, delete-orphan")
    triaged_complaints = relationship("TriagedComplaint", back_populates="department_rel")

    def __repr__(self) -> str:
        return f"<Department(code='{self.code}', name='{self.name}')>"


class Category(Base):
    """
    Department-linked categories and subcategories.
    All taxonomy remains configurable in the database.
    """
    __tablename__ = "categories"

    category_id = Column(String(64), primary_key=True, index=True)
    department_id = Column(String(64), ForeignKey("departments.department_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False, index=True)
    description = Column(Text, nullable=True)
    typical_sla_hours = Column(Integer, nullable=True)
    subcategories = Column(JSON, nullable=True)  # List of subcategory definitions
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    department = relationship("Department", back_populates="categories")
    triaged_complaints = relationship("TriagedComplaint", back_populates="category_rel")

    def __repr__(self) -> str:
        return f"<Category(category_id='{self.category_id}', name='{self.name}', dept='{self.department_id}')>"
