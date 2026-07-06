from __future__ import annotations

import json
import re
import sys
from pathlib import Path


TIERS = range(2, 9)
EQUIPMENT_TIERS = range(4, 9)
ALL_LOCATIONS_LABEL = "Todas las ciudades"

RESOURCE_ITEMS: dict[str, str] = {
    "ORE": "Ore",
    "WOOD": "Wood",
    "ROCK": "Stone",
    "HIDE": "Hide",
    "FIBER": "Fiber",
    "METALBAR": "Metal Bar",
    "PLANKS": "Planks",
    "STONEBLOCK": "Stone Block",
    "LEATHER": "Leather",
    "CLOTH": "Cloth",
}

BASIC_EQUIPMENT: dict[str, str] = {
    "BAG": "Bag",
    "CAPE": "Cape",
}

TOOLS: dict[str, str] = {
    "TOOL_PICK": "Pickaxe",
    "TOOL_AXE": "Wood Axe",
    "TOOL_HAMMER": "Stone Hammer",
    "TOOL_KNIFE": "Skinning Knife",
    "TOOL_SICKLE": "Sickle",
}

WEAPONS: dict[str, str] = {
    "MAIN_SWORD": "Broadsword",
    "2H_CLAYMORE": "Claymore",
    "2H_DUALSWORD": "Dual Swords",
    "MAIN_AXE": "Battleaxe",
    "2H_AXE": "Greataxe",
    "2H_HALBERD": "Halberd",
    "MAIN_MACE": "Mace",
    "2H_MACE": "Heavy Mace",
    "2H_FLAIL": "Morning Star",
    "MAIN_HAMMER": "Hammer",
    "2H_HAMMER": "Great Hammer",
    "2H_POLEHAMMER": "Polehammer",
    "MAIN_DAGGER": "Dagger",
    "2H_DAGGERPAIR": "Dagger Pair",
    "2H_CLAWPAIR": "Claws",
    "MAIN_SPEAR": "Spear",
    "2H_SPEAR": "Pike",
    "2H_GLAIVE": "Glaive",
    "2H_QUARTERSTAFF": "Quarterstaff",
    "2H_IRONCLADEDSTAFF": "Iron-clad Staff",
    "2H_DOUBLEBLADEDSTAFF": "Double Bladed Staff",
    "2H_BOW": "Bow",
    "2H_LONGBOW": "Longbow",
    "2H_WARBOW": "Warbow",
    "MAIN_1HCROSSBOW": "Light Crossbow",
    "2H_CROSSBOW": "Crossbow",
    "2H_CROSSBOWLARGE": "Heavy Crossbow",
    "MAIN_FIRESTAFF": "Fire Staff",
    "2H_FIRESTAFF": "Great Fire Staff",
    "2H_INFERNOSTAFF": "Infernal Staff",
    "MAIN_FROSTSTAFF": "Frost Staff",
    "2H_FROSTSTAFF": "Great Frost Staff",
    "2H_GLACIALSTAFF": "Glacial Staff",
    "MAIN_ARCANESTAFF": "Arcane Staff",
    "2H_ARCANESTAFF": "Great Arcane Staff",
    "2H_ENIGMATICSTAFF": "Enigmatic Staff",
    "MAIN_HOLYSTAFF": "Holy Staff",
    "2H_HOLYSTAFF": "Great Holy Staff",
    "2H_DIVINESTAFF": "Divine Staff",
    "MAIN_NATURESTAFF": "Nature Staff",
    "2H_NATURESTAFF": "Great Nature Staff",
    "2H_WILDSTAFF": "Wild Staff",
    "MAIN_CURSEDSTAFF": "Cursed Staff",
    "2H_CURSEDSTAFF": "Great Cursed Staff",
    "2H_DEMONICSTAFF": "Demonic Staff",
}

ARTIFACT_WEAPONS: dict[str, tuple[str, str]] = {
    "MAIN_SPEAR_KEEPER": ("Heron Spear", "Lanza garza"),
    "2H_HARPOON_HELL": ("Spirithunter", "Cazador de espiritus"),
    "2H_TRIDENT_UNDEAD": ("Trinity Spear", "Lanza trinidad"),
    "MAIN_SPEAR_AVALON": ("Daybreaker", "Rompealbas"),
    "2H_GLAIVE_CRYSTAL": ("Rift Glaive", "Guja fisurante"),
}

