import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from foraclek.parse import HEADERS, read_cart


class CartTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "cart.csv"

    def write_cart(self, rows, headers=HEADERS):
        with self.path.open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(headers)
            writer.writerows(rows)

    def test_bom_quoted_commas_duplicates_and_derived_totals(self):
        self.write_cart([
            ["DEMO", "Mount, example", "2", "$1,234.50", "$2,469.00"],
            ["DEMO", "Another mount", "1.5", "$0.25", ""],
            [],
            ["This CSV export is for reference"],
        ])
        items = read_cart(self.path)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].description, "Mount, example")
        self.assertEqual(items[0].unit_price, Decimal("1234.50"))
        self.assertEqual(items[1].line_total, Decimal("0.38"))
        self.assertEqual([item.row for item in items], [2, 3])

    def test_invalid_fields_block_the_cart_without_echoing_values(self):
        cases = [
            (0, "", "Item Number"), (1, "", "Description"),
            (2, "0", "Quantity"), (2, "-1", "Quantity"),
            (2, "NaN", "Quantity"), (2, "Infinity", "Quantity"),
            (2, "1e3", "Quantity"), (3, "", "Unit Price"),
            (3, "$12,34", "Unit Price"), (3, "€1.00", "Unit Price"),
            (3, "1.001", "Unit Price"), (4, "2.00", "Line Total"),
            (1, "private\x1b[31m", "Description"),
            (1, "private\ue004", "Description"),
        ]
        for column, value, field in cases:
            with self.subTest(field=field, value=value):
                row = ["PRIVATE-PART", "Private item", "1", "$1.00", "$1.00"]
                row[column] = value
                self.write_cart([["OK", "Example", "1", "1", "1"], row])
                with self.assertRaisesRegex(ValueError, f"Row 3, {field}") as caught:
                    read_cart(self.path)
                self.assertNotIn("PRIVATE-PART", str(caught.exception))

    def test_headers_are_required_and_unique(self):
        for headers in [HEADERS[:-1], (*HEADERS, "Quantity"), ()]:
            with self.subTest(headers=headers):
                self.write_cart([], headers)
                with self.assertRaisesRegex(ValueError, "CSV headers"):
                    read_cart(self.path)

    def test_empty_truncated_and_malformed_carts_fail(self):
        for rows in [[], [["PART", "Example", "1"]], [["PART", "Example", "1", "1", "1", "extra"]]]:
            self.write_cart(rows)
            with self.assertRaises(ValueError):
                read_cart(self.path)
        self.path.write_text(",".join(HEADERS) + '\nPART,"unfinished', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "malformed CSV"):
            read_cart(self.path)

    def test_header_order_extra_columns_and_multiline_row_numbers(self):
        self.write_cart([
            ["First\nitem", "A", "1", "0", "0", "unused"],
            ["Second", "B", "2", "1", "2", "unused"],
        ], ["Description", "Item Number", "Quantity", "Unit Price", "Line Total", "Extra"])
        items = read_cart(self.path)
        self.assertEqual([item.row for item in items], [2, 4])
        self.assertEqual(items[0].unit_price, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
