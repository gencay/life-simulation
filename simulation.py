#!/usr/bin/env python3
"""Advance a persisted Gray-Scott reaction-diffusion simulation."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

WIDTH = 64
HEIGHT = 64
STEPS_PER_GENERATION = 80
DU = 0.16
DV = 0.08
FEED = 0.060
KILL = 0.062
DT = 1.0


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
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return state


def measurements(state: dict) -> dict:
    values = [value for row in state["v"] for value in row]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    active_cells = sum(value > 0.10 for value in values)
    return {
        "generation": state["generation"],
        "updated_at": state["updated_at"],
        "mean_v": round(mean, 8),
        "standard_deviation_v": round(math.sqrt(variance), 8),
        "active_cells": active_cells,
        "total_cells": len(values),
    }


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
    with destination.open("a", newline="", encoding="utf-8") as history_file:
        writer = csv.DictWriter(history_file, fieldnames=metrics.keys())
        if not exists:
            writer.writeheader()
        writer.writerow(metrics)


def run(output_directory: Path, steps: int) -> dict:
    output_directory.mkdir(parents=True, exist_ok=True)
    state_path = output_directory / "state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = initial_state()

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
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("simulation"))
    parser.add_argument("--steps", type=int, default=STEPS_PER_GENERATION)
    args = parser.parse_args()
    if args.steps <= 0:
        parser.error("--steps must be positive")

    print(json.dumps(run(args.output, args.steps), indent=2))


if __name__ == "__main__":
    main()
