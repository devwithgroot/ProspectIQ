from __future__ import annotations

import json
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).with_name("catalog.json")


@lru_cache(maxsize=1)
def _raw() -> dict[str, Any]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("catalog.json must be an object")
    return payload


def _items(key: str) -> list[dict[str, str]]:
    items = _raw()[key]
    if not isinstance(items, list):
        raise ValueError(f"catalog.json {key} must be an array")
    return items


Industry = StrEnum(
    "Industry",
    {item["id"]: item["label"] for item in _items("industries")},
)

UserTitle = StrEnum(
    "UserTitle",
    {item["id"]: item["label"] for item in _items("titles")},
)


def _ids(values: list[str]) -> list[str]:
    return [value for value in values if value in UserTitle.__members__]


def common_title_ids() -> list[str]:
    return _ids(list(_raw()["common_title_ids"]))


def industry_title_ids(industry: Industry) -> list[str]:
    mapping = _raw()["titles_by_industry"]
    return _ids(list(mapping.get(industry.name, [])))


def title_ids_for(industry: Industry) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for title_id in industry_title_ids(industry) + common_title_ids():
        if title_id in seen:
            continue
        seen.add(title_id)
        ordered.append(title_id)
    return ordered


def titles_for(industry: Industry) -> list[UserTitle]:
    return [UserTitle[title_id] for title_id in title_ids_for(industry)]


def parse_industry(value: str) -> Industry:
    text = value.strip()
    if text in Industry.__members__:
        return Industry[text]
    for industry in Industry:
        if industry.value == text:
            return industry
    raise ValueError("Industry must be selected from the list.")


def parse_title(value: str) -> UserTitle:
    text = value.strip()
    if text in UserTitle.__members__:
        return UserTitle[text]
    for title in UserTitle:
        if title.value == text:
            return title
    raise ValueError("Title must be selected from the list.")


def title_allowed(title: UserTitle, industry: Industry) -> bool:
    return title.name in set(title_ids_for(industry))


def catalog_error(title: str, industry: str) -> str | None:
    if not industry.strip() or not title.strip():
        return None
    try:
        parsed_industry = parse_industry(industry)
    except ValueError as exc:
        return str(exc)
    try:
        parsed_title = parse_title(title)
    except ValueError as exc:
        return str(exc)
    if not title_allowed(parsed_title, parsed_industry):
        return (
            f"{parsed_title.value} is not a title used in "
            f"{parsed_industry.value}."
        )
    return None


def catalog_payload() -> dict[str, Any]:
    titles = {item["id"]: item["label"] for item in _items("titles")}
    by_industry: dict[str, list[dict[str, str]]] = {}
    for industry in Industry:
        specific = set(industry_title_ids(industry))
        options = []
        for title_id in title_ids_for(industry):
            options.append(
                {
                    "id": title_id,
                    "label": titles[title_id],
                    "group": (
                        "Common in this industry"
                        if title_id in specific
                        else "Sales and leadership"
                    ),
                }
            )
        by_industry[industry.name] = options
        by_industry[industry.value] = options

    return {
        "industries": _items("industries"),
        "titles": _items("titles"),
        "titles_by_industry": by_industry,
    }
