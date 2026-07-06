from __future__ import annotations

import queue
import threading
import tkinter as tk
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
    DEFAULT_PRODUCT_MODE,
    DEFAULT_LOCATION,
    ITEM_NAMES,
    ITEM_NAMES_ES,
    ITEMS,
    ENCHANTMENT_CHOICES,
    LOCATION_CHOICES,
    LOCATIONS,
    MAX_ITEMS_PER_UPDATE,
    PRODUCT_MODES,
    QUALITY_CHOICES,
    QUALITY_NAMES,
    SERVERS,
    TIER_CHOICES,
)
from data_client import start_data_client
from models import MarketPrice


COLUMNS: tuple[tuple[str, str, int, str], ...] = (
    ("item_id", "ID del producto", 150, "w"),
    ("item_name", "Nombre EN", 210, "w"),
    ("item_name_es", "Nombre ES", 210, "w"),
    ("tier", "Tier", 55, "center"),
    ("enchantment", "Encant.", 70, "center"),
    ("city", "Ciudad", 110, "w"),
    ("quality", "Calidad", 70, "center"),
    ("sell_price_min", "Precio mínimo de venta", 145, "e"),
    ("sell_price_min_quantity", "Cantidad venta mínima", 145, "e"),
    ("sell_price_min_date", "Fecha actualización venta", 180, "w"),
    ("buy_price_max", "Precio máximo de compra", 155, "e"),
    ("buy_price_max_quantity", "Cantidad compra máxima", 150, "e"),
    ("buy_price_max_date", "Fecha actualización compra", 185, "w"),
    ("age", "Antigüedad del dato", 130, "w"),
    ("status", "Estado del dato", 120, "w"),
)


class AlbionMarketApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Albion Market Test")
        self.geometry("1320x720")
        self.minsize(980, 560)

        self.result_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.prices: list[MarketPrice] = []
        self.is_fetching = False
        self.auto_refresh_job: str | None = None
        self.sort_column = "item_id"
        self.sort_reverse = False

        self.server_name = tk.StringVar(value="Americas")
        self.product_mode = tk.StringVar(value=DEFAULT_PRODUCT_MODE)
        self.location_name = tk.StringVar(value=DEFAULT_LOCATION)
        self.search_text = tk.StringVar()
        self.tier_filter = tk.StringVar(value="Todos")
        self.enchantment_filter = tk.StringVar(value="Todos")
        self.quality_filter = tk.StringVar(value="Todas")
        self.auto_refresh_enabled = tk.BooleanVar(value=False)
        self.interval_label = tk.StringVar(value="60 segundos")
        self.status_text = tk.StringVar(value="Última consulta: - | Registros: 0 | Conexión: Sin consultar")

        self._build_interface()
        self._configure_styles()
        self.search_text.trace_add("write", lambda *_: self.refresh_table())
        self.after(100, self.process_result_queue)
        self.after(500, self.start_data_client_on_launch)

    def _build_interface(self) -> None:
        main_frame = ttk.Frame(self, padding=12)
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)

        title = ttk.Label(main_frame, text="Albion Market Test", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 10))

        toolbar = ttk.Frame(main_frame)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        toolbar.columnconfigure(9, weight=1)

        ttk.Label(toolbar, text="Servidor").grid(row=0, column=0, padx=(0, 6))
        server_selector = ttk.Combobox(
            toolbar,
            textvariable=self.server_name,
            values=list(SERVERS.keys()),
            state="readonly",
            width=12,
        )
        server_selector.grid(row=0, column=1, padx=(0, 12))

        ttk.Label(toolbar, text="Ciudad").grid(row=0, column=2, padx=(0, 6))
        location_selector = ttk.Combobox(
            toolbar,
            textvariable=self.location_name,
            values=LOCATION_CHOICES,
            state="readonly",
            width=17,
        )
        location_selector.grid(row=0, column=3, padx=(0, 12))

        ttk.Label(toolbar, text="Productos").grid(row=0, column=4, padx=(0, 6))
        product_mode_selector = ttk.Combobox(
            toolbar,
            textvariable=self.product_mode,
            values=list(PRODUCT_MODES.keys()),
            state="readonly",
            width=18,
        )
        product_mode_selector.grid(row=0, column=5, padx=(0, 12))

        update_button = ttk.Button(toolbar, text="Actualizar precios", command=self.start_price_update)
        update_button.grid(row=0, column=6, padx=(0, 12))

        auto_refresh_check = ttk.Checkbutton(
            toolbar,
            text="Actualización automática",
            variable=self.auto_refresh_enabled,
            command=self.on_auto_refresh_changed,
        )
        auto_refresh_check.grid(row=0, column=7, padx=(0, 8))

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

        search_row = ttk.Frame(main_frame)
        search_row.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        search_row.columnconfigure(1, weight=1)

        ttk.Label(search_row, text="Buscar producto").grid(row=0, column=0, padx=(0, 6))
        search_entry = ttk.Entry(search_row, textvariable=self.search_text)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(search_row, text="Ej: guja, glaive, t6 guja, guja fisurante").grid(
            row=0,
            column=2,
            sticky="e",
        )

        filter_row = ttk.Frame(main_frame)
        filter_row.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        filter_row.columnconfigure(6, weight=1)

        ttk.Label(filter_row, text="Tier").grid(row=0, column=0, padx=(0, 6))
        tier_selector = ttk.Combobox(
            filter_row,
            textvariable=self.tier_filter,
            values=TIER_CHOICES,
            state="readonly",
            width=10,
        )
        tier_selector.grid(row=0, column=1, padx=(0, 12))
        tier_selector.bind("<<ComboboxSelected>>", lambda _event: self.refresh_table())

        ttk.Label(filter_row, text="Encantamiento").grid(row=0, column=2, padx=(0, 6))
        enchantment_selector = ttk.Combobox(
            filter_row,
            textvariable=self.enchantment_filter,
            values=ENCHANTMENT_CHOICES,
            state="readonly",
            width=18,
        )
        enchantment_selector.grid(row=0, column=3, padx=(0, 12))
        enchantment_selector.bind("<<ComboboxSelected>>", lambda _event: self.refresh_table())

        ttk.Label(filter_row, text="Calidad").grid(row=0, column=4, padx=(0, 6))
        quality_selector = ttk.Combobox(
            filter_row,
            textvariable=self.quality_filter,
            values=list(QUALITY_CHOICES.keys()),
            state="readonly",
            width=16,
        )
        quality_selector.grid(row=0, column=5, padx=(0, 12))
        quality_selector.bind("<<ComboboxSelected>>", lambda _event: self.refresh_table())

        table_frame = ttk.Frame(main_frame)
        table_frame.grid(row=4, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_frame,
            columns=[column_id for column_id, *_ in COLUMNS],
            show="headings",
            height=18,
        )

        for column_id, heading, width, anchor in COLUMNS:
            self.tree.heading(
                column_id,
                text=heading,
                anchor="center",
                command=lambda selected_column=column_id: self.sort_by_column(selected_column),
            )
            self.tree.column(column_id, width=width, minwidth=70, anchor=anchor, stretch=False)

        vertical_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        horizontal_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vertical_scrollbar.set, xscrollcommand=horizontal_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        footer = ttk.Label(main_frame, textvariable=self.status_text, anchor="w")
        footer.grid(row=5, column=0, sticky="ew", pady=(10, 0))

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Treeview", rowheight=26)
        self.tree.tag_configure("Reciente", background="#e9f7ef")
        self.tree.tag_configure("Precaución", background="#fff8dc")
        self.tree.tag_configure("Desactualizado", background="#fdecea")
        self.tree.tag_configure("Sin datos", background="#f2f2f2")

    def start_data_client_on_launch(self) -> None:
        if not DATA_CLIENT_AUTO_START:
            return

        message = start_data_client(DATA_CLIENT_PATHS, DATA_CLIENT_ARGS)
        self.set_status(connection_status=f"Data Client: {message}")

    def start_price_update(self) -> None:
        if self.is_fetching:
            self.set_status(connection_status="Ya hay una consulta en ejecución")
            return

        self.is_fetching = True
        requested_items = self.get_requested_items()
        requested_locations = self.get_requested_locations()
        requested_qualities = self.get_requested_qualities()

        if not requested_items:
            self.is_fetching = False
            self.set_status(connection_status="No hay productos que coincidan con la búsqueda")
            return

        if len(requested_items) > MAX_ITEMS_PER_UPDATE:
            self.is_fetching = False
            self.set_status(
                connection_status=(
                    f"La busqueda encontro {len(requested_items)} productos. "
                    "Escribe un nombre mas especifico."
                )
            )
            return

        self.set_status(
            connection_status=(
                f"Consultando {len(requested_items)} productos en "
                f"{len(requested_locations)} ciudad(es)..."
            )
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
            if self.matches_tier_filter(item_id)
            and self.matches_enchantment_filter(item_id)
        ]

    def matches_tier_filter(self, item_id: str) -> bool:
        selected_tier = self.tier_filter.get()
        if selected_tier == "Todos":
            return True
        return self.get_item_tier_label(item_id) == selected_tier

    def matches_enchantment_filter(self, item_id: str) -> bool:
        selected_enchantment = self.enchantment_filter.get()
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
            self.result_queue.put(("error", str(exc)))
        except Exception as exc:
            self.result_queue.put(("error", f"Error inesperado: {exc}"))
        else:
            self.result_queue.put(("success", prices))

    def process_result_queue(self) -> None:
        try:
            while True:
                event_type, payload = self.result_queue.get_nowait()
                self.is_fetching = False

                if event_type == "success":
                    self.prices = payload
                    self.refresh_table()
                    self.set_status(record_count=len(self.prices), connection_status="OK")
                else:
                    self.set_status(connection_status=payload)
        except queue.Empty:
            pass

        self.after(100, self.process_result_queue)

    def refresh_table(self) -> None:
        filter_terms = normalize_search_text(self.search_text.get()).split()
        visible_prices = [
            price
            for price in self.prices
            if self.matches_tier_filter(price.item_id)
            and self.matches_enchantment_filter(price.item_id)
            and self.matches_quality_filter(price.quality)
            and (
                not filter_terms
                or all(
                    term
                    in get_item_search_text(
                        price.item_id,
                        f"{self.get_item_name(price.item_id)} {self.get_item_name_es(price.item_id)}",
                    )
                    for term in filter_terms
                )
            )
        ]

        visible_prices.sort(
            key=lambda price: self.get_sort_value(price, self.sort_column),
            reverse=self.sort_reverse,
        )

        self.tree.delete(*self.tree.get_children())
        for price in visible_prices:
            status = price.status()
            self.tree.insert("", "end", values=self.get_table_values(price), tags=(status,))

    def sort_by_column(self, column_id: str) -> None:
        if self.sort_column == column_id:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column_id
            self.sort_reverse = False
        self.refresh_table()

    def get_sort_value(self, price: MarketPrice, column_id: str) -> Any:
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

    def get_item_name(self, item_id: str) -> str:
        return ITEM_NAMES.get(item_id, self.humanize_item_id(item_id))

    def get_item_name_es(self, item_id: str) -> str:
        return ITEM_NAMES_ES.get(item_id, "")

    def humanize_item_id(self, item_id: str) -> str:
        if not item_id:
            return ""
        return item_id.replace("_", " ").title()

    def get_table_values(self, price: MarketPrice) -> tuple[str, ...]:
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

    def set_status(self, record_count: int | None = None, connection_status: str | None = None) -> None:
        if record_count is None:
            record_count = len(self.prices)

        if connection_status is None:
            connection_status = "OK" if self.prices else "Sin consultar"

        last_query = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_text.set(
            f"Última consulta: {last_query} | "
            f"Registros: {record_count} | "
            f"Conexión: {connection_status}"
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


def main() -> None:
    app = AlbionMarketApp()
    app.mainloop()


if __name__ == "__main__":
    main()
