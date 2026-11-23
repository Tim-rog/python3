import json

import pytest
from conftest import make_room

from src.catalog import Catalog
from src.errors import CorruptedFileError, UnsupportedFormatVersionError


def test_json_roundtrip(filled, tmp_path):
    path = tmp_path / "cat.json"
    filled.save(path)
    restored = Catalog()
    restored.load(path)
    assert list(restored) == list(filled)  # содержимое и порядок
    assert restored.find_by_category("лекционная") == filled.find_by_category(
        "лекционная"
    )


def test_format_vers_in_root(filled, tmp_path):
    path = tmp_path / "cat.json"
    filled.save(path)
    assert json.loads(path.read_text(encoding="utf-8"))["format_vers"] == 2


def test_cyrillic_not_escaped(filled, tmp_path):
    path = tmp_path / "cat.json"
    filled.save(path)
    assert "Большая лекционная" in path.read_text(encoding="utf-8")


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


BAD_DOCS = [
    "{not json",  # битый JSON
    "[]",  # корень не объект
    '{"items": []}',  # нет версии
    '{"format_vers": "2", "items": []}',  # версия не int
    '{"format_vers": 2, "items": {}}',  # items не список
    '{"format_vers": 2, "items": [1]}',  # элемент не объект
    '{"format_vers": 2, "items": [{"id": "x"}]}',  # не хватает полей
]


@pytest.mark.parametrize("text", BAD_DOCS)
def test_corrupted_file(tmp_path, text):
    with pytest.raises(CorruptedFileError):
        Catalog().load(write(tmp_path / "bad.json", text))


def test_invalid_entity_inside_file_is_corruption(tmp_path):
    doc = {"format_vers": 2, "items": [{**make_room().to_dict(), "capacity": -1}]}
    with pytest.raises(CorruptedFileError):
        Catalog().load(write(tmp_path / "bad.json", json.dumps(doc)))


def test_duplicate_id_in_file(tmp_path):
    item = make_room().to_dict()
    doc = {"format_vers": 2, "items": [item, item]}
    with pytest.raises(CorruptedFileError):
        Catalog().load(write(tmp_path / "bad.json", json.dumps(doc)))


def test_unknown_version(tmp_path):
    with pytest.raises(UnsupportedFormatVersionError):
        Catalog().load(write(tmp_path / "v.json", '{"format_vers": 999, "items": []}'))


def test_missing_file_propagates_oserror(tmp_path):
    with pytest.raises(FileNotFoundError):
        Catalog().load(tmp_path / "nope.json")


def test_failed_load_does_not_change_existing_catalog(filled, tmp_path):
    """Ключевой тест: ошибка загрузки не должна менять каталог ни частично, ни совсем."""
    before_items = list(filled)
    before_cat = filled.find_by_category("лекционная")

    good = make_room("g1").to_dict()
    bad = {**make_room("g2").to_dict(), "year": "abc"}
    # первый элемент валиден, второй - нет: частичная загрузка была бы заметна
    path = write(
        tmp_path / "bad.json", json.dumps({"format_vers": 2, "items": [good, bad]})
    )
    with pytest.raises(CorruptedFileError):
        filled.load(path)

    assert list(filled) == before_items
    assert filled.find_by_category("лекционная") == before_cat
    assert "g1" not in filled


@pytest.mark.parametrize("text", ["{not json", '{"format_vers": 999, "items": []}'])
def test_failed_load_keeps_catalog_for_other_errors(filled, tmp_path, text):
    before = list(filled)
    with pytest.raises(Exception):
        filled.load(write(tmp_path / "bad.json", text))
    assert list(filled) == before


def test_migration_v1_to_v2(tmp_path):
    old = make_room().to_dict()
    old["name"] = old.pop("title")  # в v1 поле звалось name
    path = write(tmp_path / "v1.json", json.dumps({"format_vers": 1, "items": [old]}))
    c = Catalog()
    c.load(path)
    assert c.get("r1").title == "Большая лекционная"


def test_save_is_atomic_no_tmp_left(filled, tmp_path):
    filled.save(tmp_path / "cat.json")
    assert [p.name for p in tmp_path.iterdir()] == ["cat.json"]
