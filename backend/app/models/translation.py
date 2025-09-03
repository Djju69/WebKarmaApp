"""
Translation models for multi-language support.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, Index, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class TranslationType(str, Enum):
    """Types of translatable content."""
    INTERFACE = 'interface'  # UI elements, buttons, labels
    CONTENT = 'content'      # User-generated content
    CARD = 'card'           # Card-specific content
    CATEGORY = 'category'   # Category names and descriptions
    BANNER = 'banner'       # Banner content

class InterfaceTranslation(Base):
    """Stores translations for interface elements."""
    __tablename__ = 'interface_translations'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), nullable=False, index=True)
    module = Column(String(100), nullable=False, index=True)  # e.g., 'auth', 'navigation', 'errors'
    ru = Column(Text, nullable=False)  # Russian
    en = Column(Text, nullable=False)  # English
    es = Column(Text, nullable=False)  # Spanish
    fr = Column(Text, nullable=False)  # French
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Index for faster lookups
    __table_args__ = (
        Index('idx_interface_translation_key_module', 'key', 'module', unique=True),
    )

    def __repr__(self):
        return f"<InterfaceTranslation {self.module}.{self.key}>"


class ContentTranslation(Base):
    """Stores translations for dynamic content."""
    __tablename__ = 'content_translations'

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(
        String(20),
        nullable=False,
        index=True
    )
    content_id = Column(Integer, nullable=False, index=True)  # ID of the content in its respective table
    field_name = Column(String(100), nullable=False, index=True)  # e.g., 'title', 'description'
    ru = Column(Text, nullable=True)  # Russian
    en = Column(Text, nullable=True)  # English
    es = Column(Text, nullable=True)  # Spanish
    fr = Column(Text, nullable=True)  # French
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Index for faster lookups
    __table_args__ = (
        Index('idx_content_translation_lookup', 'content_type', 'content_id', 'field_name', unique=True),
    )

    def __repr__(self):
        return f"<ContentTranslation {self.content_type}.{self.content_id}.{self.field_name}>"


class Language(Base):
    """Supported languages in the system."""
    __tablename__ = 'languages'

    code = Column(String(10), primary_key=True)  # e.g., 'en', 'ru', 'es', 'fr'
    name = Column(String(50), nullable=False)    # Native name of the language
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Only one language can be default
    sort_order = Column(Integer, default=0)      # For language selector ordering
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Language {self.code} ({self.name})>"


# Add these to __all__ if needed in other modules
__all__ = ['InterfaceTranslation', 'ContentTranslation', 'Language', 'TranslationType']
