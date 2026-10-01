"""Render DailyView offline using the production YAML example and synthetic inputs.

This adapter emulates only the Home Assistant Jinja helpers used by DailyView.
It does not contact Home Assistant, dither to the E1002 palette, or upload a frame.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import math
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined, TemplateError
from odl_renderer import generate_image

ROOT = Path(__file__).resolve().parent

def sample_input(scenario: str, at: datetime, seed: int = 0) -> dict[str, Any]:
    """Build deterministic, entirely fictitious calendar/weather/battery inputs."""
    rng = random.Random(seed)
    events: list[dict[str, Any]] = []

    def add(start: datetime, minutes: int, title: str, calendar: int = 0) -> None:
        events.append({"start": start.isoformat(), "end": (start + timedelta(minutes=minutes)).isoformat(),
                       "summary": title, "calendar": calendar})

    if scenario in ("today", "busy", "long-text"):
        add(at + timedelta(hours=2), 45, "Pick up a parcel")
    if scenario == "busy":
        add(at + timedelta(hours=5, minutes=rng.randrange(0, 45)), 90, "Sports practice", 1)
        all_day = at.date() + timedelta(days=1)
        events.append({"start": all_day.isoformat(), "end": (all_day + timedelta(days=1)).isoformat(),
                       "summary": "A day off", "calendar": 0})
        add(at + timedelta(days=1, hours=1), 60, "Dentist", 1)
        add(at + timedelta(days=2), 80, "Visit the market")
    if scenario == "long-text":
        add(at + timedelta(hours=3), 60,
            "A very long example appointment title to check truncation at the right edge", 1)
    return {"at": at.isoformat(), "events": events,
            "weather": {"condition": "partlycloudy", "temperature": 19.3}, "battery": 87}


def read_script(path: Path, key: str) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or key not in data:
        raise ValueError(f"Script key {key!r} not found in {path}")
    script = data[key]["sequence"]
    if [script[0]["action"], script[1]["action"], script[3]["action"]] != [
        "calendar.get_events", "weather.get_forecasts", "opendisplay.drawcustom"
    ]:
        raise ValueError("Expected the four-step DailyView example script")
    return {"calendars": script[0]["target"]["entity_id"],
            "weather_entity": script[1]["target"]["entity_id"],
            "duration_days": script[0]["data"]["duration"]["days"],
            "variables": script[2]["variables"], "draw": script[3]["data"]}


def parse_at(value: str) -> datetime:
    at = datetime.fromisoformat(value)
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("'at' must include a UTC offset, e.g. 2026-10-01T09:00:00+02:00")
    return at


def build_payload(script: dict[str, Any], inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Adapt a fixture to the HA response variables and evaluate the *same* YAML layout."""
    at = parse_at(inputs["at"])
    calendars = script["calendars"]
    if not isinstance(calendars, list) or len(calendars) != 2:
        raise ValueError("Offline adapter expects the example's two calendars")
    agenda: dict[str, dict[str, list[dict[str, str]]]] = {key: {"events": []} for key in calendars}
    for event in inputs.get("events", []):
        if not isinstance(event, dict) or not all(isinstance(event.get(field), str) for field in ("start", "end", "summary")):
            raise ValueError("Each event needs string start, end and summary fields")
        source = event.get("calendar", 0)
        if not isinstance(source, int) or isinstance(source, bool) or source not in (0, 1):
            raise ValueError("Event calendar must be 0 or 1")
        start, _ = _as_datetime(event["start"], at)
        finish, _ = _as_datetime(event["end"], at)
        if finish <= start:
            raise ValueError("Event end must be later than start")
        # Model the get_events response window (including ongoing events).
        if start < at + timedelta(days=script["duration_days"]) and finish > at:
            agenda[calendars[source]]["events"].append({
                "start": event["start"], "end": event["end"], "summary": event["summary"]})

    weather = inputs.get("weather")
    if weather is not None and not isinstance(weather, dict):
        raise ValueError("'weather' must be an object or null")
    forecast = [] if weather is None else [{"datetime": at.replace(hour=12, minute=0, second=0).isoformat(),
                                            "condition": weather.get("condition"),
                                            "temperature": weather.get("temperature")}]
    daily_weather = {script["weather_entity"]: {"forecast": forecast}}
    battery = inputs.get("battery")

    def is_number(value: Any) -> bool:
        try:
            return math.isfinite(float(value))
        except (ValueError, TypeError):
            return False

    def as_datetime(value: str) -> datetime:
        return _as_datetime(value, at)[0]

    env = Environment(undefined=StrictUndefined, autoescape=False)
    env.globals.update(now=lambda: at, as_datetime=as_datetime,
                       as_local=lambda dt: dt.astimezone(at.tzinfo),
                       today_at=lambda clock: datetime.combine(at.date(), time.fromisoformat(clock), at.tzinfo),
                       timedelta=timedelta, is_number=is_number,
                       states=lambda entity: str(battery) if battery is not None else "unknown")
    context = {"agenda": agenda, "daily_weather": daily_weather}
    left = []
    for element in script["variables"]["left_payload"]:
        item = element.copy()
        if isinstance(item.get("value"), str):
            item["value"] = env.from_string(item["value"]).render(**context).strip()
        left.append(item)

    def render_list(field: str) -> list[dict[str, Any]]:
        rendered = env.from_string(script["variables"][field]).render(**context).strip()
        result = ast.literal_eval(rendered)
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise ValueError(f"{field} must render to a list of draw elements")
        return result

    return left + render_list("weather_payload") + render_list("calendar_payload")