SPANISH_ALIASES: dict[str, list[str]] = {
    "BAG": ["bolsa"],
    "CAPE": ["capa"],
    "ORE": ["mineral"],
    "WOOD": ["madera"],
    "ROCK": ["piedra"],
    "HIDE": ["piel"],
    "FIBER": ["fibra"],
    "METALBAR": ["lingote"],
    "PLANKS": ["tablones"],
    "STONEBLOCK": ["bloque de piedra"],
    "LEATHER": ["cuero"],
    "CLOTH": ["tela"],
    "MAIN_SWORD": ["espada", "espada ancha"],
    "2H_CLAYMORE": ["mandoble", "claymore"],
    "2H_DUALSWORD": ["espadas dobles"],
    "MAIN_AXE": ["hacha"],
    "2H_AXE": ["gran hacha"],
    "2H_HALBERD": ["alabarda"],
    "MAIN_MACE": ["maza"],
    "2H_MACE": ["maza pesada"],
    "2H_FLAIL": ["lucero del alba"],
    "MAIN_HAMMER": ["martillo"],
    "2H_HAMMER": ["gran martillo"],
    "2H_POLEHAMMER": ["martillo de asta"],
    "MAIN_DAGGER": ["daga"],
    "2H_DAGGERPAIR": ["par de dagas"],
    "2H_CLAWPAIR": ["garras"],
    "MAIN_SPEAR": ["lanza"],
    "2H_SPEAR": ["pica"],
    "MAIN_SPEAR_KEEPER": ["lanza garza", "garza", "heron spear"],
    "2H_HARPOON_HELL": ["cazador de espiritus", "spirithunter"],
    "2H_TRIDENT_UNDEAD": ["lanza trinidad", "trinity spear"],
    "MAIN_SPEAR_AVALON": ["rompealbas", "daybreaker"],
    "2H_GLAIVE": ["guja", "glaive"],
    "2H_GLAIVE_CRYSTAL": ["guja fisurante", "rift glaive"],
    "2H_QUARTERSTAFF": ["baston de combate", "baston"],
    "2H_IRONCLADEDSTAFF": ["baston blindado"],
    "2H_DOUBLEBLADEDSTAFF": ["baston de doble hoja"],
    "2H_BOW": ["arco"],
    "2H_LONGBOW": ["arco largo"],
    "2H_WARBOW": ["arco de guerra"],
    "MAIN_1HCROSSBOW": ["ballesta ligera"],
    "2H_CROSSBOW": ["ballesta"],
    "2H_CROSSBOWLARGE": ["ballesta pesada"],
    "MAIN_FIRESTAFF": ["baston de fuego"],
    "2H_FIRESTAFF": ["gran baston de fuego"],
    "2H_INFERNOSTAFF": ["baston infernal"],
    "MAIN_FROSTSTAFF": ["baston de escarcha"],
    "2H_FROSTSTAFF": ["gran baston de escarcha"],
    "2H_GLACIALSTAFF": ["baston glacial"],
    "MAIN_ARCANESTAFF": ["baston arcano"],
    "2H_ARCANESTAFF": ["gran baston arcano"],
    "2H_ENIGMATICSTAFF": ["baston enigmatico"],
    "MAIN_HOLYSTAFF": ["baston sagrado"],
    "2H_HOLYSTAFF": ["gran baston sagrado"],
    "2H_DIVINESTAFF": ["baston divino"],
    "MAIN_NATURESTAFF": ["baston natural"],
    "2H_NATURESTAFF": ["gran baston natural"],
    "2H_WILDSTAFF": ["baston salvaje"],
    "MAIN_CURSEDSTAFF": ["baston maldito"],
    "2H_CURSEDSTAFF": ["gran baston maldito"],
    "2H_DEMONICSTAFF": ["baston demoniaco"],
}

