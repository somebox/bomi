"""SQLite database schema and CRUD operations."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Analysis, Attribute, Part, PriceTier

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS parts (
    lcsc_code TEXT PRIMARY KEY,
    mfr_part TEXT,
    manufacturer TEXT,
    package TEXT,
    category TEXT,
    subcategory TEXT,
    description TEXT,
    stock INTEGER DEFAULT 0,
    library_type TEXT,
    preferred INTEGER DEFAULT 0,
    datasheet_url TEXT,
    jlcpcb_url TEXT,
    fetched_at TEXT,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS prices (
    lcsc_code TEXT NOT NULL,
    qty_from INTEGER NOT NULL,
    qty_to INTEGER,
    unit_price REAL NOT NULL,
    PRIMARY KEY (lcsc_code, qty_from),
    FOREIGN KEY (lcsc_code) REFERENCES parts(lcsc_code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attributes (
    lcsc_code TEXT NOT NULL,
    attr_name TEXT NOT NULL,
    attr_value_raw TEXT,
    attr_value_num REAL,
    attr_unit TEXT,
    PRIMARY KEY (lcsc_code, attr_name),
    FOREIGN KEY (lcsc_code) REFERENCES parts(lcsc_code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lcsc_code TEXT NOT NULL,
    method TEXT NOT NULL,
    model TEXT,
    prompt TEXT,
    response TEXT,
    extracted_json TEXT,
    created_at TEXT,
    cost_usd REAL,
    FOREIGN KEY (lcsc_code) REFERENCES parts(lcsc_code) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_parts_category ON parts(category);
CREATE INDEX IF NOT EXISTS idx_parts_package ON parts(package);
CREATE INDEX IF NOT EXISTS idx_parts_stock ON parts(stock);
CREATE INDEX IF NOT EXISTS idx_attr_name_num ON attributes(attr_name, attr_value_num);
"""


