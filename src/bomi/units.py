"""SI prefix parsing and unit normalization for component attribute values."""

import re

SI_PREFIXES = {
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "µ": 1e-6,
    "μ": 1e-6,  # Greek mu
    "m": 1e-3,
    "k": 1e3,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
}

UNIT_ALIASES = {
    "Ω": "ohm",
    "ohm": "ohm",
    "ohms": "ohm",
    "F": "farad",
    "farad": "farad",
    "farads": "farad",
    "H": "henry",
    "henry": "henry",
    "henries": "henry",
    "V": "volt",
    "volt": "volt",
    "volts": "volt",
    "A": "ampere",
    "ampere": "ampere",
    "amperes": "ampere",
    "W": "watt",
    "watt": "watt",
    "watts": "watt",
    "%": "percent",
    "℃": "celsius",
    "°C": "celsius",
    "C": "celsius",
}

# Pattern for fraction like 1/16W
_FRACTION_RE = re.compile(
    r"^[±]?\s*(\d+)\s*/\s*(\d+)\s*([a-zA-ZΩ℃°%µμ]*)"
)

# Pattern for number with optional SI prefix and unit
# Matches: 10kΩ, 100nF, 4.7µH, 3.3V, ±1%, 2.5Ω@VGS=10V
_VALUE_RE = re.compile(
    r"^[±]?\s*(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"  # number
    r"\s*([pnuµμmkKMG])?"                          # optional SI prefix
    r"\s*([a-zA-ZΩ℃°%]*)"                          # optional unit
)


def parse_value(raw: str) -> tuple[float | None, str | None]:
    """Parse a component attribute value string into (numeric_value, unit).

    Returns (None, None) for unparseable values.

    Examples:
        "10kΩ" → (10000.0, "ohm")
        "100nF" → (1e-7, "farad")
        "1/16W" → (0.0625, "watt")
        "±1%" → (1.0, "percent")
        "2.5Ω@VGS=10V" → (2.5, "ohm")
    """
    if not raw or not isinstance(raw, str):
        return None, None

    raw = raw.strip()
    if not raw:
        return None, None

    # Strip conditional suffixes like @VGS=10V
    value_part = raw.split("@")[0].strip()

    # Try fraction pattern first
    m = _FRACTION_RE.match(value_part)
    if m:
        num, denom, unit_str = m.groups()
        try:
            value = float(num) / float(denom)
        except (ValueError, ZeroDivisionError):
            return None, None
        unit = _normalize_unit(unit_str) if unit_str else None
        return value, unit

    # Try standard number pattern
    m = _VALUE_RE.match(value_part)
    if m:
        num_str, prefix, unit_str = m.groups()
        try:
            value = float(num_str)
        except ValueError:
            return None, None
        if prefix:
            value *= SI_PREFIXES.get(prefix, 1)
        unit = _normalize_unit(unit_str) if unit_str else None
        return value, unit

    # Try plain number
    try:
        return float(value_part), None
    except ValueError:
        return None, None


def _normalize_unit(unit_str: str) -> str | None:
    """Normalize a unit string to its canonical form."""
    if not unit_str:
        return None
    # Try direct lookup
    if unit_str in UNIT_ALIASES:
        return UNIT_ALIASES[unit_str]
    # Try lowercase
    if unit_str.lower() in UNIT_ALIASES:
        return UNIT_ALIASES[unit_str.lower()]
    # Return as-is if not recognized
    return unit_str.lower() if unit_str else None


def parse_filter_expr(expr: str) -> tuple[str, str, float | str] | None:
    """Parse a filter expression like 'Resistance >= 10k' or 'Circuit = SP3T'.

    Returns (attr_name, operator, value) or None if invalid.

    Numeric values are returned as float and compared against attr_value_num.
    String values (only valid with ``=``) are returned as str and compared
    against attr_value_raw.

    Supported operators: >=, <=, >, <, =
    """
    # Match: attr_name operator value
    m = re.match(
        r"^\s*(.+?)\s*(>=|<=|!=|==|>|<|=)\s*(.+?)\s*$",
        expr,
    )
    if not m:
        return None

    attr_name, op, value_str = m.groups()
    if op == "==":
        op = "="

    num, _ = parse_value(value_str)
    if num is not None:
        return attr_name, op, num

    # Try plain number
    try:
        return attr_name, op, float(value_str)
    except ValueError:
        pass

    # String value — only valid for equality operators
    if op in ("=", "!="):
        return attr_name, op, value_str

    return None
