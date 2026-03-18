"""Normalize API responses into model objects."""

import json
from datetime import datetime, timezone

from .models import Attribute, Part, PriceTier
from .units import parse_value


def normalize_search_response(api_response: dict) -> list[Part]:
    """Convert JLCPCB search API response to list of Part objects."""
    data = api_response.get("data") or {}
    page_info = data.get("componentPageInfo") or {}
    components = page_info.get("list") or []
    return [_normalize_component(c) for c in components]


def get_search_metadata(api_response: dict) -> dict:
    """Extract pagination metadata from search response."""
    data = api_response.get("data") or {}
    page_info = data.get("componentPageInfo") or {}
    return {
        "total": page_info.get("total", 0),
        "pages": page_info.get("pages", 0),
        "has_next_page": page_info.get("hasNextPage", False),
    }


def _normalize_component(c: dict) -> Part:
    """Convert a single component dict to a Part."""
    # Build URL
    url_suffix = c.get("urlSuffix", "")
    jlcpcb_url = f"https://jlcpcb.com/partdetail/{url_suffix}" if url_suffix else None

    # Parse prices
    prices = []
    for p in c.get("componentPrices") or []:
        qty_to = p.get("endNumber")
        if qty_to == -1:
            qty_to = None
        prices.append(PriceTier(
            qty_from=p["startNumber"],
            qty_to=qty_to,
            unit_price=p["productPrice"],
        ))

    # Parse attributes
    attributes = []
    for a in c.get("attributes", []) or []:
        name = a.get("attribute_name_en", "")
        raw = a.get("attribute_value_name", "")
        num, unit = parse_value(raw)
        attributes.append(Attribute(
            name=name,
            value_raw=raw,
            value_num=num,
            unit=unit,
        ))

    return Part(
        lcsc_code=c.get("componentCode", ""),
        mfr_part=c.get("componentModelEn", ""),
        manufacturer=c.get("componentBrandEn", ""),
        package=c.get("componentSpecificationEn", ""),
        category=c.get("componentTypeEn", ""),
        subcategory=c.get("secondSortName", ""),
        description=c.get("describe", ""),
        stock=c.get("stockCount", 0),
        library_type=c.get("componentLibraryType", ""),
        preferred=bool(c.get("preferredComponentFlag", False)),
        datasheet_url=c.get("dataManualUrl"),
        jlcpcb_url=jlcpcb_url,
        fetched_at=datetime.now(timezone.utc),
        raw_json=json.dumps(c),
        prices=prices,
        attributes=attributes,
    )