OFFHANDS: dict[str, str] = {
    "OFF_SHIELD": "Shield",
    "OFF_TOWERSHIELD": "Sarcophagus",
    "OFF_BOOK": "Tome of Spells",
    "OFF_ORB": "Eye of Secrets",
    "OFF_TORCH": "Torch",
}

ARMOR: dict[str, str] = {
    "HEAD_PLATE_SET1": "Soldier Helmet",
    "ARMOR_PLATE_SET1": "Soldier Armor",
    "SHOES_PLATE_SET1": "Soldier Boots",
    "HEAD_PLATE_SET2": "Knight Helmet",
    "ARMOR_PLATE_SET2": "Knight Armor",
    "SHOES_PLATE_SET2": "Knight Boots",
    "HEAD_PLATE_SET3": "Guardian Helmet",
    "ARMOR_PLATE_SET3": "Guardian Armor",
    "SHOES_PLATE_SET3": "Guardian Boots",
    "HEAD_LEATHER_SET1": "Mercenary Hood",
    "ARMOR_LEATHER_SET1": "Mercenary Jacket",
    "SHOES_LEATHER_SET1": "Mercenary Shoes",
    "HEAD_LEATHER_SET2": "Hunter Hood",
    "ARMOR_LEATHER_SET2": "Hunter Jacket",
    "SHOES_LEATHER_SET2": "Hunter Shoes",
    "HEAD_LEATHER_SET3": "Assassin Hood",
    "ARMOR_LEATHER_SET3": "Assassin Jacket",
    "SHOES_LEATHER_SET3": "Assassin Shoes",
    "HEAD_CLOTH_SET1": "Scholar Cowl",
    "ARMOR_CLOTH_SET1": "Scholar Robe",
    "SHOES_CLOTH_SET1": "Scholar Sandals",
    "HEAD_CLOTH_SET2": "Cleric Cowl",
    "ARMOR_CLOTH_SET2": "Cleric Robe",
    "SHOES_CLOTH_SET2": "Cleric Sandals",
    "HEAD_CLOTH_SET3": "Mage Cowl",
    "ARMOR_CLOTH_SET3": "Mage Robe",
    "SHOES_CLOTH_SET3": "Mage Sandals",
}

MOUNTS: dict[str, str] = {
    "MOUNT_HORSE": "Riding Horse",
    "MOUNT_OX": "Transport Ox",
}

TIER_NAMES: dict[int, str] = {
    2: "Novice's",
    3: "Journeyman's",
    4: "Adept's",
    5: "Expert's",
    6: "Master's",
    7: "Grandmaster's",
    8: "Elder's",
}


def with_tier_name(tier: int, name: str) -> str:
    return f"{TIER_NAMES.get(tier, f'T{tier}')} {name}"


def add_tiered_items(
    catalog: dict[str, str],
    item_templates: dict[str, str],
    tiers: range,
    include_enchantments: bool = False,
) -> None:
    for tier in tiers:
        for suffix, name in item_templates.items():
            item_id = f"T{tier}_{suffix}"
            catalog[item_id] = with_tier_name(tier, name)

            if include_enchantments:
                for enchantment in range(1, 5):
                    catalog[f"{item_id}@{enchantment}"] = (
                        f"{with_tier_name(tier, name)} .{enchantment}"
                    )


def add_tiered_named_items(
    english_catalog: dict[str, str],
    spanish_catalog: dict[str, str],
    item_templates: dict[str, tuple[str, str]],
    tiers: range,
    include_enchantments: bool = False,
) -> None:
    for tier in tiers:
        for suffix, (english_name, spanish_name) in item_templates.items():
            item_id = f"T{tier}_{suffix}"
            english_catalog[item_id] = with_tier_name(tier, english_name)
            spanish_catalog[item_id] = f"T{tier} {spanish_name}"

            if include_enchantments:
                for enchantment in range(1, 5):
                    enchanted_item_id = f"{item_id}@{enchantment}"
                    english_catalog[enchanted_item_id] = (
                        f"{with_tier_name(tier, english_name)} .{enchantment}"
                    )
                    spanish_catalog[enchanted_item_id] = (
                        f"T{tier} {spanish_name} .{enchantment}"
                    )


