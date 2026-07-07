from __future__ import annotations

from dataclasses import dataclass

from crafting_models import CraftingModifierBook, CraftingRecipe
from models import MarketPrice


@dataclass(frozen=True)
class MaterialCost:
    item_id: str
    count_per_unit: float
    total_count: float
    unit_price: int
    gross_cost: float
    returned_value: float
    net_cost: float
    returnable: bool


@dataclass(frozen=True)
class CityProfit:
    city: str
    sell_price: int
    gross_revenue: float
    market_tax: float
    net_revenue: float
    profit_total: float
    profit_per_unit: float
    margin_percent: float
    silver_per_focus: float


@dataclass(frozen=True)
class ReturnRateInfo:
    return_rate_percent: float
    production_bonus_percent: float
    base_bonus_percent: float
    category_bonus_percent: float
    focus_bonus_percent: float
    source: str


def production_bonus_to_return_rate_percent(production_bonus: float) -> float:
    if production_bonus <= 0:
        return 0.0
    return (1 - (1 / (1 + production_bonus))) * 100


def calculate_return_rate_info(
    recipe: CraftingRecipe,
    crafting_city: str,
    modifier_book: CraftingModifierBook,
    use_focus: bool,
    manual_return_rate_percent: float,
    auto_return_rate: bool,
) -> ReturnRateInfo:
    if not auto_return_rate:
        manual_rate = max(0.0, min(manual_return_rate_percent, 95.0))
        return ReturnRateInfo(
            return_rate_percent=manual_rate,
            production_bonus_percent=0.0,
            base_bonus_percent=0.0,
            category_bonus_percent=0.0,
            focus_bonus_percent=0.0,
            source="Manual",
        )

    location = modifier_book.get_city(crafting_city)
    if location is None:
        return ReturnRateInfo(
            return_rate_percent=0.0,
            production_bonus_percent=0.0,
            base_bonus_percent=0.0,
            category_bonus_percent=0.0,
            focus_bonus_percent=0.0,
            source="Sin modificador",
        )

    base_bonus = (
        location.refining_bonus
        if modifier_book.is_refining_category(recipe.category)
        else location.crafting_bonus
    )
    category_bonus = location.get_category_bonus(recipe.category)
    focus_bonus = modifier_book.focus_production_bonus if use_focus and recipe.focus > 0 else 0.0
    total_bonus = base_bonus + category_bonus + focus_bonus

    return ReturnRateInfo(
        return_rate_percent=production_bonus_to_return_rate_percent(total_bonus),
        production_bonus_percent=total_bonus * 100,
        base_bonus_percent=base_bonus * 100,
        category_bonus_percent=category_bonus * 100,
        focus_bonus_percent=focus_bonus * 100,
        source="Automatico",
    )


def first_valid_sell_price(prices: list[MarketPrice], item_id: str, city: str, quality: int = 1) -> int:
    candidates = [
        price.sell_price_min
        for price in prices
        if price.item_id == item_id
        and price.city == city
        and price.quality == quality
        and price.sell_price_min > 0
    ]
    if not candidates:
        return 0
    return min(candidates)


def build_material_costs(
    recipe: CraftingRecipe,
    prices: list[MarketPrice],
    material_city: str,
    quantity: int,
    return_rate_percent: float,
) -> list[MaterialCost]:
    material_costs: list[MaterialCost] = []
    return_rate = max(0.0, min(return_rate_percent, 95.0)) / 100

    for material in recipe.materials:
        unit_price = first_valid_sell_price(prices, material.item_id, material_city)
        total_count = material.count * quantity
        gross_cost = total_count * unit_price
        returned_value = gross_cost * return_rate if material.returnable else 0.0

        material_costs.append(
            MaterialCost(
                item_id=material.item_id,
                count_per_unit=material.count,
                total_count=total_count,
                unit_price=unit_price,
                gross_cost=gross_cost,
                returned_value=returned_value,
                net_cost=gross_cost - returned_value,
                returnable=material.returnable,
            )
        )

    return material_costs


def calculate_city_profit(
    recipe: CraftingRecipe,
    item_prices: list[MarketPrice],
    city: str,
    quantity: int,
    net_crafting_cost: float,
    market_tax_percent: float,
    use_focus: bool,
) -> CityProfit:
    sell_price = first_valid_sell_price(item_prices, recipe.item_id, city)
    gross_revenue = sell_price * quantity
    market_tax = gross_revenue * max(0.0, market_tax_percent) / 100
    net_revenue = gross_revenue - market_tax
    profit_total = net_revenue - net_crafting_cost
    profit_per_unit = profit_total / quantity if quantity else 0.0
    margin_percent = (profit_total / net_crafting_cost * 100) if net_crafting_cost > 0 else 0.0
    total_focus = recipe.focus * quantity if use_focus else 0
    silver_per_focus = profit_total / total_focus if total_focus else 0.0

    return CityProfit(
        city=city,
        sell_price=sell_price,
        gross_revenue=gross_revenue,
        market_tax=market_tax,
        net_revenue=net_revenue,
        profit_total=profit_total,
        profit_per_unit=profit_per_unit,
        margin_percent=margin_percent,
        silver_per_focus=silver_per_focus,
    )
