from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


SOURCE_URL = "https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/items.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "recipes.json"


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


def optional_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def walk_items(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    if isinstance(value, dict):
        if "@uniquename" in value and "craftingrequirements" in value:
            found.append(value)
        for child in value.values():
            found.extend(walk_items(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk_items(child))

    return found


def output_item_id(base_item_id: str, enchantment: int) -> str:
    if enchantment <= 0:
        return base_item_id
    return f"{base_item_id}@{enchantment}"


def parse_materials(crafting_requirements: dict[str, Any]) -> list[dict[str, Any]]:
    materials: list[dict[str, Any]] = []

    for resource in as_list(crafting_requirements.get("craftresource")):
        if not isinstance(resource, dict):
            continue

        item_id = str(resource.get("@uniquename") or "")
        count = optional_float(resource.get("@count"))
        if not item_id or count <= 0:
            continue

        materials.append(
            {
                "item_id": item_id,
                "count": count,
                "enchantment": optional_int(resource.get("@enchantmentlevel")),
                "returnable": str(resource.get("@maxreturnamount") or "").strip() != "0",
            }
        )

    return materials


def parse_recipe(
    item: dict[str, Any],
    base_item_id: str,
    crafting_requirements: dict[str, Any],
    enchantment: int,
) -> dict[str, Any] | None:
    materials = parse_materials(crafting_requirements)
    if not materials:
        return None

    return {
        "item_id": output_item_id(base_item_id, enchantment),
        "base_item_id": base_item_id,
        "tier": optional_int(item.get("@tier")),
        "enchantment": enchantment,
        "category": str(item.get("@craftingcategory") or item.get("@shopsubcategory1") or ""),
        "silver": optional_float(crafting_requirements.get("@silver")),
        "time": optional_float(crafting_requirements.get("@time")),
        "focus": optional_int(crafting_requirements.get("@craftingfocus")),
        "materials": materials,
    }


def parse_item_recipes(item: dict[str, Any]) -> list[dict[str, Any]]:
    base_item_id = str(item.get("@uniquename") or "")
    if not base_item_id.startswith("T"):
        return []

    recipes: list[dict[str, Any]] = []

    base_requirements = item.get("craftingrequirements")
    if isinstance(base_requirements, dict):
        recipe = parse_recipe(item, base_item_id, base_requirements, 0)
        if recipe is not None:
            recipes.append(recipe)

    enchantments = item.get("enchantments")
    if isinstance(enchantments, dict):
        for enchantment_data in as_list(enchantments.get("enchantment")):
            if not isinstance(enchantment_data, dict):
                continue
            enchantment_level = optional_int(enchantment_data.get("@enchantmentlevel"))
            requirements = enchantment_data.get("craftingrequirements")
            if isinstance(requirements, dict):
                recipe = parse_recipe(item, base_item_id, requirements, enchantment_level)
                if recipe is not None:
                    recipes.append(recipe)

    return recipes


def build_recipe_book(raw_data: dict[str, Any]) -> dict[str, Any]:
    recipes: dict[str, Any] = {}

    for item in walk_items(raw_data):
        for recipe in parse_item_recipes(item):
            recipes[recipe["item_id"]] = recipe

    return dict(sorted(recipes.items()))


def main() -> None:
    response = requests.get(SOURCE_URL, timeout=60)
    response.raise_for_status()
    raw_data = response.json()

    if not isinstance(raw_data, dict):
        raise ValueError("El dump oficial de items no tiene el formato esperado.")

    recipes = build_recipe_book(raw_data)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(recipes, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"Recetas generadas: {OUTPUT_PATH}")
    print(f"Items con receta: {len(recipes)}")


if __name__ == "__main__":
    main()
