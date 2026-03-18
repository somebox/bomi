"""Reference designator parsing and overlap helpers."""

from dataclasses import dataclass
import re

_SINGLE_RE = re.compile(r"^\s*([A-Za-z]+)\s*(\d+)\s*$")
_RANGE_RE = re.compile(r"^\s*([A-Za-z]+)\s*(\d+)\s*-\s*([A-Za-z]+)\s*(\d+)\s*$")


@dataclass(frozen=True)
class RefSpec:
    """Canonical representation of a reference designator or range."""

    prefix: str
    start: int
    end: int

    @property
    def is_range(self) -> bool:
        return self.start != self.end

    @property
    def count(self) -> int:
        return self.end - self.start + 1

    def canonical(self) -> str:
        if self.is_range:
            return f"{self.prefix}{self.start}-{self.prefix}{self.end}"
        return f"{self.prefix}{self.start}"

    def overlaps(self, other: "RefSpec") -> bool:
        if self.prefix != other.prefix:
            return False
        return not (self.end < other.start or other.end < self.start)


def parse_ref(ref: str) -> RefSpec:
    """Parse and validate a reference designator."""
    m = _SINGLE_RE.match(ref)
    if m:
        prefix, start = m.groups()
        return RefSpec(prefix=prefix.upper(), start=int(start), end=int(start))

    m = _RANGE_RE.match(ref)
    if not m:
        raise ValueError(f"Invalid reference designator: {ref}")

    p1, s1, p2, s2 = m.groups()
    if p1.upper() != p2.upper():
        raise ValueError(f"Range must use one prefix: {ref}")

    start = int(s1)
    end = int(s2)
    if end < start:
        raise ValueError(f"Range end must be >= start: {ref}")

    return RefSpec(prefix=p1.upper(), start=start, end=end)


def normalize_ref(ref: str) -> str:
    """Return canonical ref string."""
    return parse_ref(ref).canonical()


def ref_count(ref: str) -> int:
    """Return number of members covered by a ref or range."""
    return parse_ref(ref).count


def refs_overlap(a: str, b: str) -> bool:
    """Return True if two refs/ranges overlap."""
    return parse_ref(a).overlaps(parse_ref(b))


def ref_sort_key(ref: str) -> tuple:
    """Sort refs by prefix, then numeric span."""
    parsed = parse_ref(ref)
    return (parsed.prefix, parsed.start, parsed.end)
