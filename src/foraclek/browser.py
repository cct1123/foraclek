"""Visible Chrome session setup and cleanup, independent of Oracle fields."""

import os
from collections.abc import Iterator
from contextlib import contextmanager

from selenium import webdriver
from selenium.common.exceptions import WebDriverException


@contextmanager
def chrome_session() -> Iterator[webdriver.Chrome]:
    """Keep Chrome available for final inspection, then close it even on failure."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    os.environ["SE_AVOID_STATS"] = "true"
    driver = webdriver.Chrome(options=options)
    try:
        yield driver
    finally:
        try:
            input("Inspect the browser and cart. Press Enter when ready to close this Chrome session: ")
        finally:
            try:
                driver.quit()
            except WebDriverException:
                pass  # The user may already have closed the browser.
