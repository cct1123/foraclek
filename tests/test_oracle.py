import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from decimal import Decimal
from unittest.mock import Mock, patch

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys

from foraclek.oracle import FillError, LOCATORS, OracleSettings, fill_cart, fill_item, origin
from foraclek.parse import CartItem

URL = "https://oracle.example"
SETTINGS = OracleSettings("Example supplier", "Example site", "Example category", "Each")
ITEM = CartItem(2, "DEMO", "Example", Decimal("2"), Decimal("1.50"), Decimal("3.00"))


class ImmediateWait:
    def __init__(self, driver, *args, **kwargs):
        self.driver = driver

    def until(self, predicate):
        result = predicate(self.driver)
        if not result:
            raise TimeoutException()
        return result


class FakeField:
    def __init__(self):
        self.value = ""
        self.writes = 0
        self.click = Mock()

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def clear(self):
        self.value = ""

    def send_keys(self, text):
        if text != Keys.TAB:
            self.value += text
            self.writes += 1

    def get_attribute(self, name):
        return self.value


class OracleTests(unittest.TestCase):
    def setUp(self):
        self.fields = {key: FakeField() for key in LOCATORS}
        self.driver = Mock(current_url=URL)
        self.driver.find_elements.side_effect = lambda *locator: [self.fields[key] for key in self.fields if LOCATORS[key] == locator]
        self.wait_patch = patch("foraclek.oracle.WebDriverWait", ImmediateWait)
        self.wait_patch.start()
        self.addCleanup(self.wait_patch.stop)
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def fill(self, answer="ADD"):
        with patch("builtins.input", return_value=answer):
            return fill_item(self.driver, ITEM, SETTINGS, URL)

    def test_origin_rejects_http_credentials_and_other_hosts_before_writes(self):
        for url in ["http://oracle.example", "https://user:secret@oracle.example", "not a URL"]:
            with self.assertRaises(ValueError):
                origin(url)
        self.driver.current_url = "https://unapproved.example"
        with self.assertRaisesRegex(FillError, "Row 2.*origin"):
            self.fill()
        self.assertTrue(all(field.writes == 0 for field in self.fields.values()))

    def test_missing_or_ambiguous_field_prevents_all_writes(self):
        del self.fields["supplier_site"]
        with self.assertRaisesRegex(FillError, "Row 2.*supplier_site"):
            self.fill()
        self.assertTrue(all(field.writes == 0 for field in self.fields.values()))
        self.driver.find_elements.return_value = [FakeField(), FakeField()]
        self.driver.find_elements.side_effect = None
        with self.assertRaisesRegex(FillError, "multiple visible matches"):
            self.fill()

    def test_cancel_never_clicks_add_to_cart(self):
        self.assertFalse(self.fill(""))
        self.fields["add_to_cart"].click.assert_not_called()

    def test_verified_fill_clicks_once_and_requires_reset(self):
        self.fields["add_to_cart"].click.side_effect = self.fields["description"].clear
        self.assertTrue(self.fill())
        self.fields["add_to_cart"].click.assert_called_once()
        self.assertEqual(self.fields["supplier_site"].value, SETTINGS.supplier_site)
        self.assertEqual(self.fields["uom"].value, SETTINGS.uom)

    def test_changed_value_stops_before_click(self):
        def confirm(_prompt):
            self.fields["supplier"].value = "Different supplier"
            return "ADD"
        with patch("builtins.input", side_effect=confirm):
            with self.assertRaisesRegex(FillError, "Row 2.*supplier"):
                fill_item(self.driver, ITEM, SETTINGS, URL)
        self.fields["add_to_cart"].click.assert_not_called()

    def test_controls_can_enable_after_their_required_values_are_filled(self):
        self.fields["supplier_site"].is_enabled = lambda: bool(self.fields["supplier"].value)
        button = self.fields["add_to_cart"]
        button.is_enabled = Mock(return_value=False)
        button.click.side_effect = self.fields["description"].clear

        def confirm(_prompt):
            button.is_enabled.return_value = True
            return "ADD"

        with patch("builtins.input", side_effect=confirm):
            self.assertTrue(fill_item(self.driver, ITEM, SETTINGS, URL))
        button.click.assert_called_once()

    def test_disabled_add_button_is_never_clicked(self):
        self.fields["add_to_cart"].is_enabled = Mock(return_value=False)
        with self.assertRaisesRegex(FillError, "Row 2.*add_to_cart"):
            self.fill()
        self.fields["add_to_cart"].click.assert_not_called()

    def test_windows_description_newlines_survive_browser_normalization(self):
        item = replace(ITEM, description="First line\r\nSecond line")

        def confirm(_prompt):
            description = self.fields["description"]
            description.value = description.value.replace("\r\n", "\n")
            return "ADD"

        self.fields["add_to_cart"].click.side_effect = self.fields["description"].clear
        with patch("builtins.input", side_effect=confirm):
            self.assertTrue(fill_item(self.driver, item, SETTINGS, URL))
        self.fields["add_to_cart"].click.assert_called_once()

    def test_uncertain_reset_never_retries_click(self):
        with self.assertRaisesRegex(FillError, "Row 2, form_reset.*uncertain"):
            self.fill()
        self.fields["add_to_cart"].click.assert_called_once()

    def test_equivalent_numeric_display_is_accepted(self):
        def confirm(_prompt):
            self.fields["quantity"].value = "2.00"
            self.fields["price"].value = "1.5"
            return "ADD"
        self.fields["add_to_cart"].click.side_effect = self.fields["description"].clear
        with patch("builtins.input", side_effect=confirm):
            self.assertTrue(fill_item(self.driver, ITEM, SETTINGS, URL))
        self.fields["add_to_cart"].click.assert_called_once()

    def test_failure_stops_later_rows_and_closes_browser(self):
        with patch("foraclek.browser.webdriver.Chrome", return_value=self.driver), \
                patch("foraclek.oracle.fill_item", side_effect=FillError("Row 2, quantity: failed")) as fill, \
                patch("builtins.input", return_value="FILL"), redirect_stderr(io.StringIO()):
            with self.assertRaises(FillError):
                fill_cart([ITEM, ITEM], URL, SETTINGS)
        fill.assert_called_once()
        self.driver.quit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
