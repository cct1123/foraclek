# Tutorial: CSV to an Oracle cart

This walkthrough uses fictional sample data. Try preview first, then use an
approved test workflow before entering a real cart. The tool assists form entry;
you remain responsible for checking the Oracle cart and submitting requisitions.

## 1. Install and verify the environment

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/).
Install Google Chrome if you will use form fill. Open PowerShell on Windows or
a terminal on macOS/Linux:

```sh
git clone https://github.com/cct1123/foraclek.git
cd foraclek
git switch main
uv sync --locked
uv run foraclek --help
uv run python -m unittest discover -s tests -v
```

`uv` creates `.venv`, installs the locked dependencies, and can download the
Python version in `.python-version` when needed. You do not need Conda, an
activated environment, or a separate `pip install`. Keep `uv.lock` in Git; do
not edit it by hand. See the [uv project guide](https://docs.astral.sh/uv/guides/projects/).

## 2. Preview the example

```sh
uv run foraclek preview examples/thorlabs-cart.csv
```

The example contains two lines totaling $33.00 USD. Nothing is sent to Oracle.
To obtain a stable JSON shape for local assistant use:

```sh
uv run foraclek preview examples/thorlabs-cart.csv --json
```

The result is an object with `currency: "USD"` and an `items` list. Each item
contains `row`, `part_number`, `description`, `quantity`, `unit_price`, and
`line_total`. Decimal values are strings so consumers can retain exact prices.
`row` is the starting physical CSV line, including the header as line 1.
Exit status is 0 on success, 1 on validation/browser failure, 2 for incorrect
command syntax, or 130 after Ctrl+C/EOF during interaction.

## 3. Prepare your own cart

Create a local `data` directory and save your Thorlabs export as `data/cart.csv`.
This directory is ignored by Git. If starting in Excel, save as **CSV UTF-8**.
The first row must include these headers, in any order:

```csv
Item Number,Description,Quantity,Unit Price,Line Total
DEMO-001,Example optical mount,2,$12.50,$25.00
DEMO-002,"Example post, 25 mm",1,$8.00,
```

Use only USD carts with US number formatting. Quote cells containing commas,
such as `"$1,234.50"`. Quantity must be positive; zero-priced items are accepted
but should be reviewed. Money fields allow at most two decimal places.
The tool derives blank line totals using quantity × unit price, rounded to
cents with half-up rounding. Supplied totals must match. Discounts, taxes,
shipping, mixed currencies, and other adjustments need manual reconciliation.

```sh
uv run foraclek preview data/cart.csv
```

Fix every reported row and field in the source file and run preview again.
Nonempty invalid rows block the entire import. Blank rows and a standalone
`This CSV export...` footer are ignored. Duplicate part numbers are preserved.

## 4. Supply Oracle settings explicitly

Use your organization's approved URL and the exact supplier, supplier site,
category, and unit-of-measure display values. The following placeholders are
deliberately unusable; replace each before running. This single-line command
works in PowerShell and POSIX shells:

```sh
uv run foraclek fill data/cart.csv --url "https://your-approved-tenant.example" --supplier "YOUR SUPPLIER" --supplier-site "YOUR SITE" --category "YOUR CATEGORY" --uom "YOUR UOM"
```

All rows share these settings. Split the CSV if rows require different settings.
The tool does not infer procurement classifications or fill the currency field;
confirm the form uses **USD**. Do not put credentials in the URL or arguments.

The supported form uses these exact English labels, with optional `*`/`:`:

| CSV or setting | Oracle field |
| --- | --- |
| Item Number + Description | Item Description (textarea) |
| Quantity | Quantity |
| Unit Price | Price |
| `--category` | Category Name |
| `--uom` | UOM Name |
| `--supplier` | Supplier |
| `--supplier-site` | Supplier Site |
| Per-line approval | Add to Cart button or link |

Selectors are centralized in `src/foraclek/oracle.py`. They expect a label and
editable field within the same table row, in the current top-level page.
Other layouts, embedded frames, languages, or ambiguous visible matches stop
the operation and require an inspected selector update.

## 5. Review and fill one line at a time

1. Review the printed cart and settings. Type `OPEN` to launch visible Chrome.
2. Sign in manually in that Chrome window. It uses a separate temporary profile,
   so your normal Chrome sign-in is not reused. Navigate to the classic
   **Non-Catalog Request** form on the supplied Oracle origin.
3. Ensure the form is ready for a new item. Type `FILL` in the terminal for the
   displayed CSV row. The tool checks that every required control is visible
   and unique, then waits for each field to become enabled before filling it.
4. Review all populated values in Oracle, resolve any lookup suggestions, and
   verify USD currency. Type `ADD` only when this line is correct. The tool
   rechecks the values, waits for **Add to Cart** to become enabled, and clicks it once.
5. After the description field resets, check that the line appears correctly
   in the cart before approving the next `FILL`. A reset is only a UI signal;
   the tool cannot independently verify the saved cart contents.
6. Press Enter at a row approval prompt to stop. Inspect the final cart, then
   press Enter at the final prompt to close the Chrome session.

The tool never clicks Submit, Checkout, or Place Order. Ctrl+C interrupts the
run; a final inspection prompt may still appear so you can check partial
progress before closing Chrome. Closing the browser does not undo cart changes.
Review prompts are intentionally interactive; assistants must not pipe approval
strings into `fill` or treat their own inspection as human approval.

## 6. Recover from an error

If a field is missing, duplicated, rejected, or the form does not reset within
15 seconds, the operation stops. Inspect the exact row/field and the Oracle cart.
A click may have succeeded even when a subsequent wait failed. Do not rerun the
whole cart without checking for duplicates. There are no automatic click retries.

After confirming which lines were actually added, rerun the same command with
`--start-row N`, where `N` is the printed CSV row of the first item still needed.
The complete CSV is still validated before the selected suffix is processed.
Starting a new run opens a new Chrome session and requires manual sign-in again.

Common issues:

| Problem | Action |
| --- | --- |
| `uv` is not found | Finish the uv installation and open a new terminal. |
| Python/dependency download blocked | Follow your organization's package/proxy policy; do not disable TLS checks. |
| Chrome/WebDriver cannot start | Install/update approved Chrome; Selenium Manager normally manages the driver. Consult [Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/). |
| Page origin differs | Finish SSO and return to the approved Oracle origin. If the actual tenant differs, verify and use its URL explicitly. |
| Field not found or multiple matches | Verify the classic form and labels. Stop and inspect the DOM before changing selectors. |
| Oracle changed/rejected a value | Resolve the lookup and use exact display values in the next command; check the pending form and cart first. |
| Invalid CSV/encoding/total | Save UTF-8 CSV, fix the named field, and preview again. |

## For an agent assistant

Read `AGENTS.md` first. Use the fictional example, preview JSON, and unit tests
to develop without accessing Oracle.

For code changes, use `src/foraclek/parse.py` for parsing and validation,
`cli.py` for commands and preview, `browser.py` for Chrome session management,
and `oracle.py` for selectors and form entry. `parsebrowertrial.py` and
`src/foraclek/__main__.py` only launch the CLI; keep application logic in the
modules above.

A suitable local instruction is:

> Read AGENTS.md, run uv sync --locked, and validate examples/thorlabs-cart.csv
> with preview --json. Explain any blocked rows. Do not start a live fill.

For a real cart, get authorization before exposing its contents to a remote
service or assistant. Keep fixture data fictional. A human should run the final
`fill` command in their own interactive terminal and perform all approvals.
