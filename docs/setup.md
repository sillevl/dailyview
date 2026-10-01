# Install DailyView

## 1. Prerequisites

- A Seeed reTerminal **E1002** (7.3-inch Spectra 6, 800 × 480), battery or USB power, and a Bluetooth adapter that supports **active BLE connections**. An ESPHome Bluetooth proxy can work; a passive-only Shelly proxy cannot upload images.
- Home Assistant **2026.7.0 or later** for the [OpenDisplay custom integration](https://github.com/OpenDisplay/Home_Assistant_Integration#requirements); this installation was inspected on Home Assistant 2026.9.4. [Home Assistant's built-in integration](https://www.home-assistant.io/integrations/opendisplay/) documents `upload_image`, but the DailyView script requires the **custom integration's `opendisplay.drawcustom` action**. Use the integration providing that action; do not assume the core image-upload action is a substitute.
- Two functioning `calendar.*` entities (or edit the example to merge a different set), a `weather.*` entity that supports **daily forecasts**, and the display's battery sensor if you want battery percentage in the footer. Home Assistant's system timezone should be set to your location.
- Backups and access to Home Assistant's YAML configuration or the equivalent script/automation editors.

## 2. Install and configure OpenDisplay on the E1002

1. Follow [Seeed's OpenDisplay setup instructions](https://wiki.seeedstudio.com/EN04_opendisplay/) and open the [E1002 Toolbox preset](https://opendisplay.org/firmware/toolbox/index.html?config=reterminal-e1002) in a compatible browser. Confirm the **E1002** preset before flashing. **Flashing replaces the existing firmware**; plan a restore path first.
2. Install firmware over USB, then use Toolbox's Bluetooth configuration to apply the preset. Keep the display within range of the host/proxy. If enabling BLE encryption, record its key privately; never add it to this project.
3. Set a deep-sleep interval and BLE wake window in the device settings if using battery power. The inspected installation reported `power_mode: 1`, `deep_sleep_time_seconds: 120` and `sleep_timeout_ms: 40000` (40 seconds). An optional 1800 s deep-sleep interval trades much fewer wake-ups for up to about 30 minutes' wait for queued updates; do **not** treat 1800 s as a verified current setting. Ensure the BLE advertising window is long enough to establish a connection and deliver an image.
4. Install the [OpenDisplay Home Assistant custom integration through HACS](https://github.com/OpenDisplay/Home_Assistant_Integration#installation) (or follow its manual installation and restart instructions). Add/discover the device in **Settings → Devices & services**, provide the device's encryption key in the integration's setup flow if requested, and check that `opendisplay.drawcustom` appears under **Developer tools → Actions**. A working active Bluetooth adapter or ESPHome Bluetooth proxy is required.

## 3. Discover your own IDs and data sources

- **Device ID:** in Home Assistant, select the display in a new OpenDisplay `drawcustom` action and inspect its YAML. Replace `REPLACE_WITH_YOUR_DEVICE_ID` in the script example. Device IDs are instance-specific; never reuse someone else's.
- **Calendars:** locate your `calendar.*` entity IDs under **Developer tools → States**. Edit both `calendar.get_events.target.entity_id` and the two `agenda['calendar.…'].events` references in `calendar_payload`. If you have one calendar, remove the second target **and** remove the `+ agenda['calendar.secondary'].events` expression.
- **Weather:** choose a `weather.*` entity that supports `weather.get_forecasts` with `type: daily`. Replace the target ID **and** the dictionary key in `daily_weather['weather.local']`. The displayed temperature is the forecast's `temperature` (daily maximum where the provider supplies a high/low), **not** the current temperature.
- **Battery:** use the battery sensor created for your E1002; replace `sensor.display_battery`. If it is disabled/unavailable, the footer will show `n.b.`. Verify your weather entity's temperature unit is Celsius before retaining the hard-coded `°` symbol.
- In **Developer tools → Actions**, test `calendar.get_events` over three days and `weather.get_forecasts` with a daily forecast before loading the script. Avoid sharing the returned private event titles or device diagnostics publicly.

## 4. Add scripts and automation

1. Back up your existing `scripts.yaml` and `automations.yaml`. In [the script example](../examples/scripts.yaml), make the substitutions above. Add its single **top-level mapping entry** `dailyview_display:` to `scripts.yaml` (merge; don't replace existing scripts). If you maintain scripts in the UI, create a script with the equivalent sequence there instead. Do **not** paste the example automation into `scripts.yaml`.
2. Add the single **list item** from [the automation example](../examples/automations.yaml) to `automations.yaml` (merge; don't replace other automations). Its target is `script.dailyview_display`; change it if your generated script entity ID differs. If you use the UI editor, create a time automation with four triggers and a `script.turn_on` action instead.
3. Check configuration in **Developer tools → YAML → Check configuration** (or the supported authenticated configuration-check API). Fix errors **before** reloading. Reload **Scripts** and **Automations** under **Developer tools → YAML**, or restart Home Assistant if your installation cannot reload them. Check that `script.dailyview_display` and the automation both appear and are enabled.
4. Before sending anything to the display, **clone the production script** as `dailyview_preview` and change **only** `dry-run: false` to `dry-run: true`. Reload scripts, run the preview script once and inspect the integration's **Display content** image entity. The preview generates an image without physical delivery. Keep the preview script in dry-run mode permanently.
5. When satisfied, run `script.dailyview_display` once (explicit physical delivery) and check the display and the integration's pending-update indicator. Deep-sleeping displays may receive the queued frame only after their next wake-up. Keep the four scheduled automation triggers enabled only after verifying the result.

**Safety:** If editing a live system, review the exact diff and get approval before writing, reloading or sending a physical update. Keep snapshots and tokens outside version control. The checked-in YAML is a reusable example, **not** a remote deployment command.

## Primary references

- [Seeed: reTerminal E-series with OpenDisplay](https://wiki.seeedstudio.com/EN04_opendisplay/)
- [OpenDisplay custom integration: installation, queueing and configuration](https://github.com/OpenDisplay/Home_Assistant_Integration)
- [OpenDisplay `drawcustom` elements, fonts and service options](https://github.com/OpenDisplay/Home_Assistant_Integration/blob/main/docs/drawcustom/supported_types.md)
- [Home Assistant `calendar.get_events`](https://www.home-assistant.io/actions/calendar.get_events/)
- [Home Assistant `weather.get_forecasts`](https://www.home-assistant.io/actions/weather.get_forecasts/)
