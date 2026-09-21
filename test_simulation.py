import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
