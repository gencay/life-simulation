#!/usr/bin/env python3
"""Advance a persisted Gray-Scott reaction-diffusion simulation."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path

from evolution_ticker import render_ticker

WIDTH = 64
HEIGHT = 64
STEPS_PER_GENERATION = 80
DU = 0.16
DV = 0.08
FEED = 0.060
KILL = 0.062
DT = 1.0
MAX_FRAMES = 48
DAILY_STEPS = 480


def daily_plan(now: datetime) -> dict:
    day = now.astimezone(timezone.utc).date().isoformat()
    seed = f"life-simulation-cadence-v1:{day}"
    randomizer = random.Random(seed)
    count = randomizer.randint(3, 6)
    hours = sorted([0, 8, 16] + randomizer.sample([4, 12, 20], count - 3))
    return {
        "date": day,
        "seed": seed,
        "daily_generations": count,
        "hours_utc": hours,
        "steps_per_generation": DAILY_STEPS // count,
        "daily_steps": DAILY_STEPS,
    }


def initial_state(seed: int = 20260920) -> dict:
    randomizer = random.Random(seed)
    u = [[1.0 for _ in range(WIDTH)] for _ in range(HEIGHT)]
    v = [[0.0 for _ in range(WIDTH)] for _ in range(HEIGHT)]

    radius = 7
    center_x = WIDTH // 2
    center_y = HEIGHT // 2
    for y in range(center_y - radius, center_y + radius):
        for x in range(center_x - radius, center_x + radius):
            u[y][x] = 0.50 + randomizer.uniform(-0.02, 0.02)
            v[y][x] = 0.25 + randomizer.uniform(-0.02, 0.02)

    return {
        "model": "gray-scott",
        "width": WIDTH,
        "height": HEIGHT,
        "generation": 0,
        "parameters": {
            "diffusion_u": DU,
            "diffusion_v": DV,
            "feed": FEED,
            "kill": KILL,
            "dt": DT,
        },
        "u": u,
        "v": v,
    }


def laplacian(field: list[list[float]], x: int, y: int) -> float:
    height = len(field)
    width = len(field[0])
    center = field[y][x]
    return (
        field[y][(x - 1) % width]
        + field[y][(x + 1) % width]
        + field[(y - 1) % height][x]
        + field[(y + 1) % height][x]
        - 4.0 * center
    )


def advance(state: dict, steps: int = STEPS_PER_GENERATION) -> dict:
    u = state["u"]
    v = state["v"]
    height = state["height"]
    width = state["width"]

    for _ in range(steps):
        next_u = [[0.0 for _ in range(width)] for _ in range(height)]
        next_v = [[0.0 for _ in range(width)] for _ in range(height)]

        for y in range(height):
            for x in range(width):
                current_u = u[y][x]
                current_v = v[y][x]
                reaction = current_u * current_v * current_v
                updated_u = current_u + (
                    DU * laplacian(u, x, y)
                    - reaction
                    + FEED * (1.0 - current_u)
                ) * DT
                updated_v = current_v + (
                    DV * laplacian(v, x, y)
                    + reaction
                    - (FEED + KILL) * current_v
                ) * DT
                next_u[y][x] = min(1.0, max(0.0, updated_u))
                next_v[y][x] = min(1.0, max(0.0, updated_v))

        u = next_u
        v = next_v

    state["u"] = u
    state["v"] = v
    state["generation"] += 1
    state["steps"] = steps
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return state


def measurements(state: dict) -> dict:
    values = [value for row in state["v"] for value in row]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    active_cells = sum(value > 0.10 for value in values)
    metrics = {
        "generation": state["generation"],
        "updated_at": state["updated_at"],
        "mean_v": round(mean, 8),
        "standard_deviation_v": round(math.sqrt(variance), 8),
        "active_cells": active_cells,
        "total_cells": len(values),
    }
    metrics["steps"] = state.get("steps", "")
    metrics["daily_generations"] = state.get("cadence", {}).get("daily_generations", "")
    metrics["cadence_date"] = state.get("cadence", {}).get("date", "")
    metrics["event"] = state.get("event", "")
    metrics["scheduled_slot"] = state.get("scheduled_slot", "")
    return metrics


def render_svg(state: dict, destination: Path, scale: int = 8) -> None:
    width = state["width"]
    height = state["height"]
    rectangles = []
    for y, row in enumerate(state["v"]):
        for x, value in enumerate(row):
            intensity = min(255, max(0, round(value * 680)))
            red = max(5, intensity // 5)
            green = min(255, 25 + intensity)
            blue = min(255, 75 + intensity)
            rectangles.append(
                f'<rect x="{x * scale}" y="{y * scale}" width="{scale}" '
                f'height="{scale}" fill="rgb({red},{green},{blue})"/>'
            )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width * scale}" height="{height * scale}" '
        f'viewBox="0 0 {width * scale} {height * scale}">'
        '<rect width="100%" height="100%" fill="#030712"/>'
        + "".join(rectangles)
        + "</svg>\n"
    )
    destination.write_text(svg, encoding="utf-8")


def append_history(destination: Path, metrics: dict) -> None:
    exists = destination.exists()
    if exists:
        with destination.open(newline="", encoding="utf-8") as history_file:
            reader = csv.DictReader(history_file)
            fields = reader.fieldnames
            history = list(reader)
        if fields != list(metrics):
            if not fields or not set(fields).issubset(metrics):
                raise ValueError("History contains unexpected columns; refusing to discard data.")
            # Keep legacy rows intact; unknown historical cadence remains blank.
            with destination.open("w", newline="", encoding="utf-8") as history_file:
                writer = csv.DictWriter(history_file, fieldnames=metrics)
                writer.writeheader()
                writer.writerows(history)
    with destination.open("a", newline="", encoding="utf-8") as history_file:
        writer = csv.DictWriter(history_file, fieldnames=metrics.keys())
        if not exists:
            writer.writeheader()
        writer.writerow(metrics)


def record_frame(output_directory: Path, state: dict) -> list[dict]:
    destination = output_directory / "frames.json"
    frames = (
        json.loads(destination.read_text(encoding="utf-8"))
        if destination.exists()
        else []
    )
    frame = {
        **measurements(state),
        "width": state["width"],
        "height": state["height"],
        "pixels": [
            min(255, max(0, round(value * 680)))
            for row in state["v"]
            for value in row
        ],
    }
    frames = [item for item in frames if item["generation"] != frame["generation"]]
    frames.append(frame)
    frames = sorted(frames, key=lambda item: item["generation"])[-MAX_FRAMES:]
    destination.write_text(json.dumps(frames, separators=(",", ":")) + "\n")
    return frames


def publish_dashboard(output_directory: Path, site_directory: Path) -> None:
    data_directory = site_directory / "data"
    data_directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output_directory / "latest.svg", data_directory / "latest.svg")
    shutil.copyfile(output_directory / "metrics.json", data_directory / "metrics.json")

    with (output_directory / "history.csv").open(
        newline="", encoding="utf-8"
    ) as history_file:
        history = list(csv.DictReader(history_file))
    (data_directory / "history.json").write_text(
        json.dumps(history, indent=2) + "\n",
        encoding="utf-8",
    )
    state = json.loads((output_directory / "state.json").read_text(encoding="utf-8"))
    frames = record_frame(output_directory, state)
    render_ticker(history, frames, state.get("cadence"), output_directory / "evolution.svg")
    shutil.copyfile(output_directory / "evolution.svg", data_directory / "evolution.svg")
    # One response keeps the field, chart, and readings on the same generation.
    (data_directory / "dashboard.json").write_text(
        json.dumps(
            {
                "metrics": measurements(state),
                "parameters": state["parameters"],
                "cadence": state.get("cadence"),
                "history": history,
                "frames": frames,
            },
            separators=(",", ":"),
        ) + "\n",
        encoding="utf-8",
    )


def run(
    output_directory: Path,
    steps: int,
    site_directory: Path | None = None,
    cadence: dict | None = None,
    event: str = "local",
    scheduled_slot: str | None = None,
) -> dict:
    output_directory.mkdir(parents=True, exist_ok=True)
    state_path = output_directory / "state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        record_frame(output_directory, state)
    else:
        state = initial_state()

    state["event"] = event
    state["scheduled_slot"] = scheduled_slot or ""
    if cadence is not None:
        state["cadence"] = cadence
    else:
        state.pop("cadence", None)
    if scheduled_slot is not None:
        state["last_scheduled_slot"] = scheduled_slot
    state = advance(state, steps)
    metrics = measurements(state)
    state_path.write_text(
        json.dumps(state, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (output_directory / "metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n",
        encoding="utf-8",
    )
    append_history(output_directory / "history.csv", metrics)
    render_svg(state, output_directory / "latest.svg")
    record_frame(output_directory, state)
    if site_directory is not None:
        publish_dashboard(output_directory, site_directory)
    return metrics


def evolve(
    output_directory: Path,
    site_directory: Path,
    event: str,
    now: datetime | None = None,
    steps: int | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    plan = daily_plan(now)
    scheduled_slot = None
    if event == "schedule":
        if steps is not None:
            raise ValueError("Scheduled runs must use the daily plan's step count.")
        hour = now.astimezone(timezone.utc).hour // 4 * 4
        scheduled_slot = f"{plan['date']}T{hour:02d}:17Z"
        if hour not in plan["hours_utc"]:
            return {"advanced": False, "reason": "This window is not selected.", "cadence": plan}
        state_path = output_directory / "state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("last_scheduled_slot", "") >= scheduled_slot:
                return {"advanced": False, "reason": "This or a later window was already committed.", "cadence": plan}
    metrics = run(
        output_directory,
        steps if steps is not None else plan["steps_per_generation"],
        site_directory,
        cadence=plan,
        event=event,
        scheduled_slot=scheduled_slot,
    )
    return {"advanced": True, "metrics": metrics, "cadence": plan}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("simulation"))
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--steps", type=int)
    parser.add_argument(
        "--event", choices=["local", "push", "schedule", "workflow_dispatch"], default="local"
    )
    args = parser.parse_args()
    if args.steps is not None and args.steps <= 0:
        parser.error("--steps must be positive")
    if args.event == "schedule" and args.steps is not None:
        parser.error("--steps cannot override the scheduled daily plan")

    result = evolve(args.output, args.site, args.event, steps=args.steps)
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(f"advanced={str(result['advanced']).lower()}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
