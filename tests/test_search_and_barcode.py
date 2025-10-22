# Rev 1.0.0

from __future__ import annotations

from src.services.search_service import parse_query
from src.ui.utils import barcode_input


def test_parse_query_with_directives() -> None:
    text, filters = parse_query("laptop type:lt loc:HQ mac:aa:bb")
    assert text == "laptop"
    assert filters["type"] == "lt"
    assert filters["loc"] == "HQ"
    assert filters["mac"] == "aa:bb"


def test_barcode_analyze_asset_tag() -> None:
    result = barcode_input.analyze("sdmm-lt-0005")
    assert result == {"asset_tag": "SDMM-LT-0005"}


def test_barcode_analyze_mac() -> None:
    result = barcode_input.analyze("aa:bb:cc:dd:ee:ff")
    assert result == {"mac_address": "AABBCCDDEEFF"}
