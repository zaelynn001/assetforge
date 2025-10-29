# Rev 1.2.0 - Distro

"""Minimal XLSX export helpers for AssetForge."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Dict, Iterable, List
from zipfile import ZipFile, ZIP_DEFLATED


INVENTORY_COLUMNS = [
    ("Asset Tag", "asset_tag"),
    ("Name", "name"),
    ("Model", "model"),
    ("Type", "type_name"),
    ("Extension", "extension"),
    ("Sub Type", "sub_type_name"),
    ("Location", "location_name"),
    ("User", "user_name"),
    ("Group", "group_name"),
    ("MAC Address", "mac_address"),
    ("IP Address", "ip_address"),
    ("Notes", "notes"),
    ("Updated", "updated_at_utc"),
]


def export_inventory(workbook_path: Path, *, items: List[Dict[str, str]]) -> None:
    """Write an XLSX workbook with the current inventory."""
    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    rows_inventory = _build_inventory_rows(items)
    with ZipFile(workbook_path, "w", ZIP_DEFLATED) as zf:
        _write_core_parts(zf)
        _write_inventory_sheet(zf, rows_inventory)


def _build_inventory_rows(items: Iterable[Dict[str, str]]) -> List[List[str]]:
    rows = [[header for header, _ in INVENTORY_COLUMNS]]
    for item in items:
        row = []
        for _title, key in INVENTORY_COLUMNS:
            value = item.get(key)
            row.append(_format_value(value))
        rows.append(row)
    return rows


def _write_core_parts(zf: ZipFile) -> None:
    zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
    zf.writestr("_rels/.rels", _RELS)
    zf.writestr("xl/workbook.xml", _WORKBOOK)
    zf.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
    zf.writestr("xl/styles.xml", _STYLES)


def _write_inventory_sheet(zf: ZipFile, rows: List[List[str]]) -> None:
    zf.writestr("xl/worksheets/sheet1.xml", _build_sheet_xml(rows))


def _build_sheet_xml(rows: List[List[str]]) -> str:
    xml_rows = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx, value in enumerate(row):
            cell_ref = _column_letter(c_idx + 1) + str(r_idx)
            if value == "":
                cells.append(f'<c r="{cell_ref}" />')
            else:
                cells.append(
                    f'<c r="{cell_ref}" t="inlineStr"><is><t>{_escape(value)}</t></is></c>'
                )
        xml_rows.append(f"<row r=\"{r_idx}\">{''.join(cells)}</row>")
    sheet_data = "".join(xml_rows)
    return _SHEET_TEMPLATE.format(sheet_data=sheet_data)


def _column_letter(index: int) -> str:
    letters = []
    while index:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
    )


def _format_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    return str(value)


_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_WORKBOOK = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheets>
        <sheet name="Inventory" sheetId="1" r:id="rId1"/>
    </sheets>
</workbook>"""

_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
    <fonts count="1"><font><sz val="11"/><color theme="1"/><name val="Calibri"/><family val="2"/></font></fonts>
    <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
    <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
    <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
    <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1"/></xf></cellXfs>
</styleSheet>"""

_SHEET_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
    <sheetData>{sheet_data}</sheetData>
</worksheet>"""
