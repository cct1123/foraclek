import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from foraclek.cli import main

EXAMPLE = str(Path(__file__).resolve().parents[1] / "examples" / "thorlabs-cart.csv")
FILL_ARGS = ["fill", EXAMPLE, "--url", "https://oracle.example", "--supplier", "Example",
             "--supplier-site", "Site", "--category", "Category", "--uom", "Each"]


class CliTests(unittest.TestCase):
    def test_json_preview_never_opens_browser(self):
        output = io.StringIO()
        with redirect_stdout(output), patch("selenium.webdriver.Chrome") as chrome:
            self.assertEqual(main(["preview", EXAMPLE, "--json"]), 0)
        chrome.assert_not_called()
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["currency"], "USD")
        self.assertEqual(payload["items"][0]["unit_price"], "12.50")
        self.assertEqual(len(payload["items"]), 2)

    def test_bad_path_has_nonzero_exit_and_no_json(self):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            self.assertEqual(main(["preview", EXAMPLE + ".missing", "--json"]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("could not read the CSV", error.getvalue())

    def test_fill_cannot_be_piped_or_run_without_review(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
                patch("sys.stdin.isatty", return_value=False), patch("selenium.webdriver.Chrome") as chrome:
            self.assertEqual(main(FILL_ARGS), 1)
        chrome.assert_not_called()

    def test_cancel_before_launch(self):
        with redirect_stdout(io.StringIO()), patch("sys.stdin.isatty", return_value=True), \
                patch("builtins.input", return_value=""), patch("selenium.webdriver.Chrome") as chrome:
            self.assertEqual(main(FILL_ARGS), 0)
        chrome.assert_not_called()

    def test_resume_does_not_open_browser_for_empty_suffix(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), patch("selenium.webdriver.Chrome") as chrome:
            self.assertEqual(main(FILL_ARGS + ["--start-row", "99"]), 1)
        chrome.assert_not_called()


if __name__ == "__main__":
    unittest.main()
