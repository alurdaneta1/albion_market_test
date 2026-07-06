"""Editable settings for the Albion market test app."""

from catalog import ALL_LOCATIONS_LABEL, ITEM_CATALOG, SPANISH_ITEM_CATALOG

ITEMS: list[str] = [
    "T4_BAG",
    "T4_CAPE",
    "T4_ORE",
]

ITEM_NAMES: dict[str, str] = {
    **ITEM_CATALOG,
}

ITEM_NAMES_ES: dict[str, str] = {
    **SPANISH_ITEM_CATALOG,
}

PRODUCT_MODES: dict[str, str] = {
    "Catalogo completo": "catalog",
    "Solo seleccionados": "selected",
}

DEFAULT_PRODUCT_MODE = "Catalogo completo"

LOCATIONS: list[str] = [
    "Bridgewatch",
    "Martlock",
    "Caerleon",
    "Thetford",
    "Fort Sterling",
    "Lymhurst",
    "Brecilien",
    "Black Market",
]

LOCATION_CHOICES: list[str] = [
    "Bridgewatch",
    ALL_LOCATIONS_LABEL,
    "Martlock",
    "Caerleon",
    "Thetford",
    "Fort Sterling",
    "Lymhurst",
    "Brecilien",
    "Black Market",
]

DEFAULT_LOCATION = "Bridgewatch"

TIER_CHOICES: list[str] = [
    "Todos",
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
    "T6",
    "T7",
    "T8",
]

ENCHANTMENT_CHOICES: list[str] = [
    "Todos",
    "Sin encantamiento",
    ".1",
    ".2",
    ".3",
    ".4",
]

QUALITY_CHOICES: dict[str, int | None] = {
    "Todas": None,
    "Normal": 1,
    "Bueno": 2,
    "Sobresaliente": 3,
    "Excelente": 4,
    "Obra maestra": 5,
}

QUALITY_NAMES: dict[int, str] = {
    1: "Normal",
    2: "Bueno",
    3: "Sobresaliente",
    4: "Excelente",
    5: "Obra maestra",
}

SERVERS: dict[str, str] = {
    "Americas": "https://west.albion-online-data.com",
    "Europe": "https://europe.albion-online-data.com",
    "Asia": "https://east.albion-online-data.com",
}

AUTO_REFRESH_INTERVALS: dict[str, int] = {
    "30 segundos": 30,
    "60 segundos": 60,
    "5 minutos": 300,
}

REQUEST_TIMEOUT_SECONDS = 15
MAX_ITEMS_PER_REQUEST = 80
MAX_ITEMS_PER_UPDATE = 400

DATA_CLIENT_AUTO_START = True
DATA_CLIENT_PATHS: list[str] = [
    r"C:\Program Files\Albion Data Client\albiondata-client.exe",
    r"C:\Program Files (x86)\Albion Data Client\albiondata-client.exe",
]
DATA_CLIENT_ARGS: list[str] = []