def build_catalogs() -> tuple[dict[str, str], dict[str, str]]:
    english_catalog: dict[str, str] = {}
    spanish_catalog: dict[str, str] = {}
    add_tiered_items(english_catalog, RESOURCE_ITEMS, TIERS, include_enchantments=True)
    add_tiered_items(english_catalog, BASIC_EQUIPMENT, EQUIPMENT_TIERS, include_enchantments=True)
    add_tiered_items(english_catalog, TOOLS, EQUIPMENT_TIERS, include_enchantments=False)
    add_tiered_items(english_catalog, WEAPONS, EQUIPMENT_TIERS, include_enchantments=True)
    add_tiered_items(english_catalog, OFFHANDS, EQUIPMENT_TIERS, include_enchantments=True)
    add_tiered_items(english_catalog, ARMOR, EQUIPMENT_TIERS, include_enchantments=True)
    add_tiered_items(english_catalog, MOUNTS, range(3, 9), include_enchantments=False)
    add_tiered_named_items(
        english_catalog,
        spanish_catalog,
        ARTIFACT_WEAPONS,
        EQUIPMENT_TIERS,
        include_enchantments=True,
    )
    return dict(sorted(english_catalog.items())), dict(sorted(spanish_catalog.items()))


def get_app_base_path() -> Path:
    bundle_path = getattr(sys, "_MEIPASS", None)
    if bundle_path:
        return Path(bundle_path)
    return Path(__file__).resolve().parent


CATALOG_DATA_PATH = get_app_base_path() / "data" / "items_catalog.json"


def load_generated_catalogs() -> tuple[dict[str, str], dict[str, str]]:
    if not CATALOG_DATA_PATH.exists():
        return {}, {}

    raw_catalog = json.loads(CATALOG_DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw_catalog, dict):
        return {}, {}

    english_catalog: dict[str, str] = {}
    spanish_catalog: dict[str, str] = {}

    for item_id, names in raw_catalog.items():
        if not isinstance(item_id, str) or not isinstance(names, dict):
            continue

        english_name = names.get("en")
        spanish_name = names.get("es")

        if isinstance(english_name, str) and english_name:
            english_catalog[item_id] = english_name
        if isinstance(spanish_name, str) and spanish_name:
            spanish_catalog[item_id] = spanish_name

    return dict(sorted(english_catalog.items())), dict(sorted(spanish_catalog.items()))


GENERATED_ITEM_CATALOG, GENERATED_SPANISH_ITEM_CATALOG = load_generated_catalogs()
FALLBACK_ITEM_CATALOG, FALLBACK_SPANISH_ITEM_CATALOG = build_catalogs()

ITEM_CATALOG = GENERATED_ITEM_CATALOG or FALLBACK_ITEM_CATALOG
SPANISH_ITEM_CATALOG = GENERATED_SPANISH_ITEM_CATALOG or FALLBACK_SPANISH_ITEM_CATALOG


def normalize_search_text(value: str) -> str:
    value = value.lower()
    value = value.replace("'s", "s").replace("’s", "s")
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return re.sub(r"[^a-z0-9@.]+", " ", value).strip()


def get_base_item_id(item_id: str) -> str:
    without_enchantment = item_id.split("@", 1)[0]
    parts = without_enchantment.split("_", 1)
    if len(parts) != 2:
        return without_enchantment
    return parts[1]


def get_item_search_text(item_id: str, item_name: str, spanish_name: str = "") -> str:
    base_item_id = get_base_item_id(item_id)
    tier_text = item_id.split("_", 1)[0].lower()
    aliases = SPANISH_ALIASES.get(base_item_id, [])
    return normalize_search_text(" ".join([item_id, item_name, spanish_name, tier_text, *aliases]))


def filter_catalog_items(catalog: dict[str, str], query: str) -> list[str]:
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return list(catalog.keys())

    terms = normalized_query.split()
    matches: list[str] = []
    for item_id, item_name in catalog.items():
        search_text = get_item_search_text(item_id, item_name, SPANISH_ITEM_CATALOG.get(item_id, ""))
        if all(term in search_text for term in terms):
            matches.append(item_id)

    return matches
