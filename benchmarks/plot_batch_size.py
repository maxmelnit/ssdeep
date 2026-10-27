#!/usr/bin/env python3

import argparse
import csv
import math
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib.colors import HexColor


WIDTH = 720
HEIGHT = 480

TEXT = HexColor("#20262E")
MUTED = HexColor("#5F6B76")
GRID = HexColor("#D9DEE3")
NEUTRAL = HexColor("#A8B2BC")
SELECTED = HexColor("#1769AA")


def read_measurements(path):
    grouped = defaultdict(list)
    with path.open(newline="") as source:
        for row in csv.DictReader(source):
            grouped[int(row["batch_size"])].append(float(row["seconds"]))

    results = []
    for batch_size in sorted(grouped):
        values = grouped[batch_size]
        quartiles = statistics.quantiles(values, n=4, method="inclusive")
        results.append({
            "batch_size": batch_size,
            "median": statistics.median(values),
            "q1": quartiles[0],
            "q3": quartiles[2],
            "runs": len(values),
        })
    return results


def add_text(drawing, x, y, text, size=11, anchor="start", bold=False,
             color=TEXT):
    drawing.add(String(
        x,
        y,
        text,
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        fillColor=color,
        textAnchor=anchor,
    ))


def add_panel(drawing, data, panel_y, panel_height, y_title,
              values, lower, upper, y_max, ticks, value_format,
              show_whiskers=False):
    left = 92
    right = WIDTH - 30
    bottom = panel_y
    top = panel_y + panel_height
    plot_width = right - left
    count = len(data)
    slot_width = plot_width / count
    bar_width = min(58, slot_width * 0.58)

    add_text(drawing, left, top + 8, y_title, size=10, color=TEXT)

    for tick in ticks:
        y = bottom + (tick / y_max) * panel_height
        drawing.add(Line(left, y, right, y, strokeColor=GRID, strokeWidth=0.7))
        add_text(drawing, left - 10, y - 4, value_format(tick),
                 size=9, anchor="end", color=MUTED)

    drawing.add(Line(left, bottom, right, bottom, strokeColor=TEXT, strokeWidth=1))
    drawing.add(Line(left, bottom, left, top, strokeColor=TEXT, strokeWidth=1))

    for index, item in enumerate(data):
        centre = left + slot_width * (index + 0.5)
        value = values[index]
        y_value = bottom + (value / y_max) * panel_height
        fill = SELECTED if item["batch_size"] == 1024 else NEUTRAL

        drawing.add(Rect(
            centre - bar_width / 2,
            bottom,
            bar_width,
            y_value - bottom,
            fillColor=fill,
            strokeColor=None,
        ))

        label_y = y_value + 7
        if show_whiskers:
            y_low = bottom + (lower[index] / y_max) * panel_height
            y_high = bottom + (upper[index] / y_max) * panel_height
            drawing.add(Line(centre, y_low, centre, y_high,
                             strokeColor=TEXT, strokeWidth=1.2))
            drawing.add(Line(centre - 6, y_low, centre + 6, y_low,
                             strokeColor=TEXT, strokeWidth=1.2))
            drawing.add(Line(centre - 6, y_high, centre + 6, y_high,
                             strokeColor=TEXT, strokeWidth=1.2))
            label_y = y_high + 7

        add_text(drawing, centre, label_y, value_format(value),
                 size=9, anchor="middle", bold=item["batch_size"] == 1024)
        add_text(drawing, centre, bottom - 17, f"{item['batch_size']:,}",
                 size=9, anchor="middle", color=MUTED)

        if item["batch_size"] == 1024:
            add_text(drawing, centre, bottom - 31, "selected",
                     size=8, anchor="middle", bold=True, color=SELECTED)

    add_text(drawing, (left + right) / 2, bottom - 48,
             "Batch size (signatures)", size=10, anchor="middle")

def create_figure(data, signature_count):
    drawing = Drawing(WIDTH, HEIGHT)

    selected = min(data, key=lambda item: item["median"])["batch_size"]
    if selected != 1024:
        raise RuntimeError(
            f"expected batch size 1,024 to be fastest, found {selected:,}")

    medians = [item["median"] for item in data]
    q1 = [item["q1"] for item in data]
    q3 = [item["q3"] for item in data]
    execution_max = math.ceil(max(q3) * 10) / 10

    add_panel(
        drawing,
        data,
        panel_y=285,
        panel_height=145,
        y_title="Median time (seconds)",
        values=medians,
        lower=q1,
        upper=q3,
        y_max=execution_max,
        ticks=[0.0, 0.2, 0.4, 0.6, 0.8],
        value_format=lambda value: f"{value:.3f}",
        show_whiskers=True,
    )

    memory = [
        item["batch_size"] * signature_count * 4 / (1024 * 1024)
        for item in data
    ]
    memory_max = math.ceil(max(memory) / 16) * 16
    add_panel(
        drawing,
        data,
        panel_y=65,
        panel_height=125,
        y_title="Temporary score storage (MiB)",
        values=memory,
        lower=memory,
        upper=memory,
        y_max=memory_max,
        ticks=[0, 16, 32, 48, 64],
        value_format=lambda value: f"{value:.0f}",
    )

    return drawing


def main():
    parser = argparse.ArgumentParser(
        description="Plot the clean ssdeep comparison batch-size results")
    parser.add_argument("input", type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--png", required=True, type=Path)
    parser.add_argument("--signature-count", type=int, default=4096)
    arguments = parser.parse_args()

    data = read_measurements(arguments.input)
    figure = create_figure(data, arguments.signature_count)

    arguments.pdf.parent.mkdir(parents=True, exist_ok=True)
    arguments.png.parent.mkdir(parents=True, exist_ok=True)
    renderPDF.drawToFile(figure, str(arguments.pdf))
    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-r",
            "200",
            "-singlefile",
            str(arguments.pdf),
            str(arguments.png.with_suffix("")),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print(f"Wrote {arguments.pdf}")
    print(f"Wrote {arguments.png}")


if __name__ == "__main__":
    main()
