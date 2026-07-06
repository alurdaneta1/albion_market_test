from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


LOCAL_TIMEZONE = datetime.now().astimezone().tzinfo


def parse_api_datetime(value: Any) -> datetime | None:
    """Parse Albion Data Project dates and convert them to local time."""
    if not isinstance(value, str) or not value:
        return None

    cleaned_value = value.strip()
    if not cleaned_value or cleaned_value.startswith("0001-01-01"):
        return None

    try:
        parsed = datetime.fromisoformat(cleaned_value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(LOCAL_TIMEZONE)


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S %Z")


def format_age(value: datetime | None, now: datetime | None = None) -> str:
    if value is None:
        return ""

    current_time = now or datetime.now().astimezone()
    seconds = max(0, int((current_time - value).total_seconds()))

    if seconds < 60:
        return f"{seconds} s"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"

    hours = minutes // 60
    remaining_minutes = minutes % 60
    if hours < 24:
        return f"{hours} h {remaining_minutes} min"

    days = hours // 24
    remaining_hours = hours % 24
    return f"{days} d {remaining_hours} h"


def freshness_status(
    sell_price_min: int,
    sell_updated_at: datetime | None,
    buy_price_max: int,
    buy_updated_at: datetime | None,
    now: datetime | None = None,
) -> str:
    valid_dates: list[datetime] = []

    if sell_price_min > 0 and sell_updated_at is not None:
        valid_dates.append(sell_updated_at)
    if buy_price_max > 0 and buy_updated_at is not None:
        valid_dates.append(buy_updated_at)

    if not valid_dates:
        return "Sin datos"

    current_time = now or datetime.now().astimezone()
    newest_update = max(valid_dates)
    age_minutes = (current_time - newest_update).total_seconds() / 60

    if age_minutes < 5:
        return "Reciente"
    if age_minutes <= 30:
        return "Precaución"
    return "Desactualizado"


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def format_number(value: int | None) -> str:
    if value is None or value == 0:
        return ""
    return f"{value:,}".replace(",", ".")


@dataclass(frozen=True)
class MarketPrice:
    item_id: str
    city: str
    quality: int
    sell_price_min: int
    sell_price_min_quantity: int | None
    sell_price_min_date: datetime | None
    buy_price_max: int
    buy_price_max_quantity: int | None
    buy_price_max_date: datetime | None

    @classmethod
    def from_api(cls, raw_data: dict[str, Any]) -> MarketPrice:
        return cls(
            item_id=str(raw_data.get("item_id") or ""),
            city=str(raw_data.get("city") or ""),
            quality=optional_int(raw_data.get("quality")) or 0,
            sell_price_min=optional_int(raw_data.get("sell_price_min")) or 0,
            sell_price_min_quantity=optional_int(
                raw_data.get("sell_price_min_quantity")
                or raw_data.get("sell_order_min_quantity")
                or raw_data.get("sell_quantity")
            ),
            sell_price_min_date=parse_api_datetime(raw_data.get("sell_price_min_date")),
            buy_price_max=optional_int(raw_data.get("buy_price_max")) or 0,
            buy_price_max_quantity=optional_int(
                raw_data.get("buy_price_max_quantity")
                or raw_data.get("buy_order_max_quantity")
                or raw_data.get("buy_quantity")
            ),
            buy_price_max_date=parse_api_datetime(raw_data.get("buy_price_max_date")),
        )

    @property
    def newest_update(self) -> datetime | None:
        dates = [
            date_value
            for price, date_value in (
                (self.sell_price_min, self.sell_price_min_date),
                (self.buy_price_max, self.buy_price_max_date),
            )
            if price > 0 and date_value is not None
        ]
        if not dates:
            return None
        return max(dates)

    def status(self) -> str:
        return freshness_status(
            self.sell_price_min,
            self.sell_price_min_date,
            self.buy_price_max,
            self.buy_price_max_date,
        )

    def age_text(self) -> str:
        return format_age(self.newest_update)

    def as_table_values(self) -> tuple[str, ...]:
        return (
            self.item_id,
            self.city,
            str(self.quality),
            format_number(self.sell_price_min),
            format_number(self.sell_price_min_quantity),
            format_datetime(self.sell_price_min_date),
            format_number(self.buy_price_max),
            format_number(self.buy_price_max_quantity),
            format_datetime(self.buy_price_max_date),
            self.age_text(),
            self.status(),
        )
