""
Internationalization (i18n) utilities for handling translations.
"""
from typing import Dict, Optional, Union, Any

from fastapi import Depends, Request
from fastapi.requests import HTTPConnection
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import get_db
from app.models.translation import (
    InterfaceTranslation,
    ContentTranslation,
    TranslationType,
    Language
)
from app.core.config import settings

class TranslationService:
    """Service for handling translations."""
    
    def __init__(self, db: Session, default_language: str = 'ru'):
        self.db = db
        self.default_language = default_language
        self._cache = {}
        self._languages = None
    
    async def get_languages(self) -> list[dict]:
        """Get all active languages."""
        if self._languages is None:
            languages = self.db.query(Language).filter(
                Language.is_active == True  # noqa: E712
            ).order_by(Language.sort_order).all()
            self._languages = [
                {"code": lang.code, "name": lang.name, "is_default": lang.is_default}
                for lang in languages
            ]
        return self._languages
    
    async def get_interface_translation(
        self,
        key: str,
        module: str,
        language: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Get a translation for an interface element."""
        if language is None:
            language = self.default_language
            
        # Check cache first
        cache_key = f"{module}.{key}.{language}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # Query the database
        translation = self.db.query(InterfaceTranslation).filter(
            InterfaceTranslation.key == key,
            InterfaceTranslation.module == module
        ).first()
        
        if not translation:
            # Return the key if no translation found (helpful for development)
            self._cache[cache_key] = key
            return key
            
        # Get the translation for the requested language
        translated_text = getattr(translation, language, None)
        
        # Fallback to default language if translation is missing
        if not translated_text:
            translated_text = getattr(translation, self.default_language, key)
        
        # Format with kwargs if provided
        if kwargs and isinstance(translated_text, str):
            translated_text = translated_text.format(**kwargs)
            
        self._cache[cache_key] = translated_text
        return translated_text
    
    async def get_content_translation(
        self,
        content_type: Union[str, TranslationType],
        content_id: int,
        field_name: str,
        language: Optional[str] = None,
        default: Optional[str] = None
    ) -> Optional[str]:
        """Get a translation for content."""
        if language is None:
            language = self.default_language
            
        # Check cache first
        cache_key = f"{content_type}.{content_id}.{field_name}.{language}"
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        # Query the database
        translation = self.db.query(ContentTranslation).filter(
            ContentTranslation.content_type == content_type,
            ContentTranslation.content_id == content_id,
            ContentTranslation.field_name == field_name
        ).first()
        
        if not translation:
            return default
            
        # Get the translation for the requested language
        translated_text = getattr(translation, language, None)
        
        # Fallback to default language if translation is missing
        if not translated_text:
            translated_text = getattr(translation, self.default_language, default)
            
        self._cache[cache_key] = translated_text
        return translated_text
    
    def clear_cache(self):
        """Clear the translation cache."""
        self._cache.clear()
        self._languages = None


def get_translation_service(db: Session = Depends(get_db)) -> TranslationService:
    """Dependency to get a translation service instance."""
    return TranslationService(db=db, default_language=settings.DEFAULT_LANGUAGE)


def get_request_language(request: Request) -> str:
    """Get the language from the request (header, cookie, or default)."""
    # Check Accept-Language header
    accept_language = request.headers.get('accept-language')
    if accept_language:
        # Parse the first language from the header
        # Format: 'en-US,en;q=0.9,ru;q=0.8'
        lang = accept_language.split(',')[0].split(';')[0].lower()
        # Only return if it's a supported language
        if lang in settings.SUPPORTED_LANGUAGES:
            return lang
    
    # Check language cookie
    lang_cookie = request.cookies.get('lang')
    if lang_cookie and lang_cookie in settings.SUPPORTED_LANGUAGES:
        return lang_cookie
    
    # Default to settings
    return settings.DEFAULT_LANGUAGE


# Shortcut functions for common use cases
async def t(
    key: str,
    module: str,
    request: Optional[HTTPConnection] = None,
    db: Optional[Session] = None,
    *,
    **kwargs: Any
) -> str:
    """
    Shortcut function to get a translation.

    Example:
        await t("login_button", "auth", request)
    """
    if not db:
        from app.db.session import get_db as get_db_session
        db = next(get_db_session())
        
    service = TranslationService(db=db, default_language=settings.DEFAULT_LANGUAGE)
    
    language = None
    if hasattr(request, 'state') and hasattr(request.state, 'language'):
        language = request.state.language
    
    return await service.get_interface_translation(
        key=key,
        module=module,
        language=language,
        **kwargs
    )
