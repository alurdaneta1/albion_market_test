from __future__ import annotations

from typing import Any

import requests

from config import MAX_ITEMS_PER_REQUEST, REQUEST_TIMEOUT_SECONDS
from models import MarketPrice


class AlbionApiError(Exception):
    """Readable error raised when the market API cannot return valid data."""


def build_prices_url(base_url: str, item_ids: list[str]) -> str:
    cleaned_base_url = base_url.rstrip("/")
    joined_items = ",".join(item_ids)
    return f"{cleaned_base_url}/api/v2/stats/prices/{joined_items}.json"


def chunk_items(item_ids: list[str], chunk_size: int) -> list[list[str]]:
    return [item_ids[index : index + chunk_size] for index in range(0, len(item_ids), chunk_size)]


def validate_inputs(base_url: str, item_ids: list[str], locations: list[str]) -> None:
    if not base_url.startswith("https://"):
        raise AlbionApiError("El servidor configurado no parece ser una URL HTTPS válida.")
    if not item_ids:
        raise AlbionApiError("No hay productos configurados para consultar.")
    if not locations:
        raise AlbionApiError("No hay ciudades configuradas para consultar.")


def fetch_market_prices(
    base_url: str,
    item_ids: list[str],
    locations: list[str],
    qualities: list[int] | None = None,
    timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
) -> list[MarketPrice]:
    validate_inputs(base_url, item_ids, locations)

    params = {"locations": ",".join(locations)}
    if qualities:
        params["qualities"] = ",".join(str(quality) for quality in qualities)

    all_prices: list[MarketPrice] = []

    for item_chunk in chunk_items(item_ids, MAX_ITEMS_PER_REQUEST):
        url = build_prices_url(base_url, item_chunk)

        try:
            response = requests.get(url, params=params, timeout=timeout_seconds)
            response.raise_for_status()
        except requests.Timeout as exc:
            raise AlbionApiError("La consulta tardó demasiado y superó el timeout.") from exc
        except requests.ConnectionError as exc:
            raise AlbionApiError("No se pudo conectar con la API de Albion Online Data.") from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "desconocido"
            raise AlbionApiError(f"La API respondió con un error HTTP {status_code}.") from exc
        except requests.RequestException as exc:
            raise AlbionApiError(f"Error inesperado al consultar la API: {exc}") from exc

        try:
            raw_json: Any = response.json()
        except ValueError as exc:
            raise AlbionApiError("La API respondió, pero el contenido no es JSON válido.") from exc

        if not isinstance(raw_json, list):
            raise AlbionApiError("La API devolvió un formato inesperado: se esperaba una lista.")

        for index, row in enumerate(raw_json, start=1):
            if not isinstance(row, dict):
                raise AlbionApiError(f"Registro inválido en la posición {index}: se esperaba un objeto.")
            all_prices.append(MarketPrice.from_api(row))

    return all_prices
