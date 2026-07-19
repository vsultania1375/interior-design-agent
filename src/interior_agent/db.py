from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable


class CatalogRepository:
    """Read-only access to the challenge SQLite catalog."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).resolve()
        if not self.db_path.exists():
            raise FileNotFoundError(f"Catalog database not found: {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        if "in_stock" in item:
            item["in_stock"] = bool(item["in_stock"])
        for field in ("style_tags", "room_types"):
            if field in item:
                item[field] = [part.strip() for part in (item[field] or "").split(",") if part.strip()]
        return item

    def search_catalog(
        self,
        *,
        category: str,
        style: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        room_type: str | None = None,
        max_width_cm: int | None = None,
        max_depth_cm: int | None = None,
        in_stock_only: bool = True,
        include_null_price: bool = True,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        clauses = ["LOWER(category) = LOWER(?)"]
        params: list[Any] = [category.strip()]

        if style:
            clauses.append("LOWER(COALESCE(style_tags, '')) LIKE LOWER(?)")
            params.append(f"%{style.strip()}%")
        if min_price is not None:
            clauses.append("price_inr >= ?")
            params.append(int(min_price))
        if max_price is not None:
            if include_null_price:
                clauses.append("(price_inr <= ? OR price_inr IS NULL)")
            else:
                clauses.append("price_inr <= ?")
            params.append(int(max_price))
        elif not include_null_price:
            clauses.append("price_inr IS NOT NULL")
        if room_type:
            clauses.append("LOWER(COALESCE(room_types, '')) LIKE LOWER(?)")
            params.append(f"%{room_type.strip()}%")
        if max_width_cm is not None:
            clauses.append("(width_cm <= ? OR depth_cm <= ? OR width_cm IS NULL OR depth_cm IS NULL)")
            params.extend([int(max_width_cm), int(max_width_cm)])
        if max_depth_cm is not None:
            clauses.append("(depth_cm <= ? OR width_cm <= ? OR width_cm IS NULL OR depth_cm IS NULL)")
            params.extend([int(max_depth_cm), int(max_depth_cm)])
        if in_stock_only:
            clauses.append("in_stock = 1")

        sql = f"""
            SELECT *
            FROM catalog
            WHERE {' AND '.join(clauses)}
            ORDER BY
                CASE WHEN price_inr IS NULL THEN 1 ELSE 0 END,
                price_inr ASC,
                item_id ASC
            LIMIT ?
        """
        params.append(max(1, min(int(limit), 100)))

        with self._connect() as connection:
            return [self._row_to_dict(row) for row in connection.execute(sql, params)]

    def get_items(self, item_ids: Iterable[str]) -> dict[str, dict[str, Any]]:
        normalized = list(dict.fromkeys(item_id.strip() for item_id in item_ids if item_id and item_id.strip()))
        if not normalized:
            return {}
        placeholders = ",".join("?" for _ in normalized)
        sql = f"SELECT * FROM catalog WHERE item_id IN ({placeholders})"
        with self._connect() as connection:
            rows = connection.execute(sql, normalized).fetchall()
        return {row["item_id"]: self._row_to_dict(row) for row in rows}

    def all_item_ids(self) -> set[str]:
        with self._connect() as connection:
            return {row[0] for row in connection.execute("SELECT item_id FROM catalog")}

    def list_briefs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM room_briefs ORDER BY brief_id")]

    def get_brief(self, brief_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM room_briefs WHERE brief_id = ?", (brief_id,)).fetchone()
        return dict(row) if row else None

    def categories(self) -> list[str]:
        with self._connect() as connection:
            return [row[0] for row in connection.execute("SELECT DISTINCT category FROM catalog ORDER BY category")]
