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
CRAFTING_MODIFIERS_PATH = get_app_base_path() / "data" / "crafting_modifiers.json"


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


@dataclass(frozen=True)
class CraftingLocationModifier:
    city: str
    cluster_id: str
    crafting_bonus: float
    refining_bonus: float
    modifiers: dict[str, float]

    @classmethod
    def from_dict(cls, city: str, raw_data: dict[str, Any]) -> CraftingLocationModifier:
        raw_modifiers = raw_data.get("modifiers")
        modifiers = {
            str(name): float(value or 0)
            for name, value in raw_modifiers.items()
            if isinstance(name, str)
        } if isinstance(raw_modifiers, dict) else {}

        return cls(
            city=city,
            cluster_id=str(raw_data.get("cluster_id") or ""),
            crafting_bonus=float(raw_data.get("crafting_bonus") or 0),
            refining_bonus=float(raw_data.get("refining_bonus") or 0),
            modifiers=modifiers,
        )

    def get_category_bonus(self, category: str) -> float:
        return self.modifiers.get(category, 0.0)


@dataclass(frozen=True)
class CraftingModifierBook:
    cities: dict[str, CraftingLocationModifier]
    refining_categories: set[str]
    focus_production_bonus: float

    def get_city(self, city: str) -> CraftingLocationModifier | None:
        return self.cities.get(city)

    def is_refining_category(self, category: str) -> bool:
        return category in self.refining_categories


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


def load_crafting_modifiers() -> CraftingModifierBook:
    if not CRAFTING_MODIFIERS_PATH.exists():
        return CraftingModifierBook(cities={}, refining_categories=set(), focus_production_bonus=0.59)

    raw_data = json.loads(CRAFTING_MODIFIERS_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        return CraftingModifierBook(cities={}, refining_categories=set(), focus_production_bonus=0.59)

    raw_cities = raw_data.get("cities")
    cities: dict[str, CraftingLocationModifier] = {}
    if isinstance(raw_cities, dict):
        for city, raw_city in raw_cities.items():
            if isinstance(city, str) and isinstance(raw_city, dict):
                cities[city] = CraftingLocationModifier.from_dict(city, raw_city)

    raw_refining_categories = raw_data.get("refining_categories")
    refining_categories = {
        str(category)
        for category in raw_refining_categories
        if isinstance(category, str)
    } if isinstance(raw_refining_categories, list) else set()

    return CraftingModifierBook(
        cities=cities,
        refining_categories=refining_categories,
        focus_production_bonus=float(raw_data.get("focus_production_bonus") or 0.59),
    )