class Database:
    """SQLite database wrapper for parts storage."""

    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def upsert_part(self, part: Part):
        """Insert or update a part and its prices/attributes."""
        now = part.fetched_at or datetime.now(timezone.utc)
        self.conn.execute(
            """INSERT INTO parts (lcsc_code, mfr_part, manufacturer, package,
               category, subcategory, description, stock, library_type,
               preferred, datasheet_url, jlcpcb_url, fetched_at, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(lcsc_code) DO UPDATE SET
               mfr_part=excluded.mfr_part, manufacturer=excluded.manufacturer,
               package=excluded.package, category=excluded.category,
               subcategory=excluded.subcategory, description=excluded.description,
               stock=excluded.stock, library_type=excluded.library_type,
               preferred=excluded.preferred, datasheet_url=excluded.datasheet_url,
               jlcpcb_url=excluded.jlcpcb_url, fetched_at=excluded.fetched_at,
               raw_json=excluded.raw_json""",
            (
                part.lcsc_code, part.mfr_part, part.manufacturer, part.package,
                part.category, part.subcategory, part.description, part.stock,
                part.library_type, int(part.preferred), part.datasheet_url,
                part.jlcpcb_url, now.isoformat(), part.raw_json,
            ),
        )

        # Replace prices
        self.conn.execute(
            "DELETE FROM prices WHERE lcsc_code = ?", (part.lcsc_code,)
        )
        for p in part.prices:
            self.conn.execute(
                "INSERT INTO prices (lcsc_code, qty_from, qty_to, unit_price) "
                "VALUES (?, ?, ?, ?)",
                (part.lcsc_code, p.qty_from, p.qty_to, p.unit_price),
            )

        # Replace attributes
        self.conn.execute(
            "DELETE FROM attributes WHERE lcsc_code = ?", (part.lcsc_code,)
        )
        for a in part.attributes:
            self.conn.execute(
                "INSERT INTO attributes (lcsc_code, attr_name, attr_value_raw, "
                "attr_value_num, attr_unit) VALUES (?, ?, ?, ?, ?)",
                (part.lcsc_code, a.name, a.value_raw, a.value_num, a.unit),
            )

        self.conn.commit()

    def get_part(self, lcsc_code: str) -> Part | None:
        """Fetch a part with its prices and attributes."""
        row = self.conn.execute(
            "SELECT * FROM parts WHERE lcsc_code = ?", (lcsc_code,)
        ).fetchone()
        if not row:
            return None

        prices = [
            PriceTier(
                qty_from=r["qty_from"],
                qty_to=r["qty_to"],
                unit_price=r["unit_price"],
            )
            for r in self.conn.execute(
                "SELECT * FROM prices WHERE lcsc_code = ? ORDER BY qty_from",
                (lcsc_code,),
            )
        ]

        attributes = [
            Attribute(
                name=r["attr_name"],
                value_raw=r["attr_value_raw"],
                value_num=r["attr_value_num"],
                unit=r["attr_unit"],
            )
            for r in self.conn.execute(
                "SELECT * FROM attributes WHERE lcsc_code = ? ORDER BY attr_name",
                (lcsc_code,),
            )
        ]

        fetched_at = None
        if row["fetched_at"]:
            try:
                fetched_at = datetime.fromisoformat(row["fetched_at"])
            except ValueError:
                pass

        return Part(
            lcsc_code=row["lcsc_code"],
            mfr_part=row["mfr_part"] or "",
            manufacturer=row["manufacturer"] or "",
            package=row["package"] or "",
            category=row["category"] or "",
            subcategory=row["subcategory"] or "",
            description=row["description"] or "",
            stock=row["stock"] or 0,
            library_type=row["library_type"] or "",
            preferred=bool(row["preferred"]),
            datasheet_url=row["datasheet_url"],
            jlcpcb_url=row["jlcpcb_url"],
            fetched_at=fetched_at,
            raw_json=row["raw_json"],
            prices=prices,
            attributes=attributes,
        )

    def get_part_age_hours(self, lcsc_code: str) -> float | None:
        """Return hours since part was last fetched, or None if not cached."""
        row = self.conn.execute(
            "SELECT fetched_at FROM parts WHERE lcsc_code = ?", (lcsc_code,)
        ).fetchone()
        if not row or not row["fetched_at"]:
            return None
        try:
            fetched = datetime.fromisoformat(row["fetched_at"])
            if fetched.tzinfo is None:
                fetched = fetched.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - fetched
            return delta.total_seconds() / 3600
        except ValueError:
            return None

    def delete_part(self, lcsc_code: str):
        """Delete a part and its related data."""
        self.conn.execute("DELETE FROM parts WHERE lcsc_code = ?", (lcsc_code,))
        self.conn.commit()

    def save_analysis(self, analysis: Analysis) -> int:
        """Save an analysis result, return its ID."""
        now = analysis.created_at or datetime.now(timezone.utc)
        cursor = self.conn.execute(
            """INSERT INTO analyses (lcsc_code, method, model, prompt, response,
               extracted_json, created_at, cost_usd)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                analysis.lcsc_code, analysis.method, analysis.model,
                analysis.prompt, analysis.response, analysis.extracted_json,
                now.isoformat(), analysis.cost_usd,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_analyses(self, lcsc_code: str) -> list[Analysis]:
        """Get all analyses for a part."""
        rows = self.conn.execute(
            "SELECT * FROM analyses WHERE lcsc_code = ? ORDER BY created_at DESC",
            (lcsc_code,),
        ).fetchall()
        return [
            Analysis(
                id=r["id"],
                lcsc_code=r["lcsc_code"],
                method=r["method"],
                model=r["model"] or "",
                prompt=r["prompt"] or "",
                response=r["response"] or "",
                extracted_json=r["extracted_json"],
                created_at=(
                    datetime.fromisoformat(r["created_at"])
                    if r["created_at"] else None
                ),
                cost_usd=r["cost_usd"],
            )
            for r in rows
        ]

    def stats(self) -> dict:
        """Return database statistics."""
        parts = self.conn.execute("SELECT COUNT(*) FROM parts").fetchone()[0]
        attrs = self.conn.execute("SELECT COUNT(*) FROM attributes").fetchone()[0]
        analyses = self.conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        categories = self.conn.execute(
            "SELECT COUNT(DISTINCT category) FROM parts"
        ).fetchone()[0]
        return {
            "parts": parts,
            "attributes": attrs,
            "analyses": analyses,
            "categories": categories,
        }

    def clear(self):
        """Delete all data."""
        self.conn.execute("DELETE FROM analyses")
        self.conn.execute("DELETE FROM attributes")
        self.conn.execute("DELETE FROM prices")
        self.conn.execute("DELETE FROM parts")
        self.conn.commit()

    def query_parts(
        self,
        keyword: str | None = None,
        package: str | None = None,
        min_stock: int | None = None,
        basic_only: bool = False,
        preferred_only: bool = False,
        max_price: float | None = None,
        attr_filters: list[tuple[str, str, float]] | None = None,
        limit: int = 50,
    ) -> list[Part]:
        """Query parts from local DB with filters.

        attr_filters: list of (attr_name, operator, value) tuples
        """
        conditions = []
        params: list = []

        if keyword:
            conditions.append(
                "(p.description LIKE ? OR p.mfr_part LIKE ? OR p.lcsc_code LIKE ?)"
            )
            like = f"%{keyword}%"
            params.extend([like, like, like])

        if package:
            conditions.append("p.package LIKE ?")
            params.append(f"%{package}%")

        if min_stock is not None:
            conditions.append("p.stock >= ?")
            params.append(min_stock)

        if basic_only:
            conditions.append("p.library_type = 'base'")

        if preferred_only:
            conditions.append("p.preferred = 1")

        if max_price is not None:
            conditions.append(
                "EXISTS (SELECT 1 FROM prices pr WHERE pr.lcsc_code = p.lcsc_code "
                "AND pr.qty_from = (SELECT MIN(qty_from) FROM prices WHERE lcsc_code = p.lcsc_code) "
                "AND pr.unit_price <= ?)"
            )
            params.append(max_price)

        if attr_filters:
            for attr_name, op, value in attr_filters:
                sql_op = op if op != "=" else "="
                conditions.append(
                    f"EXISTS (SELECT 1 FROM attributes a "
                    f"WHERE a.lcsc_code = p.lcsc_code "
                    f"AND a.attr_name = ? AND a.attr_value_num {sql_op} ?)"
                )
                params.extend([attr_name, value])

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT lcsc_code FROM parts p WHERE {where} ORDER BY p.stock DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(sql, params).fetchall()
        return [self.get_part(r["lcsc_code"]) for r in rows]
