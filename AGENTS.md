# Agent instructions

## Scope

`main` is a small Python project managed with uv. It imports a Thorlabs USD CSV,
validates it locally, and assists a human with the Oracle classic Non-Catalog
Request form. The separate extension experiment is not the architecture for
this branch. Prefer the standard library; Selenium is the only direct runtime
dependency. Do not add a backend, database, frontend framework, OCR, telemetry,
or multi-supplier abstraction without an explicit scope change.

## First steps and checks

Read `README.md` and `docs/tutorial.md`, then run from the repository root:

```sh
uv sync --locked
uv run foraclek preview examples/thorlabs-cart.csv --json
uv run python -m unittest discover -s tests -v
```

Use `uv run` for project commands. Do not install into the system Python or
replace uv with Conda/pip environment management. `uv build` verifies packaging.
If a dependency changes, use uv to regenerate `uv.lock`; do not edit it by hand.
Commit the lockfile and `.python-version`, never `.venv` or local cart data.

## File responsibilities

- `src/foraclek/parse.py`: small CartItem schema, CSV parsing, validation.
- `src/foraclek/browser.py`: visible Chrome setup, final inspection, and cleanup.
- `src/foraclek/oracle.py`: centralized selectors, origin checks, browser fill.
- `src/foraclek/cli.py`: CLI arguments, preview, and review prompts.
- `src/foraclek/__main__.py` and `parsebrowertrial.py`: thin launchers for the CLI.
- `tests/`: focused standard-library tests with fictional data and fake drivers.

Prefer small typed functions and existing files. Keep parsing separate from DOM
interaction. Use Decimal for quantities/prices and explicit procurement settings.
Preserve duplicate parts; never silently skip a nonempty malformed row. Errors
should identify the row and field without echoing sensitive imported values.

## Operating boundaries

Preview is read-only and does not open a browser, but its stdout contains cart
data. Use fictional data in development and do not paste private preview output
into external tools, logs, issues, or model context without explicit approval.
Real CSV files belong in ignored `data/` or outside the repository.

Do not start a live Oracle fill unless specifically authorized. Even with that
authorization, leave manual sign-in and each OPEN/FILL/ADD approval to the human
operator. Never pipe approval strings or add a bypass/auto-approve option. Do not
read, request, store, or automate credentials. Do not reuse a private browser
profile, capture screenshots, or send carts to third-party services.

Keep the browser visible and interruptible. Validate all input before browser
entry; require explicit URL, supplier, site, category, and UOM. Check the approved
origin and all required fields before writing. Stop on uncertain state or changed
values, and never retry Add to Cart automatically. No autonomous requisition
submission. A form reset does not prove the saved cart is correct; the human
must inspect it before continuing or resuming with `--start-row`.

## Completion

Run focused checks for changed behavior and update the README/tutorial whenever
commands or workflow change. Report what was tested and distinguish fake-driver
tests from live Oracle verification. Keep unrelated branches and user edits intact.
