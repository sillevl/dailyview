# How DailyView works

The reference implementation is [the portable script](../examples/scripts.yaml). The inspected installation keeps its production script in `/config/scripts.yaml` and its time automation in `/config/automations.yaml`; their local entity IDs and aliases are intentionally omitted here. See [setup](setup.md) to map the portable example to your installation. No code runs on the display to fetch events or weather.

## Execution sequence

1. `calendar.get_events` requests the next **three 24-hour periods** from the example's `calendar.primary` and `calendar.secondary` into the response variable `agenda`. This is rolling **72 hours from render time**, not three whole calendar days. At 17:00, for example, the window ends about 17:00 three days later.
2. `weather.get_forecasts` requests `type: daily` from the example's `weather.local` into `daily_weather`.
3. Script variables build three ordered lists of draw instructions: `left_payload`, `weather_payload`, and `calendar_payload`. `opendisplay.drawcustom` receives their concatenation as a single `payload`; later items draw over earlier ones. Home Assistant evaluates the templates when the script runs.
4. With `dry-run: false`, the integration renders an **800 × 480** frame and delivers it via BLE if possible, or queues it for a sleeping device. Its Display content image entity shows the rendered/queued frame. `dry-run: true` renders a preview without sending.
5. The time automation starts the production script at **00:00, 06:00, 11:00, 17:00** in the HA local timezone using `script.turn_on`; both script and automation use `mode: single`. An automation trigger starts generation, **not** necessarily instant physical delivery.

## Coordinates and palette

The origin is top-left; X increases rightward, Y downward. Text `anchor: mt` means middle-top, `lt` left-top, `lm` left-middle and `mm` middle-middle. The renderer accepts `font: ppb` and `font: rbm` as bundled fonts. These are **pixel sizes**.

| Region | Exact production geometry and content |
| --- | --- |
| Canvas | 800 × 480, white background, no rotation. |
| Left | Dark `#202020` rectangle X=0–369, Y=0–479. Month X=185/Y=39 at 28 px, day X=185/Y=78 at 205 px, weekday X=185/Y=248 at 42 px. Rule X=85–285/Y=300. Text is Dutch (fixed month/weekday arrays), independent of HA's language settings. |
| Weather | Today's daily forecast icon centered at X=115/Y=390, 120 px, with condition-dependent color; rounded integer forecast maximum at X=200/Y=390, 50 px. A missing/non-numeric daily forecast displays `--°` instead of an icon. |
| Right header | “Kalender” centered X=585/Y=39, 28 px, with a gold rule X=470–700/Y=84. |
| Events | Up to five rows starting at Y=`100 + index × 70`. Each row has a gold vertical line X=402, time/date at X=415/Y=top (21 px) and title at X=415/Y=top+26 (20 px). Both text fields use `max_width: 365` and truncate overly long strings. |
| Today highlight | For events overlapping local today: pastel green `#CBE3CE` rectangle X=390–785, Y=top−6…top+54, behind the row. |
| Empty agenda | Two centered lines: “Even geen plannen” at X=585/Y=250, 28 px, and “Tijd voor iets leuks!” at X=585/Y=290, 22 px. The header and footer remain. No icon or online quote service. |
| Footer | Render-time timestamp `DD/MM/YYYY HH:MM` plus battery percent at X=798/Y=478, right-bottom anchored at 14 px. `n.b.` stands in when the battery state is not numeric. The timestamp is **when Home Assistant rendered**, not the time the device woke. |

The icon comes from **today's daily forecast `condition`**, never the current `weather.*` entity state. The provider can revise the forecast during the day, so the icon may change at the next render even when the daily maximum stays the same. Mapped conditions include sunny, partly cloudy, cloudy, fog, rain, storms, snow, wind and related variants. Unmapped conditions use `mdi:weather-cloudy-alert` with a neutral color. The display converts the requested colors to its physical six-color palette.

## Calendar rules and edge cases

- The script combines both `.events` lists, sorts by the events' `start` value and takes the **first five**. Duplicate events present in both calendars are **not deduplicated**. Change both the service target and Jinja dictionary keys together if renaming calendars.
- Timed same-day events show `DD/MM  HH:MM–HH:MM`; timed events spanning dates show both dates/times. An all-day event is detected when the raw start value has exactly ten characters (`YYYY-MM-DD`); it displays only `DD/MM`. The integration supplying the calendar controls which events fall inside the requested window.
- The today highlight uses `begins < tomorrow at midnight` **and** `ends > today at midnight` in HA's local timezone. Ongoing/multi-day items can therefore be highlighted; events exactly ending at today's midnight are not. A forecast or event missing from the service response is not the same as a zero-event list: a failed service call can abort the script instead of showing the empty message.
- With no events returned in the next rolling 72 hours, the empty message appears; the weather/date/footer are still drawn. The footer is not considered an agenda item.
- Only the script invocation refreshes the rendered image. Changes to events/weather/battery between scheduled runs do **not** update the physical frame automatically.

## Rendering and power choices

Production specifies `dither: floyd_steinberg`, `refresh_type: fast`, `background: white`, `rotate: 0`, `dry-run: false`. The integration supports other algorithms and `full` refresh; these are independent settings and should be compared one at a time. `fast` may leave more ghosting than `full` on some panels. The actual dev script intentionally differs (`dither: burkes`, X=0–399 dark column, `#E7F3E8` highlight, `dry-run: true`) because it was used for layout iterations; for faithful testing **clone production and switch only `dry-run`**.

The inspected E1002 advertises about **40 seconds** awake after a no-connection wake (`sleep_timeout_ms: 40000`) and Home Assistant last reported a **120-second** deep-sleep interval. Deep sleep and update cadence are separate: the display wakes to advertise even if there is no new frame. A proposed 1800-second interval would allow up to approximately 30 minutes of additional queue delay; its actual application was not verified. Queue timeout was **24 hours**, with **three missed cycles** allowed before availability is affected. See [operations](operations.md) for delivery checks.

## Why the example is not a raw export

The actual device ID is deliberately replaced and weather/battery IDs generalized. These identifiers must be chosen in the target HA instance. Live scripts or device diagnostics may contain private metadata; never copy the entire HA configuration directory to share this project. The example reproduces production logic and positions, **not** the historically divergent dev geometry.

See the [OpenDisplay drawcustom guide](https://github.com/OpenDisplay/Home_Assistant_Integration/blob/main/docs/drawcustom/supported_types.md), [odl-renderer element reference](https://github.com/OpenDisplay/odl-renderer), and [HA forecast action](https://www.home-assistant.io/actions/weather.get_forecasts/) for behavior beyond this layout.
