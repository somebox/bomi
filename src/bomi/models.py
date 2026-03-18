"""Data models for parts, prices, and attributes."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PriceTier:
    qty_from: int
    qty_to: int | None  # None means unlimited
    unit_price: float


@dataclass
class Attribute:
    name: str
    value_raw: str
    value_num: float | None = None
    unit: str | None = None


@dataclass
class Part:
    lcsc_code: str  # e.g. "C8287"
    mfr_part: str = ""
    manufacturer: str = ""
    package: str = ""
    category: str = ""
    subcategory: str = ""
    description: str = ""
    stock: int = 0
    library_type: str = ""  # "base" or "expand"
    preferred: bool = False
    datasheet_url: str | None = None
    jlcpcb_url: str | None = None
    fetched_at: datetime | None = None
    raw_json: str | None = None
    prices: list[PriceTier] = field(default_factory=list)
    attributes: list[Attribute] = field(default_factory=list)


@dataclass
class Analysis:
    id: int | None = None
    lcsc_code: str = ""
    method: str = ""
    model: str = ""
    prompt: str = ""
    response: str = ""
    extracted_json: str | None = None
    created_at: datetime | None = None
    cost_usd: float | None = None
