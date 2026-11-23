import pytest

from src.catalog import Catalog, Room


def make_room(id="r1", **kw):
    """Проиводит валидные аудитории, чтобы проверить код."""
    data = dict(
        id=id,
        title="Большая лекционная",
        category="лекционная",
        year=1985,
        building="Главный корпус",
        floor=1,
        capacity=120,
        equipment=("проектор",),
    )
    data.update(kw)
    return Room(**data)


@pytest.fixture
def filled():
    c = Catalog()
    c.add(make_room("r1"))
    c.add(make_room("r2", title="Малая лекционная", year=1990, capacity=60))
    c.add(
        make_room(
            "r3",
            title="Компьютерный класс 3",
            category="компьютерный класс",
            year=2015,
            floor=3,
            capacity=24,
            equipment=("ПК", "проектор"),
        )
    )
    return c


@pytest.fixture
def room():
    return make_room()
