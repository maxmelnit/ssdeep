#!/usr/bin/env python3

import argparse
import csv
import math
import subprocess
from collections import defaultdict
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Rect, String
from reportlab.lib.colors import HexColor


WIDTH = 720
HEIGHT = 440

TEXT = HexColor("#20262E")
MUTED = HexColor("#5F6B76")
GRID = HexColor("#D9DEE3")
IDEAL = HexColor("#7C8791")
HASHING = HexColor("#1769AA")
COMPARISON = HexColor("#D36B1F")


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


def read_speedups(path):
    speedups = defaultdict(list)
    with path.open(newline="") as source:
        for row in csv.DictReader(source):
            if row["implementation"] != "modified":
                continue
            speedups[row["stage"]].append((
                int(row["threads"]),
                float(row["speedup_vs_original"]),
            ))

    for stage in speedups:
        speedups[stage].sort()
    return speedups


def create_figure(speedups):
    drawing = Drawing(WIDTH, HEIGHT)
    left = 72
    right = 582
    bottom = 60
    top = 400
    plot_width = right - left
    plot_height = top - bottom
    threads = sorted({thread for values in speedups.values()
                      for thread, _ in values})
    x_min = min(threads)
    x_max = max(threads)
    y_min = 0
    largest_speedup = max(speedup for values in speedups.values()
                          for _, speedup in values)
    grid_step = 2 if max(x_max, largest_speedup) <= 10 else 4
    y_max = grid_step * math.ceil(max(x_max, largest_speedup) / grid_step)

    def x_position(value):
        return left + ((value - x_min) / (x_max - x_min)) * plot_width

    def y_position(value):
        return bottom + ((value - y_min) / (y_max - y_min)) * plot_height

    for value in range(0, y_max + 1, grid_step):
        y = y_position(value)
        drawing.add(Line(left, y, right, y, strokeColor=GRID, strokeWidth=0.7))
        add_text(drawing, left - 10, y - 4, str(value),
                 size=9, anchor="end", color=MUTED)

    for value in threads:
        x = x_position(value)
        add_text(drawing, x, bottom - 18, str(value),
                 size=9, anchor="middle", color=MUTED)

    drawing.add(Line(left, bottom, right, bottom, strokeColor=TEXT, strokeWidth=1))
    drawing.add(Line(left, bottom, left, top, strokeColor=TEXT, strokeWidth=1))
    add_text(drawing, left, top + 10, "Speedup (times original)", size=10)
    add_text(drawing, (left + right) / 2, 18, "OpenMP threads",
             size=10, anchor="middle")

    ideal_points = [(x_position(value), y_position(value)) for value in threads]
    drawing.add(PolyLine(
        [coordinate for point in ideal_points for coordinate in point],
        strokeColor=IDEAL,
        strokeWidth=1.5,
        strokeDashArray=[5, 4],
        fillColor=None,
    ))

    series = [
        ("hashing", "Hashing", HASHING, "circle"),
        ("comparison", "Comparison", COMPARISON, "square"),
    ]
    endpoint_labels = []
    for key, label, color, marker in series:
        values = speedups[key]
        points = [(x_position(thread), y_position(speedup))
                  for thread, speedup in values]
        drawing.add(PolyLine(
            [coordinate for point in points for coordinate in point],
            strokeColor=color,
            strokeWidth=2.2,
            fillColor=None,
        ))

        for x, y in points:
            if marker == "circle":
                drawing.add(Circle(x, y, 3.6, fillColor=color, strokeColor=color))
            else:
                drawing.add(Rect(x - 3.4, y - 3.4, 6.8, 6.8,
                                 fillColor=color, strokeColor=color))

        final_speedup = values[-1][1]
        endpoint_labels.append((
            y_position(final_speedup) - 4,
            f"{label} {final_speedup:.2f}x",
            color,
            True,
        ))

    endpoint_labels.append((
        y_position(x_max) - 4,
        "Ideal",
        IDEAL,
        False,
    ))
    previous_y = top + 20
    for target_y, label, color, bold in sorted(endpoint_labels, reverse=True):
        label_y = min(target_y, previous_y - 16)
        add_text(drawing, right + 10, label_y, label,
                 size=9, bold=bold, color=color)
        previous_y = label_y
    return drawing


def main():
    parser = argparse.ArgumentParser(
        description="Plot ssdeep hashing and comparison speedup")
    parser.add_argument("input", type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--png", required=True, type=Path)
    arguments = parser.parse_args()

    figure = create_figure(read_speedups(arguments.input))
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
