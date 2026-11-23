from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from .models import Room

if TYPE_CHECKING:  # только для аннотаций, избегаем циклического импорта
    from .catalog import Catalog


class CatalogView:
    __slots__ = ("_catalog",)

    def __init__(self, catalog: Catalog) -> None:
        self._catalog = catalog

    def get(self, item_id: str) -> Room:
        return self._catalog.get(item_id)

    def find_by_category(self, category: str) -> tuple[Room, ...]:
        return self._catalog.find_by_category(category)

    def find_by_name(self, query: str) -> tuple[Room, ...]:
        return self._catalog.find_by_name(query)

    def __len__(self) -> int:
        return len(self._catalog)

    def __iter__(self) -> Iterator[Room]:
        return iter(self._catalog)

    def __contains__(self, item_id: object) -> bool:
        return item_id in self._catalog
