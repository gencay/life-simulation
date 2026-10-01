import base64
import math
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from evolution_ticker import render_ticker

NS = {"svg": "http://www.w3.org/2000/svg"}


class TickerTests(unittest.TestCase):
    def render(self, count, active):
        history = [
            {
                "generation": index + 1, "updated_at": "2026-10-01T00:17:00+00:00",
                "active_cells": active(index), "total_cells": 4096,
                "mean_v": 0.1, "standard_deviation_v": 0.05,
            }
            for index in range(count)
        ]
        frames = [
            {**row, "width": 2, "height": 2, "pixels": [0, 80, 160, 255]}
            for row in history[-48:]
        ]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "evolution.svg"
            render_ticker(history, frames, None, destination)
            return ET.parse(destination).getroot()

    def test_full_history_remains_when_replay_window_rolls(self):
        root = self.render(60, lambda index: index * 10)
        trend = root.find(".//svg:polyline[@id='activity-trend']", NS)
        self.assertEqual(len(trend.attrib["points"].split()), 60)
        text = "".join(root.itertext())
        self.assertIn("60 OBSERVATIONS", text)
        self.assertIn("REPLAY WINDOW: GEN 13 - 60", text)
        images = root.findall(".//svg:image", NS)
        self.assertEqual(len(images), 7)
        for image in images:
            url = image.attrib["href"]
            self.assertTrue(url.startswith("data:image/png;base64,"))
            png = base64.b64decode(url.split(",", 1)[1])
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", png[16:24]), (2, 2))
        self.assertIsNone(root.find(".//svg:script", NS))

    def test_single_zero_and_flat_history_render_finite_coordinates(self):
        for count in (1, 5):
            for value in (0, 25):
                with self.subTest(count=count, value=value):
                    root = self.render(count, lambda _: value)
                    coordinates = root.find(".//svg:polyline[@id='activity-trend']", NS).attrib["points"]
                    self.assertTrue(all(
                        math.isfinite(float(number))
                        for point in coordinates.split() for number in point.split(",")
                    ))

    def test_negative_delta_is_displayed_without_claiming_progress(self):
        text = "".join(self.render(2, lambda index: 100 - index * 10).itertext())
        self.assertIn("-10 sites (-10.00%)", text)
        self.assertIn("not scientific progress", text)

    def test_empty_history_fails_explicitly(self):
        with self.assertRaisesRegex(ValueError, "requires measurements"):
            render_ticker([], [], None, Path("unused.svg"))


if __name__ == "__main__":
    unittest.main()
