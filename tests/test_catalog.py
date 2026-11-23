import pytest
from conftest import make_room

from src.catalog import Catalog
from src.errors import (
    CatalogError,
    DuplicateIdError,
    InvalidEntityError,
    ItemNotFoundError,
)


def test_add_get_remove(room):
    c = Catalog()
    c.add(room)
    assert c.get("r1") is room
    assert "r1" in c and len(c) == 1
    c.remove("r1")
    assert "r1" not in c and len(c) == 0


def test_get_missing():
    with pytest.raises(ItemNotFoundError):
        Catalog().get("nope")


def test_remove_missing():
    with pytest.raises(ItemNotFoundError):
        Catalog().remove("nope")


def test_domain_errors_share_base():
    with pytest.raises(CatalogError):
        Catalog().remove("nope")


def test_duplicate_id_rejected_and_catalog_unchanged(filled):
    before = list(filled)
    with pytest.raises(DuplicateIdError):
        filled.add(make_room("r1", title="Другая"))
    assert list(filled) == before


def test_add_rejects_non_book():
    c = Catalog()
    with pytest.raises(InvalidEntityError):
        c.add({"id": "x"})
    assert len(c) == 0


def test_invalid_entity_never_reaches_catalog():
    c = Catalog()
    with pytest.raises(InvalidEntityError):
        c.add(make_room(capacity=-1))  # падает ещё при создании
    assert len(c) == 0


def test_find_by_category(filled):
    assert [b.id for b in filled.find_by_category("лекционная")] == ["r1", "r2"]
    assert [b.id for b in filled.find_by_category("КОМПЬЮТЕРНЫЙ КЛАСС")] == ["r3"]
    assert filled.find_by_category("нет такой категории") == ()


def test_find_by_name_case_insensitive(filled):
    assert [b.id for b in filled.find_by_name("большая")] == ["r1"]
    assert [b.id for b in filled.find_by_name("КОМПЬЮТЕРНЫЙ")] == ["r3"]
    assert filled.find_by_name("zzz") == ()


def test_iteration_order_is_insertion_order(filled):
    assert [b.id for b in filled] == ["r1", "r2", "r3"]
    filled.remove("r1")
    filled.add(make_room("r1"))
    assert [b.id for b in filled] == ["r2", "r3", "r1"]  # переместился в конец


def test_search_results_do_not_expose_internals(filled):
    result = filled.find_by_category("лекционная")
    assert isinstance(result, tuple)  # кортеж нельзя мутировать
    assert filled.find_by_category("лекционная") is not result
    list(result).clear()
    assert len(filled.find_by_category("лекционная")) == 2


def test_iterating_while_modifying_is_safe(filled):
    for b in filled:
        filled.remove(b.id)
    assert len(filled) == 0
