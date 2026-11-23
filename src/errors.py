class CatalogError(Exception):
    """Базовая ошибка пакета."""


class InvalidEntityError(CatalogError):
    """Сущность нарушает инварианты (пустой id, неверный год и т. п.)."""


class DuplicateIdError(CatalogError):
    """Попытка добавить объект с уже существующим id."""


class ItemNotFoundError(CatalogError):
    """Объект с таким id отсутствует в каталоге."""


class UnsupportedFormatVersionError(CatalogError):
    """В файле указана версия формата, которую мы не умеем читать."""


class CorruptedFileError(CatalogError):
    """Файл не является корректным JSON или не соответствует схеме."""


class NothingToUndoError(CatalogError):
    """История операций пуста (или достигнута граница транзакции)."""
