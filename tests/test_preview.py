"""Offline preview contract checks; no Home Assistant or Bluetooth required."""

import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from odl_renderer import generate_image

import preview

SCRIPT = preview.read_script(preview.ROOT / "examples/scripts.yaml", "dailyview_display")
AT = preview.parse_at("2026-10-01T09:00:00+02:00")


class OfflinePreviewTests(unittest.TestCase):
    def test_empty_scenario_keeps_date_weather_and_centered_message(self):
        payload = preview.build_payload(SCRIPT, preview.sample_input("empty", AT))
        text = {e["value"]: e for e in payload if e["type"] == "text"}
        self.assertEqual(text["Even geen plannen"]["x"], 585)
        self.assertEqual(text["Even geen plannen"]["y"], 250)
        self.assertEqual(text["Tijd voor iets leuks!"]["y"], 290)
        self.assertEqual(text["DONDERDAG"]["x"], 185)
        self.assertIn("19°", text)
        self.assertIn("01/10/2026 09:00 - 87%", text)
        self.assertFalse(any(e["type"] == "rectangle" and e.get("fill") == "#CBE3CE" for e in payload))

    def test_busy_scenario_has_five_rows_and_today_highlight(self):
        payload = preview.build_payload(SCRIPT, preview.sample_input("busy", AT, seed=42))
        text = [e["value"] for e in payload if e["type"] == "text"]
        self.assertEqual(len([v for v in text if v in (
            "Pick up a parcel", "Sports practice", "A day off", "Dentist", "Visit the market")]), 5)
        self.assertNotIn("Even geen plannen", text)
        self.assertEqual(sum(e["type"] == "rectangle" and e.get("fill") == "#CBE3CE" for e in payload), 2)
        self.assertIn("02/10", text)  # The all-day item has no time.

    def test_rolling_window_drops_event_beyond_72_hours(self):
        data = preview.sample_input("empty", AT)
        later = AT + timedelta(days=3, minutes=1)
        data["events"] = [{"start": later.isoformat(), "end": (later + timedelta(hours=1)).isoformat(),
                            "summary": "Outside the window", "calendar": 1}]
        text = [e.get("value") for e in preview.build_payload(SCRIPT, data)]
        self.assertIn("Even geen plannen", text)
        self.assertNotIn("Outside the window", text)

    def test_missing_forecast_and_battery_show_placeholders(self):
        data = preview.sample_input("empty", AT)
        data["weather"] = None
        data["battery"] = None
        payload = preview.build_payload(SCRIPT, data)
        self.assertIn("--°", [e.get("value") for e in payload])
        self.assertTrue(any(e.get("value", "").endswith(" - n.b.") for e in payload))
        self.assertFalse(any(e["type"] == "icon" for e in payload))

    def test_fixture_and_generated_data_render_png_and_export_json(self):
        fixture = json.loads((preview.ROOT / "fixtures/example.json").read_text(encoding="utf-8"))
        for data in (fixture, preview.sample_input("long-text", AT)):
            payload = preview.build_payload(SCRIPT, data)
            image = asyncio.run(generate_image(width=800, height=480, elements=payload, background="white"))
            self.assertEqual(image.size, (800, 480))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preview.png"
            payload_path = Path(directory) / "payload.json"
            preview.main(["--input", str(preview.ROOT / "fixtures/example.json"),
                          "--output", str(output), "--payload-json", str(payload_path)])
            self.assertTrue(output.is_file())
            self.assertIsInstance(json.loads(payload_path.read_text(encoding="utf-8")), list)

    def test_seed_produces_repeatable_dummy_inputs(self):
        self.assertEqual(preview.sample_input("busy", AT, 42), preview.sample_input("busy", AT, 42))
        self.assertNotEqual(preview.sample_input("busy", AT, 42), preview.sample_input("busy", AT, 43))


if __name__ == "__main__":
    unittest.main()
