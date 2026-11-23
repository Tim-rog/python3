"""Хранение каталога в JSON.

Формат документа:
    {"format_vers": 2, "items": [ {...room...}, ... ]}

Модуль не знает про класс Catalog: он только превращает аудитории в файл и
обратно. Благодаря этому разбор документа целиком происходит ДО того, как
каталог будет изменён (основа атомарной загрузки).
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable
from typing import Any

from .errors import (
    CorruptedFileError,
    InvalidEntityError,
    UnsupportedFormatVersionError,
)
from .models import Room

format_vers = 2  # версия, которую пишем
supp_vers = (1, 2)  # версии, которая читается


def migrate_v1_to_v2(doc: dict[str, Any]) -> dict[str, Any]:
    """Миграция из v1 в v2: в v1 название аудитории хранилось в поле "name",
    в v2 оно называется "title"."""
    items = doc.get("items")
    if not isinstance(items, list):
        raise CorruptedFileError("Поле 'items' должно быть списком")

    migrated = []
    for raw in items:
        if not isinstance(raw, dict):
            raise CorruptedFileError(f"Элемент должен быть объектом: {raw!r}")
        raw = dict(raw)  # не мутируем исходный документ
        if "name" in raw:
            if "title" in raw:
                raise CorruptedFileError("В элементе одновременно name и title")
            raw["title"] = raw.pop("name")
        migrated.append(raw)
    return {"format_vers": 2, "items": migrated}


def parse_document(data: Any) -> list[Room]:
    """Проверить документ и превратить его в список аудиторий.

    Ничего не изменяет снаружи: либо возвращает полный список, либо
    бросает исключение.
    """
    if not isinstance(data, dict):
        raise CorruptedFileError("Корень документа должен быть объектом")
    if "format_vers" not in data:
        raise CorruptedFileError("Нет поля format_vers")

    version = data["format_vers"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise CorruptedFileError(f"format_vers должен быть int: {version!r}")
    if version not in supp_vers:
        raise UnsupportedFormatVersionError(
            f"Версия формата {version} не поддерживается (поддерживаются {supp_vers})"
        )

    if version == 1:
        data = migrate_v1_to_v2(data)

    items = data.get("items")
    if not isinstance(items, list):
        raise CorruptedFileError("Поле 'items' должно быть списком")

    rooms: list[Room] = []
    seen: set[str] = set()
    for raw in items:
        try:
            room = Room.from_dict(raw)
        except InvalidEntityError as exc:
            # Неверная сущность внутри файла - это повреждение файла.
            raise CorruptedFileError(f"Некорректный элемент: {exc}") from exc
        if room.id in seen:
            raise CorruptedFileError(f"Дубликат id в файле: {room.id!r}")
        seen.add(room.id)
        rooms.append(room)
    return rooms


def read_file(path: str | os.PathLike[str]) -> list[Room]:
    """Прочитать файл и вернуть аудитории. OSError (нет файла и тд тп) не гасим."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CorruptedFileError(f"Файл не является корректным JSON: {exc}") from exc
    return parse_document(data)


def write_file(path: str | os.PathLike[str], items: Iterable[Room]) -> None:
    """Записать аудитории в json.

    Пишем во временный файл рядом с целевым и подменяем через os.replace.
    При сбое старый файл остаётся целым, а не полузаписанным.
    """
    doc = {"format_vers": format_vers, "items": [b.to_dict() for b in items]}
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
