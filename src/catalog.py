from __future__ import annotations

import os
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Any

from . import storage
from .errors import (
    DuplicateIdError,
    InvalidEntityError,
    ItemNotFoundError,
    NothingToUndoError,
)
from .models import Room
from .view import CatalogView


def norm(text: str) -> str:
    return text.strip().casefold()


class Catalog:
    """Каталог аудиторий.

    Порядок итерации: в порядке добавления. Если элемент удалить и добавить
    снова, он окажется в конце. После load() порядок равен порядку в файле.
    Все find_* возвращают новые кортежи в том же порядке.
    """

    def __init__(self, items: Iterable[Room] = ()) -> None:
        self._items: dict[str, Room] = {}
        self._by_category: dict[str, dict[str, None]] = {}

        self._history: list[tuple[Any, ...]] = []
        self._floor = 0
        for item in items:
            self.add(item)
        self._history.clear()

    def insert(self, item: Room) -> None:
        self._items[item.id] = item
        self._by_category.setdefault(norm(item.category), {})[item.id] = None

    def delete(self, item_id: str) -> Room:
        item = self._items.pop(item_id)
        key = norm(item.category)
        ids = self._by_category[key]
        del ids[item_id]
        if not ids:
            del self._by_category[key]
        return item

    def rebuild_index(self) -> None:
        """Пересобрать индекс с нуля по _items (после load/undo)."""
        self._by_category = {}
        for item in self._items.values():
            self._by_category.setdefault(norm(item.category), {})[item.id] = None

    def add(self, item: Room) -> None:
        """Добавить аудиторию. DuplicateIdError, если id уже занят."""
        if not isinstance(item, Room):
            raise InvalidEntityError(f"Ожидался Room, получено {type(item).__name__}")
        if item.id in self._items:
            raise DuplicateIdError(f"Аудитория с id {item.id!r} уже есть в каталоге")
        self.insert(item)
        self._history.append(("add", item.id))

    def get(self, item_id: str) -> Room:
        """Вернуть аудиторию по id (O(1)). ItemNotFoundError, если нет."""
        try:
            return self._items[item_id]
        except KeyError:
            raise ItemNotFoundError(f"Аудитория с id {item_id!r} не найдена") from None

    def remove(self, item_id: str) -> None:
        """Удалить аудиторию. ItemNotFoundError, если id отсутствует."""
        if item_id not in self._items:
            raise ItemNotFoundError(f"Аудитория с id {item_id!r} не найдена")
        position = list(self._items).index(item_id)
        item = self.delete(item_id)
        self._history.append(("remove", item, position))

    def find_by_category(self, category: str) -> tuple[Room, ...]:
        """Аудитории категории (без учёта регистра). Берём из индекса, не сканируя всё.

        Возвращается НОВЫЙ кортеж: внутренние структуры наружу не отдаём.
        """
        ids = self._by_category.get(norm(category), {})
        return tuple(self._items[i] for i in ids)

    def find_by_name(self, query: str) -> tuple[Room, ...]:
        """Аудитории, в названии которых есть подстрока query (без учёта регистра)."""
        q = norm(query)
        return tuple(b for b in self._items.values() if q in b.title.casefold())

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Room]:
        return iter(tuple(self._items.values()))

    def __contains__(self, item_id: object) -> bool:
        return item_id in self._items

    def view(self) -> CatalogView:
        return CatalogView(self)

    def _apply_inverse(self, op: tuple[Any, ...]) -> None:
        kind = op[0]
        if kind == "add":
            self.delete(op[1])
        elif kind == "remove":
            _, item, position = op
            pairs = list(self._items.items())
            pairs.insert(position, (item.id, item))
            self._items = dict(pairs)
            self.rebuild_index()
        elif kind == "replace":
            self._items = op[1]
            self.rebuild_index()
        else:  # pragma: no cover - внутренняя ошибка
            raise AssertionError(f"Неизвестная операция {kind!r}")

    def undo(self) -> None:
        """Отменить последнюю операцию (add / remove / load)."""
        if len(self._history) <= self._floor:
            raise NothingToUndoError("Нечего отменять")
        self._apply_inverse(self._history.pop())

    @contextmanager
    def transaction(self) -> Iterator[Catalog]:
        """Контекстный менеджер: при исключении все изменения внутри блока
        откатываются, исключение пробрасывается дальше.

        Откат идёт по журналу (без копирования каталога). Внутри блока undo()
        не может зайти за границу транзакции. Вложенные транзакции работают.
        """
        mark = len(self._history)
        previous_floor = self._floor
        self._floor = mark
        try:
            yield self
        except BaseException:
            while len(self._history) > mark:
                self._apply_inverse(self._history.pop())
            raise
        finally:
            self._floor = previous_floor

    def save(self, path: str | os.PathLike[str]) -> None:
        """Сохранить каталог в JSON (атомарно, версия формата в корне)."""
        storage.write_file(path, self._items.values())

    def load(self, path: str | os.PathLike[str]) -> None:
        """Заменить содержимое каталога данными из файла.

        Атомарность: файл целиком читается и проверяется в storage.read_file.
        Если там возникнет любая ошибка, до замены _items мы не дойдём и
        каталог останется нетронутым. Сама замена - присваивание, оно не падает.
        Загрузка попадает в журнал, поэтому её можно отменить через undo().
        """
        rooms = storage.read_file(path)  # может бросить CatalogError/OSError
        new_items = {r.id: r for r in rooms}
        self._history.append(("replace", self._items))
        self._items = new_items
        self.rebuild_index()
