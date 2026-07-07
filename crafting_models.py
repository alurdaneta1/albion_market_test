from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def get_app_base_path() -> Path:
    bundle_path = getattr(sys, "_MEIPASS", None)
    if bundle_path:
        return Path(bundle_path)
    return Path(__file__).resolve().parent


RECIPES_PATH = get_app_base_path() / "data" / "recipes.json"


@dataclass(frozen=True)
class CraftingMaterial:
    item_id: str
    count: float
    enchantment: int
    returnable: bool


@dataclass(frozen=True)
class CraftingRecipe:
    item_id: str
    base_item_id: str
    tier: int
    enchantment: int
    category: str
    silver: float
    time: float
    focus: int
    materials: tuple[CraftingMaterial, ...]

    @classmethod
    def from_dict(cls, raw_data: dict[str, Any]) -> CraftingRecipe:
        materials = tuple(
            CraftingMaterial(
                item_id=str(material.get("item_id") or ""),
                count=float(material.get("count") or 0),
                enchantment=int(material.get("enchantment") or 0),
                returnable=bool(material.get("returnable", True)),
            )
            for material in raw_data.get("materials", [])
            if isinstance(material, dict)
        )

        return cls(
            item_id=str(raw_data.get("item_id") or ""),
            base_item_id=str(raw_data.get("base_item_id") or ""),
            tier=int(raw_data.get("tier") or 0),
            enchantment=int(raw_data.get("enchantment") or 0),
            category=str(raw_data.get("category") or ""),
            silver=float(raw_data.get("silver") or 0),
            time=float(raw_data.get("time") or 0),
            focus=int(raw_data.get("focus") or 0),
            materials=materials,
        )


def load_recipes() -> dict[str, CraftingRecipe]:
    if not RECIPES_PATH.exists():
        return {}

    raw_recipes = json.loads(RECIPES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw_recipes, dict):
        return {}

    recipes: dict[str, CraftingRecipe] = {}
    for item_id, raw_recipe in raw_recipes.items():
        if isinstance(item_id, str) and isinstance(raw_recipe, dict):
            recipe = CraftingRecipe.from_dict(raw_recipe)
            if recipe.item_id and recipe.materials:
                recipes[item_id] = recipe

    return recipes
