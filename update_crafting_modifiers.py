from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


SOURCE_URL = "https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/craftingmodifiers.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "crafting_modifiers.json"

CITY_CLUSTER_IDS: dict[str, str] = {
    "Thetford": "0000",
    "Lymhurst": "1000",
    "Martlock": "2000",
    "Bridgewatch": "3004",
    "Fort Sterling": "4000",
    "Caerleon": "3003",
    "Brecilien": "5000",
}

FOCUS_PRODUCTION_BONUS = 0.59


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def optional_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def get_node_float(node: Any, key: str) -> float:
    if not isinstance(node, dict):
        return 0.0
    return optional_float(node.get(key))


def parse_refining_categories(root: dict[str, Any]) -> list[str]:
    refining_category = root.get("refiningcategory")
    if not isinstance(refining_category, dict):
        return []

    categories: list[str] = []
    for item in as_list(refining_category.get("item")):
        if isinstance(item, dict):
            category = str(item.get("@category") or "")
            if category:
                categories.append(category)
    return sorted(set(categories))


def parse_location(raw_location: dict[str, Any]) -> dict[str, Any]:
    modifiers: dict[str, float] = {}
    for modifier in as_list(raw_location.get("craftingmodifier")):
        if not isinstance(modifier, dict):
            continue
        name = str(modifier.get("@name") or "")
        value = optional_float(modifier.get("@value"))
        if name:
            modifiers[name] = value

    return {
        "cluster_id": str(raw_location.get("@clusterid") or ""),
        "crafting_bonus": get_node_float(raw_location.get("craftingbonus"), "@value"),
        "refining_bonus": get_node_float(raw_location.get("refiningbonus"), "@value"),
        "modifiers": dict(sorted(modifiers.items())),
    }


def build_modifier_book(raw_data: dict[str, Any]) -> dict[str, Any]:
    root = raw_data.get("craftingmodifiers")
    if not isinstance(root, dict):
        raise ValueError("El archivo oficial de modificadores no tiene el formato esperado.")

    locations_by_cluster: dict[str, dict[str, Any]] = {}
    for raw_location in as_list(root.get("craftinglocation")):
        if not isinstance(raw_location, dict):
            continue
        cluster_id = str(raw_location.get("@clusterid") or "")
        if cluster_id:
            locations_by_cluster[cluster_id] = parse_location(raw_location)

    cities: dict[str, dict[str, Any]] = {}
    for city, cluster_id in CITY_CLUSTER_IDS.items():
        location = locations_by_cluster.get(cluster_id)
        if location is not None:
            cities[city] = location

    return {
        "cities": dict(sorted(cities.items())),
        "city_cluster_ids": CITY_CLUSTER_IDS,
        "focus_production_bonus": FOCUS_PRODUCTION_BONUS,
        "refining_categories": parse_refining_categories(root),
    }


def main() -> None:
    response = requests.get(SOURCE_URL, timeout=60)
    response.raise_for_status()
    raw_data = response.json()

    if not isinstance(raw_data, dict):
        raise ValueError("El archivo oficial de modificadores no tiene el formato esperado.")

    modifiers = build_modifier_book(raw_data)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(modifiers, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"Modificadores generados: {OUTPUT_PATH}")
    print(f"Ciudades incluidas: {len(modifiers['cities'])}")


if __name__ == "__main__":
    main()
