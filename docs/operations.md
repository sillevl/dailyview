# Operating and troubleshooting DailyView

## Normal use

- Edit events in the calendar provider(s) already connected to Home Assistant. DailyView reads their `calendar.*` entities; it does not create events. Both calendars are merged automatically.
- Check that the weather integration provides `weather.get_forecasts` with `type: daily`. The daily maximum and condition may change when the provider revises its forecast.
- The HA automation renders at **00:00, 06:00, 11:00 and 17:00 local time**. To change the schedule, edit the four time values in the automation, validate and reload automations. To change the 72-hour lookahead, edit `duration.days` in the script; to change the maximum visible events, edit `[:5]` in `calendar_payload`. These are different limits.
- A rendered image remains visible during deep sleep without continually refreshing the panel. A queued render is not necessarily delivered immediately; `refresh_type: fast` does not shorten the deep-sleep wait.

## Safe change and preview cycle

1. Back up the relevant script/automation configuration and review the exact proposed diff. On a live installation obtain approval before saving, reloading or sending a physical update.
2. Make layout/logic edits in a preview copy of the script with `dry-run: true`. Use the same layout and dithering as production if you need pixel-accurate comparisons. Never switch the preview copy to `false` just to test.
3. Validate Home Assistant configuration; reload scripts only after a successful check. Run the preview script from **Developer tools → Actions** (`script.dailyview_preview`, if following the setup guide) and open the device's **Display content** image entity. Preview output is generated but not uploaded.
4. To preview the zero-event case without changing real calendars, temporarily change **only the preview script's** `set events = …` expression to `set events = []`, validate/reload/run the dry-run, then restore the original expression and validate/reload again. Do not leave this simulation in production or in the regular preview script.
5. After visual approval, port the tested change to production, validate, reload and, only when desired, run `script.dailyview_display` once to request physical delivery. The automation can also deliver it at its next scheduled time. Confirm the pending-update state and physical display separately.

The preview image and physical display can differ: a dry-run renders with the preview script's own settings, and E1002 color dithering is imperfect. Older standalone preview tools may render a different design; only the dry-run clone of the current production script is a reliable reference for this layout.

## Delivery and diagnostics

- The custom integration provides an image entity for rendered/queued display content, a last-seen sensor and an **update pending** binary sensor. Entity IDs depend on your device name; find them under **Developer tools → States**. For example, yours might be `image.display_content`, `sensor.display_last_seen`, and `binary_sensor.display_update_pending`; these are placeholders, not IDs from the inspected installation.
- `update_pending: on` means Home Assistant still has a frame to deliver. It can be normal while the device sleeps; check its `queued_at`, `attempts` and `last_error` attributes. `off` after a wake and a newer `last_seen` are evidence of delivery, but still verify the physical image if it matters. A completed script action **alone** proves only that rendering/requesting succeeded.
- The integration settings include **Sleep mode** (Automatic follows device settings), **Missed cycles**, **Queue timeout**, and **Probe before queueing**. The inspected installation reported a 24-hour timeout, three missed cycles and a 40-second BLE window; these may differ elsewhere. A pending image can expire if the device never wakes before the configured timeout. [Integration documentation](https://github.com/OpenDisplay/Home_Assistant_Integration#configuration).
- If it remains queued past an expected wake, verify display power, wake configuration and active Bluetooth range/proxy. If `last_error` records a connection failure, do not treat it as successful delivery. Avoid repeatedly invoking production while an earlier frame is pending: a newer image can replace a queued earlier one.
- If battery shows `n.b.`, check that the battery sensor exists, is enabled and has a numeric state. If the icon is missing or the weather shows `--°`, verify that **today's** daily forecast exists and supplies a numeric `temperature`; the script does not substitute the current condition.
- If nothing appears in the agenda, inspect the responses from both `calendar.get_events` targets for the next three days. No returned events legitimately produces the friendly empty message. Service failures, wrong entity IDs and calendar-provider sync problems need to be fixed rather than hidden by the fallback.
- For a malformed `drawcustom` payload, check YAML syntax and the rendered Jinja. In text element mappings, keep **`'y'` quoted**; a previous YAML conversion interpreted a bare `y` as a boolean-like key. Quote every hex color (`'#CBE3CE'`), because an unquoted `#` begins a YAML comment. The fonts `ppb` and `rbm` are bundled; no external font download is required.

## Battery and deep sleep

Deep sleep saves power by reducing wake frequency, but there is **no measured battery-life curve** for this exact E1002 + OpenDisplay configuration. With a 40-second advertising window and no connection, a simplified awake fraction is `40 / (sleep_seconds + 40)`: roughly 25% for 120 s, 6% for 600 s and 2% for 1800 s. These are **time fractions, not predicted battery-life multipliers**; booting, BLE delivery, panel refresh and standby draw are omitted. A longer interval means longer potential delivery latency. Measure battery drain over several unplugged weeks with a stable workload before drawing conclusions. The battery sensor may stay at 100% for a while, and recorder history may be absent.

Do not change firmware, deep sleep, BLE proxy tuning or device controls as a side effect of a documentation or layout edit.