def _as_datetime(value: str, at: datetime) -> tuple[datetime, bool]:
    """Interpret an all-day YYYY-MM-DD as local midnight; keep timezone-aware times."""
    if len(value) == 10:
        return datetime.combine(date.fromisoformat(value), time.min, at.tzinfo), True
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"Timed event needs a UTC offset: {value}")
    return parsed.astimezone(at.tzinfo), False


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--scenario", choices=("empty", "today", "busy", "long-text"),
                        help="Generate synthetic inputs (default: busy)")
    source.add_argument("--input", type=Path, help="Use a JSON fixture instead of generated inputs")
    parser.add_argument("--at", help="Offset-aware ISO date/time; overrides the fixture timestamp")
    parser.add_argument("--seed", type=int, default=0, help="Deterministic random seed for synthetic data")
    parser.add_argument("--condition", help="Override daily forecast condition, e.g. rainy")
    parser.add_argument("--high", type=float, help="Override daily forecast maximum")
    parser.add_argument("--battery", help="Override percent; use 'none' to simulate unavailable")
    parser.add_argument("--script", type=Path, default=ROOT / "examples/scripts.yaml",
                        help="YAML script to evaluate (default: the portable example)")
    parser.add_argument("--script-key", default="dailyview_display", help="Top-level script key")
    parser.add_argument("--output", type=Path, default=ROOT / ".local/preview.png",
                        help="PNG destination (default: .local/preview.png)")
    parser.add_argument("--payload-json", type=Path, help="Also export the resolved ODL draw payload")
    args = parser.parse_args(argv)

    try:
        if args.input:
            inputs = json.loads(args.input.read_text(encoding="utf-8"))
            if not isinstance(inputs, dict):
                raise ValueError("Fixture must be a JSON object")
        else:
            at = parse_at(args.at) if args.at else datetime.now().astimezone()
            inputs = sample_input(args.scenario or "busy", at, args.seed)
        if args.at:
            inputs["at"] = parse_at(args.at).isoformat()
        if args.condition is not None or args.high is not None:
            inputs["weather"] = dict(inputs.get("weather") or {})
            if args.condition is not None:
                inputs["weather"]["condition"] = args.condition
            if args.high is not None:
                inputs["weather"]["temperature"] = args.high
        if args.battery is not None:
            inputs["battery"] = None if args.battery.lower() == "none" else float(args.battery)
        script = read_script(args.script, args.script_key)
        payload = build_payload(script, inputs)
        image = asyncio.run(generate_image(width=800, height=480, elements=payload,
                                           background=script["draw"]["background"]))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        image.save(args.output)
        if args.payload_json:
            args.payload_json.parent.mkdir(parents=True, exist_ok=True)
            args.payload_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
        print(f"Rendered {args.output} (800x480, {len(payload)} elements; no display upload)")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError, OSError,
            SyntaxError, TemplateError, yaml.YAMLError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
