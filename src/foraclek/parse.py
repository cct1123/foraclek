"""Thorlabs CSV parsing and validation; no browser or network access."""

import csv
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

HEADERS = ("Item Number", "Description", "Quantity", "Unit Price", "Line Total")
NUMBER = re.compile(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?\Z")


@dataclass(frozen=True)
class CartItem:
    row: int
    part_number: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


def _number(value: str, row: int, field: str, *, money: bool = False) -> Decimal:
    text = value.strip()
    if money:
        text = text.removeprefix("$").strip()
    if not NUMBER.fullmatch(text):
        raise ValueError(f"Row {row}, {field}: enter a finite, non-negative number.")
    number = Decimal(text.replace(",", ""))
    if field == "Quantity" and number <= 0:
        raise ValueError(f"Row {row}, {field}: must be greater than zero.")
    if money and number != number.quantize(Decimal("0.01")):
        raise ValueError(f"Row {row}, {field}: use at most two decimal places.")
    return number


def read_cart(path: str | Path) -> list[CartItem]:
    """Read every item or fail with a row/field error; preserve duplicate parts.

    Supports UTF-8 (including BOM), US decimal/grouping syntax and optional
    dollar signs. Prices are USD. Line totals must match quantity times price,
    rounded to cents using ROUND_HALF_UP. A blank line total is derived.
    """
    items = []
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        try:
            headers = [cell.strip() for cell in next(reader, [])]
            if any(headers.count(name) != 1 for name in HEADERS):
                raise ValueError("CSV headers must contain each of: " + ", ".join(HEADERS))
            previous_line = reader.line_num
            for cells in reader:
                row = previous_line + 1
                previous_line = reader.line_num
                if not any(cell.strip() for cell in cells):
                    continue
                if cells[0].strip().startswith("This CSV export") and not any(
                    cell.strip() for cell in cells[1:]
                ):
                    continue
                if len(cells) != len(headers):
                    raise ValueError(f"Row {row}: column count does not match the header.")
                values = dict(zip(headers, (cell.strip() for cell in cells)))
                for field in HEADERS[:-1]:
                    if not values[field]:
                        raise ValueError(f"Row {row}, {field}: required value is missing.")
                for field in ("Item Number", "Description"):
                    if any(
                        (ord(char) < 32 and char not in "\n\r")
                        or 127 <= ord(char) < 160 or 0xE000 <= ord(char) <= 0xF8FF
                        for char in values[field]
                    ):
                        raise ValueError(f"Row {row}, {field}: contains unsupported control or keyboard characters.")
                quantity = _number(values["Quantity"], row, "Quantity")
                price = _number(values["Unit Price"], row, "Unit Price", money=True)
                total = (quantity * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if values["Line Total"]:
                    supplied = _number(values["Line Total"], row, "Line Total", money=True)
                    if supplied != total:
                        raise ValueError(f"Row {row}, Line Total: does not match Quantity x Unit Price.")
                items.append(CartItem(row, values["Item Number"], values["Description"], quantity, price, total))
        except csv.Error:
            raise ValueError(f"Row {reader.line_num}: malformed CSV; check quoting and delimiters.") from None
        except InvalidOperation:
            raise ValueError(f"Row {reader.line_num}: a numeric value is too large or precise.") from None
    if not items:
        raise ValueError("CSV contains no cart items.")
    return items
