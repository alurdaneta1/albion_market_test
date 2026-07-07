from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import ttk
from typing import Any

from api_client import AlbionApiError, fetch_market_prices
from catalog import (
    ALL_LOCATIONS_LABEL,
    ITEM_CATALOG,
    filter_catalog_items,
    get_item_search_text,
    normalize_search_text,
)
from config import (
    AUTO_REFRESH_INTERVALS,
    DATA_CLIENT_ARGS,
    DATA_CLIENT_AUTO_START,
    DATA_CLIENT_PATHS,
    DEFAULT_LOCATION,
    DEFAULT_PRODUCT_MODE,
    ENCHANTMENT_CHOICES,
    ITEM_NAMES,
    ITEM_NAMES_ES,
    ITEMS,
    LOCATION_CHOICES,
    LOCATIONS,
    MAX_ITEMS_PER_UPDATE,
    PRODUCT_MODES,
    QUALITY_CHOICES,
    QUALITY_NAMES,
    SERVERS,
    TIER_CHOICES,
)
from crafting_models import CraftingRecipe, load_recipes
from data_client import start_data_client
from models import MarketPrice, format_number
from profit_calculator import CityProfit, MaterialCost, build_material_costs, calculate_city_profit


MARKET_COLUMNS: tuple[tuple[str, str, int, str], ...] = (
    ("item_id", "ID del producto", 150, "w"),
    ("item_name", "Nombre EN", 210, "w"),
    ("item_name_es", "Nombre ES", 210, "w"),
    ("tier", "Tier", 55, "center"),
    ("enchantment", "Encant.", 70, "center"),
    ("city", "Ciudad", 110, "w"),
    ("quality", "Calidad", 100, "center"),
    ("sell_price_min", "Precio minimo venta", 145, "e"),
    ("sell_price_min_quantity", "Cantidad venta min.", 145, "e"),
    ("sell_price_min_date", "Fecha venta", 180, "w"),
    ("buy_price_max", "Precio maximo compra", 155, "e"),
    ("buy_price_max_quantity", "Cantidad compra max.", 150, "e"),
    ("buy_price_max_date", "Fecha compra", 185, "w"),
    ("age", "Antiguedad", 130, "w"),
    ("status", "Estado", 120, "w"),
)

MATERIAL_COLUMNS: tuple[tuple[str, str, int, str], ...] = (
    ("item_id", "Material ID", 170, "w"),
    ("item_name", "Nombre EN", 220, "w"),
    ("item_name_es", "Nombre ES", 220, "w"),
    ("qty_unit", "Cant./unidad", 95, "e"),
    ("qty_total", "Cant. total", 95, "e"),
    ("unit_price", "Precio unit.", 110, "e"),
    ("gross_cost", "Costo bruto", 120, "e"),
    ("returned_value", "Retorno", 120, "e"),
    ("net_cost", "Costo neto", 120, "e"),
    ("returnable", "Retorna", 80, "center"),
)

PROFIT_COLUMNS: tuple[tuple[str, str, int, str], ...] = (
    ("city", "Ciudad", 130, "w"),
    ("sell_price", "Precio venta", 120, "e"),
    ("net_revenue", "Ingreso neto", 125, "e"),
    ("total_cost", "Costo total", 125, "e"),
    ("profit_total", "Utilidad total", 125, "e"),
    ("profit_unit", "Utilidad/unidad", 125, "e"),
    ("margin", "Margen %", 90, "e"),
    ("silver_focus", "Silver/foco", 105, "e"),
)


@dataclass(frozen=True)
class UtilityResult:
    recipe: CraftingRecipe
    material_costs: list[MaterialCost]
    city_profits: list[CityProfit]
    total_cost: float
    missing_prices: list[str]
    received_records: int


class AlbionMarketApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Albion Market Test")
        self.geometry("1380x760")
        self.minsize(1040, 620)

        self.result_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.prices: list[MarketPrice] = []
        self.recipes = load_recipes()
        self.is_fetching = False
        self.is_calculating_profit = False
        self.auto_refresh_job: str | None = None
        self.market_sort_column = "item_id"
        self.market_sort_reverse = False
        self.material_sort_column = "item_id"
        self.material_sort_reverse = False
        self.profit_sort_column = "profit_total"
        self.profit_sort_reverse = True
        self.last_utility_result: UtilityResult | None = None

        self.server_name = tk.StringVar(value="Americas")
        self.product_mode = tk.StringVar(value=DEFAULT_PRODUCT_MODE)
        self.location_name = tk.StringVar(value=DEFAULT_LOCATION)
        self.search_text = tk.StringVar()
        self.tier_filter = tk.StringVar(value="Todos")
        self.enchantment_filter = tk.StringVar(value="Todos")
        self.quality_filter = tk.StringVar(value="Todas")
        self.auto_refresh_enabled = tk.BooleanVar(value=False)
        self.interval_label = tk.StringVar(value="60 segundos")
        self.status_text = tk.StringVar(value="Ultima consulta: - | Registros: 0 | Conexion: Sin consultar")

        self.utility_server_name = tk.StringVar(value="Americas")
        self.utility_search_text = tk.StringVar()
        self.utility_recipe_id = tk.StringVar()
        self.utility_tier_filter = tk.StringVar(value="Todos")
        self.utility_enchantment_filter = tk.StringVar(value="Todos")
        self.utility_material_city = tk.StringVar(value=DEFAULT_LOCATION)
        self.utility_quantity = tk.StringVar(value="1")
        self.utility_return_rate = tk.StringVar(value="15,2")
        self.utility_station_fee = tk.StringVar(value="0")
        self.utility_market_tax = tk.StringVar(value="6,5")
        self.utility_use_focus = tk.BooleanVar(value=True)
        self.utility_status_text = tk.StringVar(value="Utilidad: carga recetas con update_recipes.py si esta lista aparece vacia.")

        self._build_interface()
        self._configure_styles()
        self.search_text.trace_add("write", lambda *_: self.refresh_market_table())
        self.utility_search_text.trace_add("write", lambda *_: self.refresh_recipe_selector())
        self.utility_tier_filter.trace_add("write", lambda *_: self.refresh_recipe_selector())
        self.utility_enchantment_filter.trace_add("write", lambda *_: self.refresh_recipe_selector())
        self.after(100, self.process_result_queue)
        self.after(500, self.start_data_client_on_launch)

    def _build_interface(self) -> None:
        main_frame = ttk.Frame(self, padding=12)
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        title = ttk.Label(main_frame, text="Albion Market Test", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        market_tab = ttk.Frame(self.notebook, padding=8)
        utility_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(market_tab, text="Mercado")
        self.notebook.add(utility_tab, text="Utilidad")

        self._build_market_tab(market_tab)
        self._build_utility_tab(utility_tab)

    def _build_market_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(3, weight=1)

        toolbar = ttk.Frame(parent)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        toolbar.columnconfigure(9, weight=1)

        ttk.Label(toolbar, text="Servidor").grid(row=0, column=0, padx=(0, 6))
        ttk.Combobox(toolbar, textvariable=self.server_name, values=list(SERVERS.keys()), state="readonly", width=12).grid(
            row=0, column=1, padx=(0, 12)
        )

        ttk.Label(toolbar, text="Ciudad").grid(row=0, column=2, padx=(0, 6))
        ttk.Combobox(toolbar, textvariable=self.location_name, values=LOCATION_CHOICES, state="readonly", width=17).grid(
            row=0, column=3, padx=(0, 12)
        )

        ttk.Label(toolbar, text="Productos").grid(row=0, column=4, padx=(0, 6))
        ttk.Combobox(toolbar, textvariable=self.product_mode, values=list(PRODUCT_MODES.keys()), state="readonly", width=18).grid(
            row=0, column=5, padx=(0, 12)
        )

        ttk.Button(toolbar, text="Actualizar precios", command=self.start_price_update).grid(row=0, column=6, padx=(0, 12))

        ttk.Checkbutton(
            toolbar,
            text="Actualizacion automatica",
            variable=self.auto_refresh_enabled,
            command=self.on_auto_refresh_changed,
        ).grid(row=0, column=7, padx=(0, 8))

        ttk.Label(toolbar, text="Intervalo").grid(row=0, column=8, padx=(0, 6))
        interval_selector = ttk.Combobox(
            toolbar,
            textvariable=self.interval_label,
            values=list(AUTO_REFRESH_INTERVALS.keys()),
            state="readonly",
            width=12,
        )
        interval_selector.grid(row=0, column=9, sticky="w", padx=(0, 12))
        interval_selector.bind("<<ComboboxSelected>>", lambda _event: self.schedule_auto_refresh())

        search_row = ttk.Frame(parent)
        search_row.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        search_row.columnconfigure(1, weight=1)

        ttk.Label(search_row, text="Buscar producto").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(search_row, textvariable=self.search_text).grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(search_row, text="Ej: guja, glaive, t6 guja, guja fisurante").grid(row=0, column=2, sticky="e")

        filter_row = ttk.Frame(parent)
        filter_row.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        filter_row.columnconfigure(6, weight=1)

        ttk.Label(filter_row, text="Tier").grid(row=0, column=0, padx=(0, 6))
        tier_selector = ttk.Combobox(filter_row, textvariable=self.tier_filter, values=TIER_CHOICES, state="readonly", width=10)
        tier_selector.grid(row=0, column=1, padx=(0, 12))
        tier_selector.bind("<<ComboboxSelected>>", lambda _event: self.refresh_market_table())

        ttk.Label(filter_row, text="Encantamiento").grid(row=0, column=2, padx=(0, 6))
        enchantment_selector = ttk.Combobox(
            filter_row,
            textvariable=self.enchantment_filter,
            values=ENCHANTMENT_CHOICES,
            state="readonly",
            width=18,
        )
        enchantment_selector.grid(row=0, column=3, padx=(0, 12))
        enchantment_selector.bind("<<ComboboxSelected>>", lambda _event: self.refresh_market_table())

        ttk.Label(filter_row, text="Calidad").grid(row=0, column=4, padx=(0, 6))
        quality_selector = ttk.Combobox(
            filter_row,
            textvariable=self.quality_filter,
            values=list(QUALITY_CHOICES.keys()),
            state="readonly",
            width=16,
        )
        quality_selector.grid(row=0, column=5, padx=(0, 12))
        quality_selector.bind("<<ComboboxSelected>>", lambda _event: self.refresh_market_table())

        table_frame = ttk.Frame(parent)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.market_tree = ttk.Treeview(
            table_frame,
            columns=[column_id for column_id, *_ in MARKET_COLUMNS],
            show="headings",
            height=18,
        )
        self.configure_tree_columns(self.market_tree, MARKET_COLUMNS, self.sort_market_by_column)

        vertical_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.market_tree.yview)
        horizontal_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.market_tree.xview)
        self.market_tree.configure(yscrollcommand=vertical_scrollbar.set, xscrollcommand=horizontal_scrollbar.set)
        self.market_tree.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        footer = ttk.Label(parent, textvariable=self.status_text, anchor="w")
        footer.grid(row=4, column=0, sticky="ew", pady=(10, 0))

    def _build_utility_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(3, weight=1)

        top_row = ttk.Frame(parent)
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_row.columnconfigure(7, weight=1)

        ttk.Label(top_row, text="Servidor").grid(row=0, column=0, padx=(0, 6))
        ttk.Combobox(
            top_row,
            textvariable=self.utility_server_name,
            values=list(SERVERS.keys()),
            state="readonly",
            width=12,
        ).grid(row=0, column=1, padx=(0, 12))

        ttk.Label(top_row, text="Buscar item").grid(row=0, column=2, padx=(0, 6))
        ttk.Entry(top_row, textvariable=self.utility_search_text, width=34).grid(row=0, column=3, padx=(0, 12))

        ttk.Label(top_row, text="Receta").grid(row=0, column=4, padx=(0, 6))
        self.recipe_selector = ttk.Combobox(top_row, textvariable=self.utility_recipe_id, state="readonly", width=42)
        self.recipe_selector.grid(row=0, column=5, sticky="ew", padx=(0, 12))
        self.recipe_selector.bind("<<ComboboxSelected>>", lambda _event: self.on_recipe_selected())

        ttk.Button(top_row, text="Calcular utilidad", command=self.start_profit_calculation).grid(row=0, column=6, padx=(0, 12))

        filter_row = ttk.Frame(parent)
        filter_row.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        filter_row.columnconfigure(13, weight=1)

        ttk.Label(filter_row, text="Tier").grid(row=0, column=0, padx=(0, 6))
        ttk.Combobox(filter_row, textvariable=self.utility_tier_filter, values=TIER_CHOICES, state="readonly", width=8).grid(
            row=0, column=1, padx=(0, 12)
        )

        ttk.Label(filter_row, text="Encant.").grid(row=0, column=2, padx=(0, 6))
        ttk.Combobox(
            filter_row,
            textvariable=self.utility_enchantment_filter,
            values=ENCHANTMENT_CHOICES,
            state="readonly",
            width=16,
        ).grid(row=0, column=3, padx=(0, 12))

        ttk.Label(filter_row, text="Ciudad materiales").grid(row=0, column=4, padx=(0, 6))
        ttk.Combobox(
            filter_row,
            textvariable=self.utility_material_city,
            values=LOCATIONS,
            state="readonly",
            width=15,
        ).grid(row=0, column=5, padx=(0, 12))

        ttk.Label(filter_row, text="Cantidad").grid(row=0, column=6, padx=(0, 6))
        ttk.Entry(filter_row, textvariable=self.utility_quantity, width=8).grid(row=0, column=7, padx=(0, 12))

        ttk.Label(filter_row, text="Retorno %").grid(row=0, column=8, padx=(0, 6))
        ttk.Entry(filter_row, textvariable=self.utility_return_rate, width=8).grid(row=0, column=9, padx=(0, 12))

        ttk.Label(filter_row, text="Fee/u").grid(row=0, column=10, padx=(0, 6))
        ttk.Entry(filter_row, textvariable=self.utility_station_fee, width=9).grid(row=0, column=11, padx=(0, 12))

        ttk.Label(filter_row, text="Impuesto %").grid(row=0, column=12, padx=(0, 6))
        ttk.Entry(filter_row, textvariable=self.utility_market_tax, width=8).grid(row=0, column=13, sticky="w", padx=(0, 12))

        ttk.Checkbutton(filter_row, text="Usar foco", variable=self.utility_use_focus).grid(row=0, column=14, padx=(0, 12))

        summary = ttk.Label(
            parent,
            text="Fase 1: usa recetas oficiales, precios de venta normales, retorno manual, fee manual e impuesto manual.",
            anchor="w",
        )
        summary.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        tables = ttk.PanedWindow(parent, orient="vertical")
        tables.grid(row=3, column=0, sticky="nsew")

        material_frame = ttk.Frame(tables)
        profit_frame = ttk.Frame(tables)
        tables.add(material_frame, weight=1)
        tables.add(profit_frame, weight=1)

        material_frame.columnconfigure(0, weight=1)
        material_frame.rowconfigure(1, weight=1)
        ttk.Label(material_frame, text="Materiales", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.material_tree = ttk.Treeview(
            material_frame,
            columns=[column_id for column_id, *_ in MATERIAL_COLUMNS],
            show="headings",
            height=8,
        )
        self.configure_tree_columns(self.material_tree, MATERIAL_COLUMNS, self.sort_materials_by_column)
        self.material_tree.grid(row=1, column=0, sticky="nsew")
        material_scrollbar = ttk.Scrollbar(material_frame, orient="vertical", command=self.material_tree.yview)
        material_scrollbar.grid(row=1, column=1, sticky="ns")
        self.material_tree.configure(yscrollcommand=material_scrollbar.set)

        profit_frame.columnconfigure(0, weight=1)
        profit_frame.rowconfigure(1, weight=1)
        ttk.Label(profit_frame, text="Ganancia por ciudad", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.profit_tree = ttk.Treeview(
            profit_frame,
            columns=[column_id for column_id, *_ in PROFIT_COLUMNS],
            show="headings",
            height=8,
        )
        self.configure_tree_columns(self.profit_tree, PROFIT_COLUMNS, self.sort_profits_by_column)
        self.profit_tree.grid(row=1, column=0, sticky="nsew")
        profit_scrollbar = ttk.Scrollbar(profit_frame, orient="vertical", command=self.profit_tree.yview)
        profit_scrollbar.grid(row=1, column=1, sticky="ns")
        self.profit_tree.configure(yscrollcommand=profit_scrollbar.set)

        footer = ttk.Label(parent, textvariable=self.utility_status_text, anchor="w")
        footer.grid(row=4, column=0, sticky="ew", pady=(10, 0))

        self.refresh_recipe_selector()

    def configure_tree_columns(
        self,
        tree: ttk.Treeview,
        columns: tuple[tuple[str, str, int, str], ...],
        sort_command: Any,
    ) -> None:
        for column_id, heading, width, anchor in columns:
            tree.heading(
                column_id,
                text=heading,
                anchor="center",
                command=lambda selected_column=column_id: sort_command(selected_column),
            )
            tree.column(column_id, width=width, minwidth=70, anchor=anchor, stretch=False)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=26)
        for tree_name in ("market_tree", "material_tree", "profit_tree"):
            tree = getattr(self, tree_name, None)
            if tree is not None:
                tree.tag_configure("Reciente", background="#e9f7ef")
                tree.tag_configure("Precaucion", background="#fff8dc")
                tree.tag_configure("Precaución", background="#fff8dc")
                tree.tag_configure("Desactualizado", background="#fdecea")
                tree.tag_configure("Sin datos", background="#f2f2f2")
                tree.tag_configure("profit_positive", background="#e9f7ef")
                tree.tag_configure("profit_negative", background="#fdecea")
                tree.tag_configure("missing_price", background="#fff8dc")

    def start_data_client_on_launch(self) -> None:
        if not DATA_CLIENT_AUTO_START:
            return

        message = start_data_client(DATA_CLIENT_PATHS, DATA_CLIENT_ARGS)
        self.set_market_status(connection_status=f"Data Client: {message}")

    def start_price_update(self) -> None:
        if self.is_fetching:
            self.set_market_status(connection_status="Ya hay una consulta en ejecucion")
            return

        requested_items = self.get_requested_items()
        requested_locations = self.get_requested_locations()
        requested_qualities = self.get_requested_qualities()

        if not requested_items:
            self.set_market_status(connection_status="No hay productos que coincidan con la busqueda")
            return

        if len(requested_items) > MAX_ITEMS_PER_UPDATE:
            self.set_market_status(
                connection_status=(
                    f"La busqueda encontro {len(requested_items)} productos. "
                    "Escribe un nombre mas especifico."
                )
            )
            return

        self.is_fetching = True
        self.set_market_status(
            connection_status=f"Consultando {len(requested_items)} productos en {len(requested_locations)} ciudad(es)..."
        )

        server_url = SERVERS[self.server_name.get()]
        worker = threading.Thread(
            target=self.fetch_prices_in_background,
            args=(server_url, requested_items, requested_locations, requested_qualities),
            daemon=True,
        )
        worker.start()

    def get_requested_items(self) -> list[str]:
        mode = PRODUCT_MODES.get(self.product_mode.get(), "catalog")
        if mode == "selected":
            item_names = {item_id: ITEM_NAMES.get(item_id, item_id) for item_id in ITEMS}
            return self.filter_item_ids(filter_catalog_items(item_names, self.search_text.get()))
        return self.filter_item_ids(filter_catalog_items(ITEM_CATALOG, self.search_text.get()))

    def get_requested_locations(self) -> list[str]:
        selected_location = self.location_name.get()
        if selected_location == ALL_LOCATIONS_LABEL:
            return LOCATIONS
        return [selected_location]

    def get_requested_qualities(self) -> list[int] | None:
        selected_quality = QUALITY_CHOICES.get(self.quality_filter.get())
        if selected_quality is None:
            return None
        return [selected_quality]

    def filter_item_ids(self, item_ids: list[str]) -> list[str]:
        return [
            item_id
            for item_id in item_ids
            if self.matches_tier_filter(item_id, self.tier_filter.get())
            and self.matches_enchantment_filter(item_id, self.enchantment_filter.get())
        ]

    def matches_tier_filter(self, item_id: str, selected_tier: str) -> bool:
        if selected_tier == "Todos":
            return True
        return self.get_item_tier_label(item_id) == selected_tier

    def matches_enchantment_filter(self, item_id: str, selected_enchantment: str) -> bool:
        if selected_enchantment == "Todos":
            return True
        if selected_enchantment == "Sin encantamiento":
            return self.get_item_enchantment_number(item_id) == 0
        return self.get_item_enchantment_label(item_id) == selected_enchantment

    def matches_quality_filter(self, quality: int) -> bool:
        selected_quality = QUALITY_CHOICES.get(self.quality_filter.get())
        if selected_quality is None:
            return True
        return quality == selected_quality

    def fetch_prices_in_background(
        self,
        server_url: str,
        item_ids: list[str],
        locations: list[str],
        qualities: list[int] | None,
    ) -> None:
        try:
            prices = fetch_market_prices(server_url, item_ids, locations, qualities=qualities)
        except AlbionApiError as exc:
            self.result_queue.put(("market_error", str(exc)))
        except Exception as exc:
            self.result_queue.put(("market_error", f"Error inesperado: {exc}"))
        else:
            self.result_queue.put(("market_success", prices))

    def process_result_queue(self) -> None:
        try:
            while True:
                event_type, payload = self.result_queue.get_nowait()

                if event_type == "market_success":
                    self.is_fetching = False
                    self.prices = payload
                    self.refresh_market_table()
                    self.set_market_status(record_count=len(self.prices), connection_status="OK")
                elif event_type == "market_error":
                    self.is_fetching = False
                    self.set_market_status(connection_status=payload)
                elif event_type == "profit_success":
                    self.is_calculating_profit = False
                    self.last_utility_result = payload
                    self.refresh_utility_tables()
                    self.set_utility_success_status(payload)
                elif event_type == "profit_error":
                    self.is_calculating_profit = False
                    self.utility_status_text.set(f"Utilidad: {payload}")
        except queue.Empty:
            pass

        self.after(100, self.process_result_queue)

    def refresh_market_table(self) -> None:
        filter_terms = normalize_search_text(self.search_text.get()).split()
        visible_prices = [
            price
            for price in self.prices
            if self.matches_tier_filter(price.item_id, self.tier_filter.get())
            and self.matches_enchantment_filter(price.item_id, self.enchantment_filter.get())
            and self.matches_quality_filter(price.quality)
            and (
                not filter_terms
                or all(
                    term
                    in get_item_search_text(
                        price.item_id,
                        self.get_item_name(price.item_id),
                        self.get_item_name_es(price.item_id),
                    )
                    for term in filter_terms
                )
            )
        ]

        visible_prices.sort(
            key=lambda price: self.get_market_sort_value(price, self.market_sort_column),
            reverse=self.market_sort_reverse,
        )

        self.market_tree.delete(*self.market_tree.get_children())
        for price in visible_prices:
            status = price.status()
            self.market_tree.insert("", "end", values=self.get_market_table_values(price), tags=(status,))

    def sort_market_by_column(self, column_id: str) -> None:
        if self.market_sort_column == column_id:
            self.market_sort_reverse = not self.market_sort_reverse
        else:
            self.market_sort_column = column_id
            self.market_sort_reverse = False
        self.refresh_market_table()

    def get_market_sort_value(self, price: MarketPrice, column_id: str) -> Any:
        def date_sort_value(value: Any) -> float:
            if value is None:
                return 0.0
            return value.timestamp()

        sort_values: dict[str, Any] = {
            "item_id": price.item_id,
            "item_name": self.get_item_name(price.item_id),
            "item_name_es": self.get_item_name_es(price.item_id),
            "tier": self.get_item_tier_number(price.item_id),
            "enchantment": self.get_item_enchantment_number(price.item_id),
            "city": price.city,
            "quality": price.quality,
            "sell_price_min": price.sell_price_min,
            "sell_price_min_quantity": price.sell_price_min_quantity or -1,
            "sell_price_min_date": date_sort_value(price.sell_price_min_date),
            "buy_price_max": price.buy_price_max,
            "buy_price_max_quantity": price.buy_price_max_quantity or -1,
            "buy_price_max_date": date_sort_value(price.buy_price_max_date),
            "age": date_sort_value(price.newest_update),
            "status": price.status(),
        }
        return sort_values.get(column_id, "")

    def get_market_table_values(self, price: MarketPrice) -> tuple[str, ...]:
        item_values = price.as_table_values()
        return (
            item_values[0],
            self.get_item_name(price.item_id),
            self.get_item_name_es(price.item_id),
            self.get_item_tier_label(price.item_id),
            self.get_item_enchantment_label(price.item_id),
            item_values[1],
            self.get_quality_label(price.quality),
            *item_values[3:],
        )

    def refresh_recipe_selector(self) -> None:
        if not hasattr(self, "recipe_selector"):
            return

        matching_recipes = self.get_matching_recipes(limit=80)
        values = [self.get_recipe_selector_label(recipe) for recipe in matching_recipes]
        self.recipe_selector.configure(values=values)

        selected_label = self.utility_recipe_id.get()
        selected_item_id = self.parse_recipe_selector_label(selected_label)
        if selected_item_id not in self.recipes:
            self.utility_recipe_id.set(values[0] if values else "")

        if values:
            self.utility_status_text.set(f"Utilidad: {len(values)} receta(s) encontradas. Selecciona una y calcula.")
        elif self.recipes:
            self.utility_status_text.set("Utilidad: no hay recetas que coincidan con la busqueda.")
        else:
            self.utility_status_text.set("Utilidad: no se encontro data/recipes.json. Ejecuta update_recipes.py.")

    def get_matching_recipes(self, limit: int | None = None) -> list[CraftingRecipe]:
        recipe_catalog = {item_id: self.get_item_name(item_id) for item_id in self.recipes}
        item_ids = filter_catalog_items(recipe_catalog, self.utility_search_text.get())
        matches: list[CraftingRecipe] = []
        for item_id in item_ids:
            recipe = self.recipes.get(item_id)
            if recipe is None:
                continue
            if not self.matches_tier_filter(recipe.item_id, self.utility_tier_filter.get()):
                continue
            if not self.matches_enchantment_filter(recipe.item_id, self.utility_enchantment_filter.get()):
                continue
            matches.append(recipe)
            if limit is not None and len(matches) >= limit:
                break
        return matches

    def get_selected_recipe(self) -> CraftingRecipe | None:
        selected_item_id = self.parse_recipe_selector_label(self.utility_recipe_id.get())
        if selected_item_id and selected_item_id in self.recipes:
            return self.recipes[selected_item_id]
        matches = self.get_matching_recipes(limit=1)
        return matches[0] if matches else None

    def get_recipe_selector_label(self, recipe: CraftingRecipe) -> str:
        english_name = self.get_item_name(recipe.item_id)
        spanish_name = self.get_item_name_es(recipe.item_id)
        label_name = english_name if not spanish_name else f"{english_name} / {spanish_name}"
        return f"{recipe.item_id} - {label_name}"

    def parse_recipe_selector_label(self, value: str) -> str:
        return value.split(" - ", 1)[0].strip()

    def on_recipe_selected(self) -> None:
        recipe = self.get_selected_recipe()
        if recipe is None:
            return
        self.utility_status_text.set(
            f"Utilidad: receta seleccionada {recipe.item_id}, materiales: {len(recipe.materials)}, foco/u: {recipe.focus}."
        )

    def start_profit_calculation(self) -> None:
        if self.is_calculating_profit:
            self.utility_status_text.set("Utilidad: ya hay un calculo en ejecucion.")
            return

        recipe = self.get_selected_recipe()
        if recipe is None:
            self.utility_status_text.set("Utilidad: selecciona una receta valida.")
            return

        try:
            quantity = max(1, int(float(self.utility_quantity.get().replace(",", "."))))
            return_rate = self.parse_float_setting(self.utility_return_rate.get())
            station_fee = max(0.0, self.parse_float_setting(self.utility_station_fee.get()))
            market_tax = max(0.0, self.parse_float_setting(self.utility_market_tax.get()))
        except ValueError as exc:
            self.utility_status_text.set(f"Utilidad: revisa cantidad, retorno, fee e impuesto. {exc}")
            return

        material_city = self.utility_material_city.get()
        server_url = SERVERS[self.utility_server_name.get()]
        self.is_calculating_profit = True
        self.utility_status_text.set(
            f"Utilidad: consultando materiales en {material_city} y venta en {len(LOCATIONS)} ciudades..."
        )

        worker = threading.Thread(
            target=self.calculate_profit_in_background,
            args=(server_url, recipe, material_city, quantity, return_rate, station_fee, market_tax, self.utility_use_focus.get()),
            daemon=True,
        )
        worker.start()

    def calculate_profit_in_background(
        self,
        server_url: str,
        recipe: CraftingRecipe,
        material_city: str,
        quantity: int,
        return_rate: float,
        station_fee: float,
        market_tax: float,
        use_focus: bool,
    ) -> None:
        try:
            material_item_ids = sorted({material.item_id for material in recipe.materials})
            material_prices = fetch_market_prices(server_url, material_item_ids, [material_city], qualities=[1])
            item_prices = fetch_market_prices(server_url, [recipe.item_id], LOCATIONS, qualities=[1])
            material_costs = build_material_costs(recipe, material_prices, material_city, quantity, return_rate)
            missing_prices = [cost.item_id for cost in material_costs if cost.unit_price <= 0]
            material_total = sum(cost.net_cost for cost in material_costs)
            station_total = station_fee * quantity
            crafting_silver_total = recipe.silver * quantity
            total_cost = material_total + station_total + crafting_silver_total
            city_profits = [
                calculate_city_profit(recipe, item_prices, city, quantity, total_cost, market_tax, use_focus)
                for city in LOCATIONS
            ]
            result = UtilityResult(
                recipe=recipe,
                material_costs=material_costs,
                city_profits=city_profits,
                total_cost=total_cost,
                missing_prices=missing_prices,
                received_records=len(material_prices) + len(item_prices),
            )
        except AlbionApiError as exc:
            self.result_queue.put(("profit_error", str(exc)))
        except Exception as exc:
            self.result_queue.put(("profit_error", f"Error inesperado: {exc}"))
        else:
            self.result_queue.put(("profit_success", result))

    def refresh_utility_tables(self) -> None:
        result = self.last_utility_result
        if result is None:
            return

        material_costs = sorted(
            result.material_costs,
            key=lambda cost: self.get_material_sort_value(cost, self.material_sort_column),
            reverse=self.material_sort_reverse,
        )
        city_profits = sorted(
            result.city_profits,
            key=lambda profit: self.get_profit_sort_value(profit, self.profit_sort_column, result.total_cost),
            reverse=self.profit_sort_reverse,
        )

        self.material_tree.delete(*self.material_tree.get_children())
        for cost in material_costs:
            tags = ("missing_price",) if cost.unit_price <= 0 else ()
            self.material_tree.insert("", "end", values=self.get_material_table_values(cost), tags=tags)

        self.profit_tree.delete(*self.profit_tree.get_children())
        for profit in city_profits:
            tags = ("profit_positive",) if profit.profit_total >= 0 else ("profit_negative",)
            self.profit_tree.insert("", "end", values=self.get_profit_table_values(profit, result.total_cost), tags=tags)

    def sort_materials_by_column(self, column_id: str) -> None:
        if self.material_sort_column == column_id:
            self.material_sort_reverse = not self.material_sort_reverse
        else:
            self.material_sort_column = column_id
            self.material_sort_reverse = False
        self.refresh_utility_tables()

    def sort_profits_by_column(self, column_id: str) -> None:
        if self.profit_sort_column == column_id:
            self.profit_sort_reverse = not self.profit_sort_reverse
        else:
            self.profit_sort_column = column_id
            self.profit_sort_reverse = column_id in {"profit_total", "profit_unit", "margin", "silver_focus"}
        self.refresh_utility_tables()

    def get_material_sort_value(self, cost: MaterialCost, column_id: str) -> Any:
        sort_values: dict[str, Any] = {
            "item_id": cost.item_id,
            "item_name": self.get_item_name(cost.item_id),
            "item_name_es": self.get_item_name_es(cost.item_id),
            "qty_unit": cost.count_per_unit,
            "qty_total": cost.total_count,
            "unit_price": cost.unit_price,
            "gross_cost": cost.gross_cost,
            "returned_value": cost.returned_value,
            "net_cost": cost.net_cost,
            "returnable": cost.returnable,
        }
        return sort_values.get(column_id, "")

    def get_profit_sort_value(self, profit: CityProfit, column_id: str, total_cost: float) -> Any:
        sort_values: dict[str, Any] = {
            "city": profit.city,
            "sell_price": profit.sell_price,
            "net_revenue": profit.net_revenue,
            "total_cost": total_cost,
            "profit_total": profit.profit_total,
            "profit_unit": profit.profit_per_unit,
            "margin": profit.margin_percent,
            "silver_focus": profit.silver_per_focus,
        }
        return sort_values.get(column_id, "")

    def get_material_table_values(self, cost: MaterialCost) -> tuple[str, ...]:
        return (
            cost.item_id,
            self.get_item_name(cost.item_id),
            self.get_item_name_es(cost.item_id),
            self.format_amount(cost.count_per_unit),
            self.format_amount(cost.total_count),
            self.format_silver(cost.unit_price),
            self.format_silver(cost.gross_cost),
            self.format_silver(cost.returned_value),
            self.format_silver(cost.net_cost),
            "Si" if cost.returnable else "No",
        )

    def get_profit_table_values(self, profit: CityProfit, total_cost: float) -> tuple[str, ...]:
        return (
            profit.city,
            self.format_silver(profit.sell_price),
            self.format_silver(profit.net_revenue),
            self.format_silver(total_cost),
            self.format_silver(profit.profit_total),
            self.format_silver(profit.profit_per_unit),
            f"{profit.margin_percent:.2f}%",
            self.format_silver(profit.silver_per_focus),
        )

    def set_utility_success_status(self, result: UtilityResult) -> None:
        best = max(result.city_profits, key=lambda profit: profit.profit_total, default=None)
        missing = f" | Sin precio materiales: {len(result.missing_prices)}" if result.missing_prices else ""
        best_text = ""
        if best is not None:
            best_text = f" | Mejor ciudad: {best.city} ({self.format_silver(best.profit_total)})"
        self.utility_status_text.set(
            f"Utilidad: {result.recipe.item_id} | Registros: {result.received_records} | "
            f"Costo total: {self.format_silver(result.total_cost)}{best_text}{missing}"
        )

    def get_item_name(self, item_id: str) -> str:
        return ITEM_NAMES.get(item_id, self.humanize_item_id(item_id))

    def get_item_name_es(self, item_id: str) -> str:
        return ITEM_NAMES_ES.get(item_id, "")

    def humanize_item_id(self, item_id: str) -> str:
        if not item_id:
            return ""
        return item_id.replace("_", " ").replace("@", " .").title()

    def get_quality_label(self, quality: int) -> str:
        return QUALITY_NAMES.get(quality, str(quality) if quality else "")

    def get_item_tier_label(self, item_id: str) -> str:
        tier = self.get_item_tier_number(item_id)
        if tier == 0:
            return ""
        return f"T{tier}"

    def get_item_tier_number(self, item_id: str) -> int:
        first_part = item_id.split("_", 1)[0]
        if not first_part.startswith("T"):
            return 0
        try:
            return int(first_part[1:])
        except ValueError:
            return 0

    def get_item_enchantment_label(self, item_id: str) -> str:
        enchantment = self.get_item_enchantment_number(item_id)
        if enchantment == 0:
            return ""
        return f".{enchantment}"

    def get_item_enchantment_number(self, item_id: str) -> int:
        if "@" not in item_id:
            return 0
        try:
            return int(item_id.rsplit("@", 1)[1])
        except ValueError:
            return 0

    def set_market_status(self, record_count: int | None = None, connection_status: str | None = None) -> None:
        if record_count is None:
            record_count = len(self.prices)

        if connection_status is None:
            connection_status = "OK" if self.prices else "Sin consultar"

        last_query = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_text.set(
            f"Ultima consulta: {last_query} | "
            f"Registros: {record_count} | "
            f"Conexion: {connection_status}"
        )

    def on_auto_refresh_changed(self) -> None:
        if self.auto_refresh_enabled.get():
            self.start_price_update()
            self.schedule_auto_refresh()
        else:
            self.cancel_auto_refresh()

    def schedule_auto_refresh(self) -> None:
        self.cancel_auto_refresh()

        if not self.auto_refresh_enabled.get():
            return

        seconds = AUTO_REFRESH_INTERVALS[self.interval_label.get()]
        self.auto_refresh_job = self.after(seconds * 1000, self.run_auto_refresh)

    def run_auto_refresh(self) -> None:
        self.start_price_update()
        self.schedule_auto_refresh()

    def cancel_auto_refresh(self) -> None:
        if self.auto_refresh_job is not None:
            self.after_cancel(self.auto_refresh_job)
            self.auto_refresh_job = None

    def parse_float_setting(self, value: str) -> float:
        cleaned_value = value.strip().replace(" ", "")
        if not cleaned_value:
            return 0.0

        if "," in cleaned_value and "." in cleaned_value:
            if cleaned_value.rfind(",") > cleaned_value.rfind("."):
                cleaned_value = cleaned_value.replace(".", "").replace(",", ".")
            else:
                cleaned_value = cleaned_value.replace(",", "")
        elif "," in cleaned_value:
            cleaned_value = cleaned_value.replace(".", "").replace(",", ".")
        elif "." in cleaned_value:
            dot_parts = cleaned_value.split(".")
            if len(dot_parts[-1]) == 3 and all(part.isdigit() for part in dot_parts):
                cleaned_value = "".join(dot_parts)

        return float(cleaned_value)

    def format_amount(self, value: float) -> str:
        if value == int(value):
            return format_number(int(value))
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def format_silver(self, value: float | int) -> str:
        rounded_value = int(round(value))
        if rounded_value == 0:
            return ""
        sign = "-" if rounded_value < 0 else ""
        return f"{sign}{format_number(abs(rounded_value))}"


def main() -> None:
    app = AlbionMarketApp()
    app.mainloop()


if __name__ == "__main__":
    main()
