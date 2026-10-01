import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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

    def test_legacy_history_keeps_original_measurements(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            first = simulation.run(output, steps=1)
            legacy_fields = [
                "generation", "updated_at", "mean_v", "standard_deviation_v",
                "active_cells", "total_cells",
            ]
            with (output / "history.csv").open("w", newline="") as history_file:
                writer = csv.DictWriter(history_file, fieldnames=legacy_fields)
                writer.writeheader()
                writer.writerow({key: first[key] for key in legacy_fields})
            simulation.run(output, steps=2, site_directory=output / "site")
            with (output / "history.csv").open(newline="") as history_file:
                rows = list(csv.DictReader(history_file))
            self.assertEqual(len(rows), 2)
            for key in legacy_fields:
                self.assertEqual(rows[0][key], str(first[key]))
            self.assertEqual(rows[0]["steps"], "")
            self.assertEqual(rows[0]["daily_generations"], "")
            self.assertEqual(rows[1]["steps"], "2")


def small_state():
    return {
        "model": "gray-scott", "width": 4, "height": 4, "generation": 0,
        "parameters": {
            "diffusion_u": simulation.DU, "diffusion_v": simulation.DV,
            "feed": simulation.FEED, "kill": simulation.KILL, "dt": simulation.DT,
        },
        "u": [[0.50 for _ in range(4)] for _ in range(4)],
        "v": [[0.25 for _ in range(4)] for _ in range(4)],
    }


class CadenceTests(unittest.TestCase):
    def test_daily_draw_is_reproducible_bounded_and_varies(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        counts = set()
        for day in range(366):
            now = start + timedelta(days=day)
            plan = simulation.daily_plan(now)
            count = plan["daily_generations"]
            counts.add(count)
            self.assertIn(count, range(3, 7))
            self.assertEqual(len(set(plan["hours_utc"])), count)
            self.assertTrue({0, 8, 16}.issubset(plan["hours_utc"]))
            self.assertTrue(set(plan["hours_utc"]).issubset({0, 4, 8, 12, 16, 20}))
            self.assertEqual(count * plan["steps_per_generation"], 480)
            self.assertEqual(simulation.daily_plan(now + timedelta(hours=23)), plan)
            self.assertEqual(
                simulation.daily_plan(now.astimezone(timezone(timedelta(hours=-7)))), plan
            )
        self.assertEqual(counts, {3, 4, 5, 6})

    @patch("simulation.initial_state", side_effect=small_state)
    def test_each_daily_draw_produces_exactly_its_count_and_480_steps(self, _initial):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        days = {}
        for offset in range(366):
            now = start + timedelta(days=offset)
            days.setdefault(simulation.daily_plan(now)["daily_generations"], now)
        for count, day in days.items():
            with self.subTest(count=count), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                advances = []
                for hour in range(0, 24, 4):
                    now = day.replace(hour=hour, minute=17)
                    result = simulation.evolve(output, output / "site", "schedule", now)
                    if result["advanced"]:
                        advances.append(result["metrics"])
                    before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
                    retry = simulation.evolve(output, output / "site", "schedule", now)
                    self.assertFalse(retry["advanced"])
                    self.assertEqual(
                        before, {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
                    )
                self.assertEqual(len(advances), count)
                self.assertEqual(sum(item["steps"] for item in advances), 480)
                self.assertEqual([item["generation"] for item in advances], list(range(1, count + 1)))

    @patch("simulation.initial_state", side_effect=small_state)
    def test_manual_run_does_not_consume_schedule_and_new_day_advances(self, _initial):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            now = datetime(2026, 10, 1, 0, 17, tzinfo=timezone.utc)
            simulation.evolve(output, output / "site", "push", now)
            scheduled = simulation.evolve(output, output / "site", "schedule", now)
            self.assertEqual(scheduled["metrics"]["generation"], 2)
            simulation.evolve(output, output / "site", "workflow_dispatch", now)
            self.assertFalse(simulation.evolve(output, output / "site", "schedule", now)["advanced"])
            tomorrow = now + timedelta(days=1)
            next_day = simulation.evolve(output, output / "site", "schedule", tomorrow)
            self.assertTrue(next_day["advanced"])
            self.assertEqual(next_day["metrics"]["cadence_date"], tomorrow.date().isoformat())
            self.assertEqual(next_day["metrics"]["generation"], 4)

    @patch("simulation.initial_state", side_effect=small_state)
    def test_daily_count_changes_next_field_not_chemical_parameters(self, _initial):
        now = datetime(2026, 10, 1, tzinfo=timezone.utc)
        states = []
        for count in (3, 6):
            plan = {**simulation.daily_plan(now), "daily_generations": count, "steps_per_generation": 480 // count}
            with tempfile.TemporaryDirectory() as directory, patch("simulation.daily_plan", return_value=plan):
                output = Path(directory)
                result = simulation.evolve(output, output / "site", "push", now)
                self.assertEqual(result["metrics"]["steps"], 480 // count)
                states.append(json.loads((output / "state.json").read_text()))
        self.assertNotEqual(states[0]["v"], states[1]["v"])
        self.assertEqual(states[0]["parameters"], states[1]["parameters"])

    def test_scheduled_steps_cannot_override_daily_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "daily plan"):
                simulation.evolve(Path(directory), Path(directory) / "site", "schedule", steps=1)


if __name__ == "__main__":
    unittest.main()
