"""Scrape category data from provider websites."""

import re

import requests

from .api import HEADERS

JLCPCB_CATEGORIES_URL = "https://jlcpcb.com/parts/all-electronic-components"


def fetch_jlcpcb_categories() -> list[dict]:
    """Scrape the JLCPCB category page and return a flat list of categories.

    Each dict has: name, parent (None for top-level), sort_id, part_count.
    """
    resp = requests.get(JLCPCB_CATEGORIES_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return _parse_jlcpcb_categories(resp.text)


def _parse_jlcpcb_categories(html: str) -> list[dict]:
    """Parse JLCPCB category page.

    The page embeds a Nuxt.js IIFE containing an ``allPartsList`` array.
    Each top-level entry has ``sortName``, ``componentCount``,
    ``componentSortKeyId``, and a ``childSortList`` array of subcategories
    with the same fields.
    """
    categories: list[dict] = []

    # Top-level entries: sortName + componentCount + childSortList (array)
    # Pattern: sortName:"Name",sortImgUrl:...,componentCount:NNN,childSortList:[...]
    top_pattern = re.compile(
        r'sortName:"([^"]+)"'
        r',sortImgUrl:\w+'
        r',componentCount:(\d+)'
        r',childSortList:\[',
    )

    # Child entries inside childSortList:
    # {sortUuid:"...",sortName:"...",sortImgUrl:X,componentCount:NNN,
    #  childSortList:X,parentId:X,componentSortKeyId:NNNN,...}
    child_pattern = re.compile(
        r'sortName:"([^"]+)"'
        r',sortImgUrl:\w+'
        r',componentCount:(\d+)'
        r',childSortList:\w+'
        r',parentId:\w+'
        r',componentSortKeyId:(\d+)',
    )

    # Walk through top-level entries
    for top_match in top_pattern.finditer(html):
        parent_name = _unescape(top_match.group(1))
        parent_count = int(top_match.group(2))

        categories.append({
            "name": parent_name,
            "parent": None,
            "sort_id": None,
            "part_count": parent_count,
        })

        # Find the matching closing bracket for childSortList
        start = top_match.end()  # right after the opening [
        bracket_depth = 1
        pos = start
        while pos < len(html) and bracket_depth > 0:
            if html[pos] == "[":
                bracket_depth += 1
            elif html[pos] == "]":
                bracket_depth -= 1
            pos += 1
        child_block = html[start:pos - 1]

        # Parse children from this block
        for child_match in child_pattern.finditer(child_block):
            child_name = _unescape(child_match.group(1))
            child_count = int(child_match.group(2))
            child_id = int(child_match.group(3))

            categories.append({
                "name": child_name,
                "parent": parent_name,
                "sort_id": child_id,
                "part_count": child_count,
            })

    return categories


def _unescape(s: str) -> str:
    """Unescape JS unicode sequences like \\u002F -> /."""
    return re.sub(
        r"\\u([0-9a-fA-F]{4})",
        lambda m: chr(int(m.group(1), 16)),
        s,
    )
