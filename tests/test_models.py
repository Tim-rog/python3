import pytest
from conftest import make_room

from src.catalog import InvalidEntityError, Room


def test_valid_room():
    r = make_room()
    assert r.id == "r1" and r.capacity == 120


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", ""),
        ("id", "   "),
        ("id", 5),
        ("title", ""),
        ("building", " "),
        ("category", None),
        ("category", "столовая"),  # не из списка
        ("year", "abc"),
        ("year", 1700),
        ("year", 3000),
        ("year", True),
        ("year", 1985.5),
        ("floor", -3),
        ("floor", 31),
        ("floor", "1"),
        ("floor", True),
        ("capacity", 0),
        ("capacity", -5),
        ("capacity", 5000),
        ("capacity", True),
        ("capacity", "10"),
        ("equipment", "проектор"),  # строка, а не список
        ("equipment", [""]),
        ("equipment", [5]),
    ],
)
def test_invalid_room(field, value):
    with pytest.raises(InvalidEntityError):
        make_room(**{field: value})


def test_cross_field_invariant():
    with pytest.raises(InvalidEntityError):
        make_room(category="компьютерный класс", equipment=())
    make_room(
        category="лекционная", equipment=()
    )  # для лекционной можно без оборудования


def test_post_init_normalizes():
    r = make_room(id=" Л-1 ", category="  Лекционная ", equipment=["проектор"])
    assert r.id == "Л-1"
    assert r.category == "лекционная"
    assert r.equipment == ("проектор",)  # list -> tuple


def test_room_is_immutable_and_hashable():
    r = make_room()
    with pytest.raises(Exception):
        r.title = "x"
    assert hash(r) == hash(make_room())  # tuple в equipment -> хешируется


def test_dict_roundtrip():
    r = make_room()
    d = r.to_dict()
    assert isinstance(d["equipment"], list)  # JSON-совместимо
    assert Room.from_dict(d) == r


def test_equipment_optional_in_dict():
    d = make_room(equipment=()).to_dict()
    del d["equipment"]
    assert Room.from_dict(d).equipment == ()


@pytest.mark.parametrize(
    "data",
    [
        "строка",
        None,
        {},
        {"id": "1"},
        {**make_room().to_dict(), "extra": 1},
    ],
)
def test_from_dict_rejects_bad_data(data):
    with pytest.raises(InvalidEntityError):
        Room.from_dict(data)
