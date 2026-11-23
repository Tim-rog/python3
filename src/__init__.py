"""Пакет каталога библиотечных аудиторий."""

from .catalog import Catalog
from .errors import (
    CatalogError,
    CorruptedFileError,
    DuplicateIdError,
    InvalidEntityError,
    ItemNotFoundError,
    NothingToUndoError,
    UnsupportedFormatVersionError,
)
from .models import Room
from .view import CatalogView

__all__ = [
    "Catalog",
    "CatalogError",
    "CatalogView",
    "CorruptedFileError",
    "DuplicateIdError",
    "InvalidEntityError",
    "ItemNotFoundError",
    "NothingToUndoError",
    "Room",
    "UnsupportedFormatVersionError",
]
