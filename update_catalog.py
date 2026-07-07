from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


SOURCE_URL = "https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/formatted/items.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "items_catalog.json"

ALLOWED_SUFFIX_PREFIXES = (
    "MAIN_",
    "2H_",
    "OFF_",
    "HEAD_",
    "ARMOR_",
    "SHOES_",
    "BAG",
    "CAPE",
    "MOUNT_",
    "TOOL_",
    "ARTEFACT_",
    "ORE",
    "WOOD",
    "ROCK",
    "HIDE",
    "FIBER",
    "METALBAR",
    "PLANKS",
    "STONEBLOCK",
    "LEATHER",
    "CLOTH",
)


def get_unique_name(item: dict[str, Any]) -> str:
    value = item.get("UniqueName") or item.get("@uniquename") or ""
    return str(value)


def get_localized_name(item: dict[str, Any], locale: str) -> str:
    names = item.get("LocalizedNames") or item.get("localizedNames") or {}
    if not isinstance(names, dict):
        return ""
    return str(names.get(locale) or "")


def should_include_item(item_id: str, english_name: str) -> bool:
    if not item_id.startswith("T"):
        return False
    if "_" not in item_id:
        return False
    if not english_name:
        return False
    if item_id.endswith("_BP") or "_BP@" in item_id:
        return False

    suffix = item_id.split("_", 1)[1]
    return suffix.startswith(ALLOWED_SUFFIX_PREFIXES)


def build_catalog(raw_items: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    catalog: dict[str, dict[str, str]] = {}

    for item in raw_items:
        item_id = get_unique_name(item)
        english_name = get_localized_name(item, "EN-US")
        spanish_name = get_localized_name(item, "ES-ES")

        if not should_include_item(item_id, english_name):
            continue

        catalog[item_id] = {
            "en": english_name,
            "es": spanish_name,
        }

    return dict(sorted(catalog.items()))


def main() -> None:
    response = requests.get(SOURCE_URL, timeout=60)
    response.raise_for_status()
    raw_items = response.json()

    if not isinstance(raw_items, list):
        raise ValueError("El metadata oficial no tiene el formato esperado.")

    catalog = build_catalog(raw_items)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Catalogo generado: {OUTPUT_PATH}")
    print(f"Items incluidos: {len(catalog)}")


if __name__ == "__main__":
    main()
