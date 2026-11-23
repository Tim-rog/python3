from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING, dataclass, fields
from datetime import date
from typing import Any

from .errors import InvalidEntityError

min_year = 1800  # год ввода аудитории в эксплуатацию: не раньше
min_floor, max_floor = -2, 30  # подвалы допустимы
max_cap = 1000

# Допустимые категории в канонической форме (нижний регистр).
ROOM_CATEGORIES = frozenset(
    {"лекционная", "практическая", "компьютерный класс", "лаборатория"}
)
# Для этих категорий оборудование обязательно (межполевой инвариант;
# правило придумано для примера, при желании его легко убрать).
EQUIPMENT_REQUIRED = frozenset({"компьютерный класс", "лаборатория"})


def _require_text(name: str, value: Any) -> str:
    """Поле обязано быть непустой строкой; возвращаем её без пробелов по краям."""
    if not isinstance(value, str) or not value.strip():
        raise InvalidEntityError(
            f"Поле {name!r} должно быть непустой строкой, получено {value!r}"
        )
    return value.strip()


def _require_int(name: str, value: Any) -> int:
    """Поле обязано быть int. bool - подкласс int (True == 1), его исключаем."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidEntityError(
            f"Поле {name!r} должно быть целым числом, получено {value!r}"
        )
    return value


@dataclass(frozen=True)
class Room:
    """Учебная аудитория.

    Обязательные поля из задания: id, title, category, year (год ввода).
    Поля варианта: building, floor, capacity, equipment.
    """

    id: str  # например "Л-101"
    title: str  # название: "Большая лекционная"
    category: str  # одна из ROOM_CATEGORIES (хранится в нижнем регистре)
    year: int  # год ввода в эксплуатацию
    building: str  # корпус
    floor: int  # этаж
    capacity: int  # число посадочных мест
    equipment: tuple[
        str, ...
    ] = ()  # кортеж, а не list: frozen не защищает от мутации list

    def __post_init__(self) -> None:
        room_id = _require_text("id", self.id)
        title = _require_text("title", self.title)
        building = _require_text("building", self.building)

        category = _require_text("category", self.category).casefold()
        if category not in ROOM_CATEGORIES:
            raise InvalidEntityError(
                f"Неизвестная категория {self.category!r}; "
                f"допустим {sorted(ROOM_CATEGORIES)}"
            )

        year = _require_int("year", self.year)
        if not min_year <= year <= date.today().year:
            raise InvalidEntityError(
                f"Год должен быть в диапазоне {min_year}..{date.today().year}, "
                f"получено {year}"
            )

        floor = _require_int("floor", self.floor)
        if not min_floor <= floor <= max_floor:
            raise InvalidEntityError(
                f"Этаж должен быть в диапазоне {min_floor}..{max_floor}, получено {floor}"
            )

        capacity = _require_int("capacity", self.capacity)
        if not 0 < capacity <= max_cap:
            raise InvalidEntityError(
                f"Вместимость должна быть в диапазоне 1..{max_cap}, получено {capacity}"
            )

        if not isinstance(self.equipment, (list, tuple)):
            raise InvalidEntityError(
                f"equipment должно быть списком строк, получено {self.equipment!r}"
            )
        equipment = tuple(_require_text("equipment[]", e) for e in self.equipment)

        if category in EQUIPMENT_REQUIRED and not equipment:
            raise InvalidEntityError(
                f"Для категории {category!r} нужно указать оборудование"
            )

        object.__setattr__(self, "id", room_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "building", building)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "equipment", equipment)

    def to_dict(self) -> dict[str, Any]:
        """Представление для JSON (tuple -> list)."""
        data = {f.name: getattr(self, f.name) for f in fields(self)}
        data["equipment"] = list(self.equipment)
        return data

    @classmethod
    def from_dict(cls, data: Any) -> Room:
        """Собрать аудиторию из словаря; любая ошибка - InvalidEntityError.

        Лишние и отсутствующие обязательные ключи - ошибка: так мы замечаем
        повреждённые документы, а не молча теряем данные.
        """
        if not isinstance(data, Mapping):
            raise InvalidEntityError(f"Ожидался объект JSON, получено {data!r}")

        allowed = {f.name for f in fields(cls)}
        required = {f.name for f in fields(cls) if f.default is MISSING}
        missing = required - data.keys()
        extra = data.keys() - allowed
        if missing or extra:
            raise InvalidEntityError(
                f"Неверный набор полей: нет {sorted(missing)}, лишние {sorted(extra)}"
            )
        return cls(**data)
