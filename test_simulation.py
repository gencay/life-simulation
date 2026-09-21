import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import simulation


class SimulationTests(unittest.TestCase):
    def test_advance_changes_state_and_generation(self):
        state = simulation.initial_state()
        original_v = [row[:] for row in state["v"]]

        simulation.advance(state, steps=1)

        self.assertEqual(state["generation"], 1)
        self.assertNotEqual(state["v"], original_v)
        self.assertTrue(
            all(0.0 <= value <= 1.0 for row in state["v"] for value in row)
        )

    def test_run_persists_and_continues_state(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            site = output / "site"
            first = simulation.run(output, steps=1, site_directory=site)
            second = simulation.run(output, steps=1, site_directory=site)

            self.assertEqual(first["generation"], 1)
            self.assertEqual(second["generation"], 2)
            self.assertTrue((output / "latest.svg").exists())
            self.assertTrue((site / "data" / "latest.svg").exists())
            self.assertTrue((site / "data" / "history.json").exists())
            self.assertEqual(
                len((output / "history.csv").read_text().splitlines()),
                3,
            )
            dashboard = json.loads((site / "data" / "dashboard.json").read_text())
            self.assertEqual(dashboard["metrics"], second)
            self.assertEqual(int(dashboard["history"][-1]["generation"]), 2)
            self.assertEqual([frame["generation"] for frame in dashboard["frames"]], [1, 2])
            frame = dashboard["frames"][-1]
            self.assertEqual(len(frame["pixels"]), frame["width"] * frame["height"])
            self.assertTrue(all(0 <= pixel <= 255 for pixel in frame["pixels"]))
            self.assertNotEqual(
                dashboard["frames"][0]["pixels"], dashboard["frames"][1]["pixels"]
            )

    def test_frame_retention_deduplication_and_full_history(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            simulation, "MAX_FRAMES", 2
        ):
            output = Path(directory)
            site = output / "site"
            for _ in range(3):
                simulation.run(output, steps=1, site_directory=site)
            simulation.publish_dashboard(output, site)
            dashboard = json.loads((site / "data" / "dashboard.json").read_text())
            self.assertEqual(len(dashboard["history"]), 3)
            self.assertEqual([frame["generation"] for frame in dashboard["frames"]], [2, 3])
            self.assertEqual(dashboard["frames"][-1]["updated_at"], dashboard["metrics"]["updated_at"])


if __name__ == "__main__":
    unittest.main()
