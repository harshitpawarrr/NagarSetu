"""
Locality Gazetteer Relational Models for NagarSetu.
Enables deterministic mapping from informal or colloquial address text and aliases
to official municipal Ward, Zone, and Canonical Locality.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class LocalityGazetteer(Base):
    """
    Official municipal locality directory with Ward and Zone mappings.
    Stores canonical locality name, alias array, and landmark metadata.
    """
    __tablename__ = "locality_gazetteer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_locality = Column(String(128), unique=True, nullable=False, index=True)
    ward = Column(String(64), nullable=False, index=True)
    zone = Column(String(64), nullable=False, index=True)
    aliases = Column(JSON, nullable=True)     # e.g., ["MP Nagar", "M.P. Nagar", "MPNagar", "M P Nagar"]
    landmarks = Column(JSON, nullable=True)   # e.g., [{"name": "District Hospital", "type": "hospital"}]
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    alias_entries = relationship("LocalityAlias", back_populates="gazetteer_record", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<LocalityGazetteer(canonical='{self.canonical_locality}', ward='{self.ward}', zone='{self.zone}')>"


class LocalityAlias(Base):
    """
    Normalized index table mapping individual colloquial aliases directly to canonical localities.
    Example: 'mp nagar', 'm.p. nagar', 'mpnagar' all point to 'MP Nagar'.
    """
    __tablename__ = "locality_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alias_normalized = Column(String(128), unique=True, nullable=False, index=True)  # Lowercased, stripped
    gazetteer_id = Column(Integer, ForeignKey("locality_gazetteer.id", ondelete="CASCADE"), nullable=False, index=True)
    canonical_locality = Column(String(128), nullable=False, index=True)

    # Relationships
    gazetteer_record = relationship("LocalityGazetteer", back_populates="alias_entries")

    def __repr__(self) -> str:
        return f"<LocalityAlias('{self.alias_normalized}' -> '{self.canonical_locality}')>"
