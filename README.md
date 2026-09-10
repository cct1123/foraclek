# foraclek

A small Python tool that validates a **Thorlabs USD CSV cart** and helps a human
enter it into Oracle's classic **Non-Catalog Request** form. Chrome stays visible;
each line requires review. The tool never submits a requisition or places an order.

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
git clone https://github.com/cct1123/foraclek.git
cd foraclek
uv sync --locked
uv run foraclek preview examples/thorlabs-cart.csv
```

The fictional example totals **$33.00 USD**. Preview does not load Selenium or
contact Oracle. Python 3.11+ is supported; `.python-version` selects 3.14.
`uv` creates `.venv` and runs commands without manual environment activation.

```sh
uv run foraclek preview examples/thorlabs-cart.csv --json
uv run foraclek --help
```

Read the [tutorial](docs/tutorial.md) for CSV formatting, Oracle settings, manual
sign-in, line approvals, and recovery. CSV headers are `Item Number`,
`Description`, `Quantity`, `Unit Price`, and `Line Total`. Invalid rows block
import; duplicate parts are preserved and blank line totals are calculated.
XLSX, screenshots, other currencies, and other Oracle layouts are outside scope.
Live compatibility must be checked on your organization's Oracle page.

## Modules

| File | Responsibility |
| --- | --- |
| [parse.py](src/foraclek/parse.py) | CartItem schema, CSV parsing, decimal validation |
| [browser.py](src/foraclek/browser.py) | Chrome setup, final inspection, cleanup |
| [oracle.py](src/foraclek/oracle.py) | Selectors, origin checks, assisted form filling |
| [cli.py](src/foraclek/cli.py) | Arguments, preview, review prompts |

`uv run foraclek`, `uv run python -m foraclek`, and
`uv run python parsebrowertrial.py` share the same CLI. The original script is a
thin launcher; its hardcoded settings and old Python API have been replaced.
For local integration, use `from foraclek.parse import read_cart`.

## Development

```sh
uv sync --locked
uv run python -m unittest discover -s tests -v
uv build
```

Tests use fictional data and fake browsers. Selenium is the only direct runtime
dependency. Keep changes small, use `uv add` only when necessary, and commit the
generated `uv.lock` with `pyproject.toml`. See [AGENTS.md](AGENTS.md) for assistant
instructions and [uv's project guide](https://docs.astral.sh/uv/guides/projects/).

## Privacy

Keep private carts in ignored `data/`. Preview prints their contents; do not send
that output to shared logs or remote assistants without approval. The application
keeps cart data in memory and writes it only to the explicitly supplied Oracle
origin. Sign in manually; credentials are never requested or stored by this code.

Dependency and driver setup may need internet access. Selenium Manager's
`SE_AVOID_STATS=true` opt-out is set; local Selenium configuration can override
it ([configuration reference](https://www.selenium.dev/documentation/selenium_manager/)).
Chrome uses a temporary profile and closes after your final inspection. Closing
Chrome does not undo Oracle cart entries; check for duplicates before retrying.
