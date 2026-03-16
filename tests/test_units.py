"""Tests for SI prefix parsing and unit normalization."""

import pytest

from jlcpcb_tool.units import parse_filter_expr, parse_value


class TestParseValue:
    """Test parse_value with various input formats."""

    def test_si_prefix_kilo_ohm(self):
        val, unit = parse_value("10kΩ")
        assert val == 10000.0
        assert unit == "ohm"

    def test_si_prefix_nano_farad(self):
        val, unit = parse_value("100nF")
        assert val == pytest.approx(1e-7)
        assert unit == "farad"

    def test_si_prefix_micro_henry(self):
        val, unit = parse_value("4.7µH")
        assert val == pytest.approx(4.7e-6)
        assert unit == "henry"

    def test_si_prefix_milli_ampere(self):
        val, unit = parse_value("500mA")
        assert val == pytest.approx(0.5)
        assert unit == "ampere"

    def test_si_prefix_pico_farad(self):
        val, unit = parse_value("100pF")
        assert val == pytest.approx(1e-10)
        assert unit == "farad"

    def test_plain_voltage(self):
        val, unit = parse_value("3.3V")
        assert val == pytest.approx(3.3)
        assert unit == "volt"

    def test_fraction_watt(self):
        val, unit = parse_value("1/16W")
        assert val == pytest.approx(0.0625)
        assert unit == "watt"

    def test_fraction_quarter_watt(self):
        val, unit = parse_value("1/4W")
        assert val == pytest.approx(0.25)
        assert unit == "watt"

    def test_tolerance_percent(self):
        val, unit = parse_value("±1%")
        assert val == pytest.approx(1.0)
        assert unit == "percent"

    def test_tolerance_with_spaces(self):
        val, unit = parse_value("± 5 %")
        assert val == pytest.approx(5.0)
        assert unit == "percent"

    def test_conditional_value(self):
        val, unit = parse_value("2.5Ω@VGS=10V")
        assert val == pytest.approx(2.5)
        assert unit == "ohm"

    def test_plain_number(self):
        val, unit = parse_value("42")
        assert val == pytest.approx(42.0)
        assert unit is None

    def test_plain_float(self):
        val, unit = parse_value("3.14")
        assert val == pytest.approx(3.14)
        assert unit is None

    def test_mega_ohm(self):
        val, unit = parse_value("1MΩ")
        assert val == pytest.approx(1e6)
        assert unit == "ohm"

    def test_giga_hertz(self):
        # Hz not in aliases, but still parses
        val, unit = parse_value("2.4G")
        assert val == pytest.approx(2.4e9)
        assert unit is None

    def test_uppercase_k(self):
        val, unit = parse_value("10KΩ")
        assert val == pytest.approx(10000.0)
        assert unit == "ohm"

    def test_greek_mu(self):
        val, unit = parse_value("4.7μF")
        assert val == pytest.approx(4.7e-6)
        assert unit == "farad"

    def test_empty_string(self):
        val, unit = parse_value("")
        assert val is None
        assert unit is None

    def test_none_input(self):
        val, unit = parse_value(None)
        assert val is None
        assert unit is None

    def test_garbage_input(self):
        val, unit = parse_value("not a value")
        assert val is None
        assert unit is None

    def test_scientific_notation(self):
        val, unit = parse_value("1e3")
        assert val == pytest.approx(1000.0)

    def test_whitespace_only(self):
        val, unit = parse_value("   ")
        assert val is None
        assert unit is None


class TestParseFilterExpr:
    """Test filter expression parsing."""

    def test_gte_with_si_prefix(self):
        result = parse_filter_expr("Resistance >= 10k")
        assert result == ("Resistance", ">=", 10000.0)

    def test_lte_plain_number(self):
        result = parse_filter_expr("Power(Watts) <= 0.25")
        assert result == ("Power(Watts)", "<=", 0.25)

    def test_gt(self):
        result = parse_filter_expr("Voltage Rated > 16")
        assert result == ("Voltage Rated", ">", 16.0)

    def test_eq_double_equals(self):
        result = parse_filter_expr("Resistance == 10k")
        assert result == ("Resistance", "=", 10000.0)

    def test_neq(self):
        result = parse_filter_expr("Tolerance != 5")
        assert result == ("Tolerance", "!=", 5.0)

    def test_invalid_no_operator(self):
        result = parse_filter_expr("Resistance 10k")
        assert result is None

    def test_invalid_no_value(self):
        result = parse_filter_expr("Resistance >=")
        assert result is None

    def test_with_spaces(self):
        result = parse_filter_expr("  Forward Current  >=  100mA  ")
        assert result is not None
        name, op, val = result
        assert name == "Forward Current"
        assert op == ">="
        assert val == pytest.approx(0.1)
