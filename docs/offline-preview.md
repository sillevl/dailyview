# Offline preview and automated layout tests

`preview.py` uses **odl-renderer==0.5.12** to render the **same ODL layout templates** that appear in [`examples/scripts.yaml`](../examples/scripts.yaml). A thin local adapter supplies the limited `now`, `states`, calendar, forecast and date helpers used by those templates. You can work on layout and text **without Home Assistant, Bluetooth, credentials or an E1002**. Keep the YAML example as the layout source; the script deliberately does not copy its coordinates into Python.

## Install (Python 3.11+)

From the `dailyview/` directory:

```sh
python -m venv .venv
# Windows PowerShell:
.venv/Scripts/python.exe -m pip install -r requirements-preview.txt
# macOS/Linux instead: .venv/bin/python -m pip install -r requirements-preview.txt
```

No HA API token or device ID is needed. The installed packages are the pinned `odl-renderer==0.5.12`, Jinja2 and PyYAML. Output defaults to the ignored `.local/preview.png` inside this repository.

## Run it

```sh
# Replace PYTHON with .venv/Scripts/python.exe (Windows) or .venv/bin/python (macOS/Linux).
PYTHON=.venv/bin/python
$PYTHON preview.py --scenario empty --at 2026-10-01T09:00:00+02:00 --output .local/empty.png
$PYTHON preview.py --scenario busy --at 2026-10-01T09:00:00+02:00 --seed 42 --output .local/busy.png --payload-json .local/busy.json
$PYTHON preview.py --input fixtures/example.json --output .local/from-fixture.png
$PYTHON preview.py --scenario long-text --condition rainy --high 18.8 --battery none --output .local/long-text.png
$PYTHON -m unittest discover -s tests -v
```

In Windows PowerShell use `$python = '.venv/Scripts/python.exe'` and `& $python preview.py ...` instead of the POSIX `PYTHON=…` assignment. Run `python preview.py --help` for the complete option list.

- `--scenario empty|today|busy|long-text`: synthetic example data. The default is `busy`.
- `--at`: timezone-aware ISO timestamp. It fixes both the on-screen date/time and the **rolling 72-hour** window. Omit it to use your computer's current local clock; specify it for deterministic tests.
- `--seed`: makes dummy appointment variations reproducible; only affects generated scenarios.
- `--input PATH`: read a JSON fixture **instead** of generating events. `--at` may override its timestamp; weather and battery override flags work with either source.
- `--condition`, `--high`, `--battery`: override simulated daily condition, maximum temperature and battery percentage. `--battery none` exercises the `n.b.` fallback.
- `--script PATH`, `--script-key KEY`: choose another trusted copy of a DailyView-shaped, four-action YAML script. This is **not** a general-purpose Home Assistant script interpreter.
- `--output PATH`: output PNG; `--payload-json PATH`: optionally save the resolved list of ODL draw elements for snapshots, assertions or other tooling. A failed invocation returns a nonzero exit code.

## Explicit input format

[`fixtures/example.json`](../fixtures/example.json) is an entirely fictitious example. Keys:

| Key | Type | Meaning |
| --- | --- | --- |
| `at` | ISO date/time string **with UTC offset** | Clock for the frame, local date matching and 72-hour filter. |
| `events` | list | Event objects containing `start`, `end`, `summary`; optionally `calendar: 0` or `1` (first or second calendar). Timed timestamps require an offset; all-day dates use `YYYY-MM-DD` and an exclusive `end` date. |
| `weather` | object or `null` | Today's `condition` and numeric `temperature` (daily forecast maximum). `null` simulates missing forecast and shows `--°`. |
| `battery` | number or `null` | Displayed percentage, or `n.b.` if `null`. |

The adapter puts these values into HA-shaped `agenda` and `daily_weather` response dictionaries. It filters events that overlap the 72-hour window, then the template sorts and displays at most five. The JSON format contains **no entity or device IDs**; the adapter reads the placeholder IDs from the YAML example. This is the seam between changing input data and the layout implementation.

## What the local test does *not* prove

- `odl-renderer` returns a full-color RGB image. Home Assistant's OpenDisplay integration performs its own **Floyd–Steinberg dithering and panel color conversion**, so the PNG is not an exact E1002 photograph. It also cannot test BLE upload, deep-sleep queueing, battery life or HA automation timing.
- Only the HA template helpers used by this particular YAML are emulated. HA's calendar provider decides precisely which events `calendar.get_events` returns, including ongoing/all-day cases; local overlap filtering is an approximation. Use a real **Home Assistant dry-run script** before changing production.
- The template is evaluated locally from **trusted YAML**; don't run arbitrary untrusted scripts through this Jinja adapter. Custom JSON fixtures may contain personal event titles; keep such fixtures in ignored `.local/`, not `fixtures/` or Git.

See [setup](setup.md) for real HA installation and [operations](operations.md) for the live dry-run workflow.
