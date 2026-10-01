"""Render a self-contained, README-safe SVG of recorded evolution."""

import base64
import math
import struct
import zlib
from html import escape
from pathlib import Path


def field_png(frame: dict) -> str:
    width, height = frame["width"], frame["height"]
    if len(frame["pixels"]) != width * height:
        raise ValueError("Recorded field dimensions do not match its pixels.")
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for value in frame["pixels"][y * width:(y + 1) * width]:
            rows.extend((max(5, value // 5), min(255, 25 + value), min(255, 75 + value)))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload))
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows)))
        + chunk(b"IEND", b"")
    )
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def render_ticker(history: list[dict], frames: list[dict], cadence: dict | None, path: Path) -> None:
    if not history or not frames:
        raise ValueError("Evolution ticker requires measurements and recorded fields.")
    if int(history[-1]["generation"]) != frames[-1]["generation"]:
        raise ValueError("Ticker measurements and field are from different generations.")
    values = [float(row["active_cells"]) for row in history]
    if not all(math.isfinite(value) and value >= 0 for value in values):
        raise ValueError("Activity history contains invalid values.")
    latest = history[-1]
    previous = history[-2] if len(history) > 1 else None
    delta = values[-1] - float(previous["active_cells"]) if previous else 0
    color = "#5eead4" if delta >= 0 else "#fb7185"
    change = "First observation"
    if previous:
        percent = f"{delta / float(previous['active_cells']) * 100:+.2f}%" if float(previous["active_cells"]) else "n/a"
        change = f"{delta:+,.0f} sites ({percent}) vs previous"
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="800" '
        'viewBox="0 0 1120 800" role="img" aria-labelledby="title description">',
        '<title id="title">Life simulation evolution ticker</title>',
        f'<desc id="description">Recorded activity across {len(history)} generations. '
        f'Latest generation {latest["generation"]}: {values[-1]:,.0f} active grid sites. '
        'Chemical self-organization, not biological life or financial data.</desc>',
        '<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1">'
        '<stop stop-color="#2dd4bf" stop-opacity=".28"/>'
        '<stop offset="1" stop-color="#2dd4bf" stop-opacity="0"/></linearGradient></defs>',
        '<rect width="1120" height="800" rx="22" fill="#070d18"/>',
        '<g font-family="ui-monospace, SFMono-Regular, Consolas, monospace">',
    ]

    def text(x: float, y: float, content: str, size: int = 13, fill: str = "#94a3b8", extra: str = "") -> None:
        svg.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" {extra}>{escape(str(content))}</text>')

    text(32, 36, "LIFE / EVOLUTION EXCHANGE", 18, "#67e8f9", 'font-weight="700"')
    text(1088, 36, "RECORDED RESULTS / NOT A LIVE PRICE", 11, extra='text-anchor="end"')
    text(32, 73, f"GEN {latest['generation']}  |  {len(history)} OBSERVATIONS  |  GRAY-SCOTT", 12)
    text(32, 125, f"{values[-1]:,.0f}", 43, "#f8fafc", 'font-weight="700"')
    text(32, 151, change, 13, color)
    text(32, 177, "ACTIVE GRID SITES / V > 0.10", 11)
    cards = [
        ("MEAN V", f"{float(latest['mean_v']):.5f}", "mean_v"),
        ("SPATIAL VARIATION", f"{float(latest['standard_deviation_v']):.5f}", "standard_deviation_v"),
    ]
    for index, (label, value, key) in enumerate(cards):
        x = 430 + index * 230
        text(x, 98, label, 11)
        text(x, 134, value, 28, "#f8fafc")
        if previous:
            difference = float(latest[key]) - float(previous[key])
            text(x, 161, f"{difference:+.5f} vs previous", 11, "#5eead4" if difference >= 0 else "#fb7185")
    text(905, 98, "DAILY DRAW", 11)
    text(905, 134, f"{cadence['daily_generations']} OBS" if cadence else "LEGACY", 28, "#f8fafc")
    text(905, 161, f"{latest['steps']} steps / gen" if latest.get("steps") else "Steps not recorded", 11)

    svg.append('<rect x="32" y="209" width="735" height="310" rx="12" fill="#0e1828"/>')
    text(52, 239, "ALL-TIME ACTIVITY", 12, "#e2e8f0")
    text(746, 239, f"HIGH {max(values):,.0f} / LOW {min(values):,.0f}", 11, extra='text-anchor="end"')
    x0, y0, width, height = 92, 267, 642, 193
    maximum = max(max(values), 1)
    first_gen = int(history[0]["generation"])
    generation_span = max(int(latest["generation"]) - first_gen, 1)
    for tick in range(5):
        y = y0 + height * tick / 4
        svg.append(f'<path d="M{x0} {y}h{width}" stroke="#223047"/>')
        text(x0 - 10, y + 4, f"{maximum * (1 - tick / 4):,.0f}", 10, extra='text-anchor="end"')
    points = [
        (x0 + (int(row["generation"]) - first_gen) / generation_span * width,
         y0 + height * (1 - value / maximum))
        for row, value in zip(history, values)
    ]
    coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    svg.append(f'<polygon points="{points[0][0]},{y0 + height} {coordinates} {points[-1][0]},{y0 + height}" fill="url(#area)"/>')
    svg.append(f'<polyline id="activity-trend" points="{coordinates}" fill="none" stroke="#5eead4" stroke-width="2.5"/>')
    svg.append(f'<circle cx="{points[-1][0]:.2f}" cy="{points[-1][1]:.2f}" r="4" fill="#f8fafc"/>')
    tick_count = min(4, len(history) - 1)
    for tick in range(tick_count + 1):
        index = round(tick * (len(history) - 1) / max(tick_count, 1))
        text(points[index][0], 481, str(history[index]["generation"]), 11, extra='text-anchor="middle"')
    text(415, 504, "GENERATION / NUMERICAL OBSERVATIONS", 10, extra='text-anchor="middle"')

    svg.append('<rect x="790" y="209" width="298" height="310" rx="12" fill="#0e1828"/>')
    text(810, 239, f"LATEST FIELD / GEN {latest['generation']}", 12, "#e2e8f0")
    svg.append(f'<image x="829" y="258" width="220" height="220" href="{field_png(frames[-1])}" style="image-rendering:pixelated"/>')
    coverage = values[-1] / float(latest["total_cells"]) * 100
    text(939, 504, f"{coverage:.1f}% ABOVE THRESHOLD", 11, extra='text-anchor="middle"')
    text(32, 553, "RECORDED FIELD HISTORY", 12, "#e2e8f0")
    text(1088, 553, f"REPLAY WINDOW: GEN {frames[0]['generation']} - {frames[-1]['generation']}", 11, extra='text-anchor="end"')
    count = min(6, len(frames))
    for index in range(count):
        frame = frames[round(index * (len(frames) - 1) / max(count - 1, 1))]
        x = 32 + index * 180
        svg.append(f'<rect x="{x}" y="568" width="156" height="141" rx="10" fill="#0e1828"/>')
        svg.append(f'<image x="{x + 28}" y="579" width="100" height="100" href="{field_png(frame)}" style="image-rendering:pixelated"/>')
        text(x + 78, 698, f"GEN {frame['generation']}", 11, "#cbd5e1", 'text-anchor="middle"')
    observed = str(latest["updated_at"])[:19].replace("T", " ") + " UTC"
    text(32, 739, f"OBSERVED {observed}", 11)
    if cadence:
        hours = " / ".join(f"{hour:02d}:17" for hour in cadence["hours_utc"])
        text(1088, 739, f"{cadence['date']} UTC: {hours}", 10, extra='text-anchor="end"')
    text(32, 773, "Chemical patterns, not organisms. Green/red show numerical change, not scientific progress.", 11)
    svg.append("</g></svg>\n")
    path.write_text("".join(svg), encoding="utf-8")
