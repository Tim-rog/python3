import pytest
from conftest import make_room

from src.catalog import Catalog, DuplicateIdError, NothingToUndoError


def index_is_consistent(c: Catalog) -> bool:
    """Индекс по категории == прямой перебор всех аудиторий."""
    cats = {b.category.casefold() for b in c} | {"нет"}
    return all(
        c.find_by_category(cat) == tuple(b for b in c if b.category.casefold() == cat)
        for cat in cats
    )


# ---- индекс -------------------------------------------------------------


def test_index_consistent_after_operations(filled):
    assert index_is_consistent(filled)
    filled.remove("r1")
    assert index_is_consistent(filled)
    filled.add(make_room("r9", category="лаборатория", equipment=("вытяжка",)))
    assert index_is_consistent(filled)


# ---- undo ---------------------------------------------------------------


def test_undo_add(filled):
    filled.add(make_room("r9"))
    filled.undo()
    assert "r9" not in filled and index_is_consistent(filled)


def test_undo_remove_restores_position(filled):
    filled.remove("r2")
    filled.undo()
    assert [b.id for b in filled] == ["r1", "r2", "r3"]
    assert index_is_consistent(filled)


def test_undo_load(filled, tmp_path):
    before = list(filled)
    other = Catalog([make_room("z1")])
    other.save(tmp_path / "o.json")
    filled.load(tmp_path / "o.json")
    assert [b.id for b in filled] == ["z1"]
    filled.undo()
    assert list(filled) == before and index_is_consistent(filled)


def test_failed_operation_not_recorded(filled):
    with pytest.raises(DuplicateIdError):
        filled.add(make_room("r1"))
    filled.undo()  # отменяет b3 (последний успешный add)...
    assert "r3" not in filled  # ...а не неудачную попытку


def test_undo_empty():
    with pytest.raises(NothingToUndoError):
        Catalog().undo()


def test_initial_items_not_undoable():
    with pytest.raises(NothingToUndoError):
        Catalog([make_room()]).undo()


# ---- транзакции ---------------------------------------------------------


def test_transaction_commit(filled):
    with filled.transaction():
        filled.add(make_room("r9"))
    assert "r9" in filled


def test_transaction_rollback(filled):
    before = list(filled)
    with pytest.raises(RuntimeError), filled.transaction():
        filled.add(make_room("r9"))
        filled.remove("r1")
        raise RuntimeError("boom")
    assert list(filled) == before and index_is_consistent(filled)


def test_transaction_rollback_on_domain_error(filled):
    before = list(filled)
    with pytest.raises(DuplicateIdError), filled.transaction():
        filled.add(make_room("r9"))
        filled.add(make_room("r1"))  # дубликат -> откат b9
    assert list(filled) == before


def test_nested_transaction_inner_rollback_only(filled):
    with filled.transaction():
        filled.add(make_room("r8"))
        with pytest.raises(RuntimeError), filled.transaction():
            filled.add(make_room("r9"))
            raise RuntimeError
        assert "r9" not in filled and "r8" in filled
    assert "r8" in filled


def test_undo_cannot_cross_transaction_boundary(filled):
    with filled.transaction(), pytest.raises(NothingToUndoError):
        filled.undo()  # b3 добавлен до транзакции


def test_transaction_rolls_back_load(filled, tmp_path):
    before = list(filled)
    Catalog([make_room("z1")]).save(tmp_path / "o.json")
    with pytest.raises(RuntimeError), filled.transaction():
        filled.load(tmp_path / "o.json")
        raise RuntimeError
    assert list(filled) == before


# ---- read-only view -----------------------------------------------------


def test_view_reads_but_cannot_mutate(filled):
    v = filled.view()
    assert len(v) == 3 and "r1" in v and v.get("r1").id == "r1"
    assert [b.id for b in v.find_by_name("малая")] == ["r2"]
    assert not hasattr(v, "add") and not hasattr(v, "remove")
    filled.add(make_room("r9"))
    assert "r9" in v  # «живое» представление
