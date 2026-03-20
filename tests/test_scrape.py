"""Tests for JLCPCB category page scraping."""

from bomi.scrape import _parse_jlcpcb_categories, _unescape


# Minimal HTML fragment mimicking the Nuxt.js IIFE structure
SAMPLE_HTML = (
    '<script>window.__NUXT__=(function(){return {data:[{allPartsList:['
    '{sortUuid:"aaa",sortName:"Resistors",'
    "sortImgUrl:a,componentCount:100,childSortList:["
    '{sortUuid:"bbb",sortName:"Chip Resistor - Surface Mount",'
    "sortImgUrl:a,componentCount:50,childSortList:a,"
    "parentId:x,componentSortKeyId:2980,grade:c,enDescription:b},"
    '{sortUuid:"ccc",sortName:"Through Hole Resistors",'
    "sortImgUrl:a,componentCount:30,childSortList:a,"
    "parentId:x,componentSortKeyId:2295,grade:c,enDescription:b}"
    "]},"
    '{sortUuid:"ddd",sortName:"Capacitors",'
    "sortImgUrl:a,componentCount:200,childSortList:["
    '{sortUuid:"eee",sortName:"MLCC - SMD\\u002FSMT",'
    "sortImgUrl:a,componentCount:150,childSortList:a,"
    "parentId:y,componentSortKeyId:2929,grade:c,enDescription:b}"
    "]}"
    "]}]})</script>"
)


class TestParseCategories:
    def test_parses_top_level(self):
        cats = _parse_jlcpcb_categories(SAMPLE_HTML)
        top = [c for c in cats if c["parent"] is None]
        assert len(top) == 2
        names = {c["name"] for c in top}
        assert names == {"Resistors", "Capacitors"}

    def test_parses_children(self):
        cats = _parse_jlcpcb_categories(SAMPLE_HTML)
        children = [c for c in cats if c["parent"] is not None]
        assert len(children) == 3

    def test_parent_child_relationship(self):
        cats = _parse_jlcpcb_categories(SAMPLE_HTML)
        chip = next(c for c in cats if c["name"] == "Chip Resistor - Surface Mount")
        assert chip["parent"] == "Resistors"
        assert chip["sort_id"] == 2980
        assert chip["part_count"] == 50

    def test_unescape_in_names(self):
        cats = _parse_jlcpcb_categories(SAMPLE_HTML)
        mlcc = next(c for c in cats if "MLCC" in c["name"])
        assert mlcc["name"] == "MLCC - SMD/SMT"
        assert mlcc["sort_id"] == 2929

    def test_component_counts(self):
        cats = _parse_jlcpcb_categories(SAMPLE_HTML)
        resistors = next(c for c in cats if c["name"] == "Resistors")
        assert resistors["part_count"] == 100

    def test_empty_html(self):
        cats = _parse_jlcpcb_categories("<html></html>")
        assert cats == []

    def test_total_count(self):
        cats = _parse_jlcpcb_categories(SAMPLE_HTML)
        assert len(cats) == 5


class TestUnescape:
    def test_unicode_slash(self):
        assert _unescape("A\\u002FB") == "A/B"

    def test_plain_text_unchanged(self):
        assert _unescape("hello world") == "hello world"

    def test_non_ascii_preserved(self):
        assert _unescape("Résistors") == "Résistors"

    def test_multiple_escapes(self):
        assert _unescape("A\\u002FB\\u002FC") == "A/B/C"
