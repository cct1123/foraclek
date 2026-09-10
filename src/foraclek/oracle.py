"""Visible, interactive Selenium entry for the classic non-catalog form."""

import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from foraclek.browser import chrome_session
from foraclek.parse import CartItem

LABELS = {
    "description": "Item Description",
    "category": "Category Name",
    "quantity": "Quantity",
    "uom": "UOM Name",
    "price": "Price",
    "supplier": "Supplier",
    "supplier_site": "Supplier Site",
}
# Exact labels avoid confusing Supplier with Supplier Site, for example.
LOCATORS = {
    field: (By.XPATH, f"//label[normalize-space(translate(., '*:', ''))='{label}']/ancestor::tr[1]//"
            + ("textarea" if field == "description" else "input[not(@type='hidden')]"))
    for field, label in LABELS.items()
}
LOCATORS["add_to_cart"] = (
    By.XPATH,
    "//button[normalize-space(.)='Add to Cart'] | //a[normalize-space(.)='Add to Cart']",
)


@dataclass(frozen=True)
class OracleSettings:
    supplier: str
    supplier_site: str
    category: str
    uom: str


class FillError(RuntimeError):
    """The page cannot safely be filled or its result is uncertain."""


def origin(url: str) -> tuple[str, str, int]:
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError
        return parsed.scheme, parsed.hostname, parsed.port or 443
    except ValueError:
        raise ValueError("Oracle URL must be HTTPS with a hostname and no embedded credentials.") from None


def _check_origin(driver, target_url: str) -> None:
    try:
        if origin(driver.current_url) == origin(target_url):
            return
    except ValueError:
        pass
    raise FillError("Page origin differs from the supplied Oracle URL; return to the approved Oracle page.")


def _field(driver, key: str, *, require_enabled: bool = True):
    matches = [element for element in driver.find_elements(*LOCATORS[key]) if element.is_displayed()]
    if len(matches) > 1:
        raise FillError(f"Field {key}: multiple visible matches; unsupported page layout.")
    return matches[0] if matches and (not require_enabled or matches[0].is_enabled()) else False


def _wait_field(driver, key: str, *, require_enabled: bool = True):
    try:
        return WebDriverWait(driver, 15, ignored_exceptions=[StaleElementReferenceException]).until(
            lambda page: _field(page, key, require_enabled=require_enabled)
        )
    except TimeoutException:
        raise FillError(f"Field {key}: not available within 15 seconds; check the classic non-catalog page.") from None


def _verify_values(driver, values: dict[str, str]) -> None:
    for key, value in values.items():
        actual = _wait_field(driver, key).get_attribute("value") or ""
        matches = actual.replace("\r\n", "\n").strip() == value.replace("\r\n", "\n").strip()
        if key in ("quantity", "price"):
            try:
                matches = Decimal(actual.strip()) == Decimal(value)
            except InvalidOperation:
                matches = False
        if not matches:
            raise FillError(f"Field {key}: Oracle changed or rejected the value; inspect the form before retrying.")


def fill_item(driver, item: CartItem, settings: OracleSettings, target_url: str) -> bool:
    """Fill one reviewed line; only click Add to Cart after explicit confirmation."""
    values = {
        "description": f"Part number: {item.part_number}\n{item.description}",
        "category": settings.category,
        "quantity": str(item.quantity),
        "uom": settings.uom,
        "price": f"{item.unit_price:.2f}",
        "supplier": settings.supplier,
        "supplier_site": settings.supplier_site,
    }
    key = "page"
    try:
        _check_origin(driver, target_url)
        for key in LOCATORS:
            _wait_field(driver, key, require_enabled=False)
        for key, value in values.items():
            _check_origin(driver, target_url)
            element = _wait_field(driver, key)
            element.clear()
            element.send_keys(value)
            element.send_keys(Keys.TAB)
        print(f"Row {item.row}: inspect every field, resolve Oracle suggestions, and confirm currency is USD.")
        if input("Type ADD to add this line to the cart, or press Enter to stop: ").strip() != "ADD":
            return False
        _check_origin(driver, target_url)
        _verify_values(driver, values)
        key = "add_to_cart"
        button = _wait_field(driver, key)
        _check_origin(driver, target_url)
        button.click()
        key = "form_reset"
        WebDriverWait(driver, 15, ignored_exceptions=[StaleElementReferenceException]).until(
            lambda page: (field := _field(page, "description")) and not field.get_attribute("value")
        )
        _check_origin(driver, target_url)
        return True
    except TimeoutException:
        raise FillError(f"Row {item.row}, {key}: outcome uncertain; inspect the cart before retrying to avoid duplicates.") from None
    except FillError as error:
        raise FillError(f"Row {item.row}: {error}") from None
    except WebDriverException:
        raise FillError(f"Row {item.row}, {key}: browser interaction failed; inspect the form and cart before retrying.") from None


def fill_cart(items: list[CartItem], target_url: str, settings: OracleSettings) -> None:
    origin(target_url)
    if any(not value.strip() for value in vars(settings).values()):
        raise ValueError("Supplier, supplier site, category, and UOM must be provided explicitly.")
    with chrome_session() as driver:
        try:
            driver.get(target_url)
            print("Sign in manually in Chrome and open the classic Non-Catalog Request form.")
            for item in items:
                if input(f"Type FILL to fill CSV row {item.row}, or press Enter to stop: ").strip() != "FILL":
                    break
                if not fill_item(driver, item, settings, target_url):
                    break
                print(f"Row {item.row}: Add to Cart clicked and form reset. Check the cart before continuing.")
        except FillError as error:
            print(f"Stopped: {error}", file=sys.stderr)
            raise
        except WebDriverException:
            print("Stopped: browser interaction failed. Inspect the page and cart before retrying.", file=sys.stderr)
            raise
