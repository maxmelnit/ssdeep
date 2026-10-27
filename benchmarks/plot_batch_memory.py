#!/usr/bin/env python3

import argparse
import csv
import math
import subprocess
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib.colors import HexColor


WIDTH = 720
HEIGHT = 520

TEXT = HexColor("#20262E")
MUTED = HexColor("#5F6B76")
GRID = HexColor("#D9DEE3")
TIME = HexColor("#D36B1F")
MEMORY = HexColor("#1769AA")


def add_text(drawing, x, y, text, size=10, anchor="start", bold=False,
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


def read_results(path):
    results = []
    with path.open(newline="") as source:
        for row in csv.DictReader(source):
            results.append({
                "batch_size": int(row["batch_size"]),
                "seconds": float(row["mean_seconds"]),
                "sd": float(row["standard_deviation_seconds"]),
                "memory_mib": float(row["mean_maximum_rss_kib"]) / 1024,
            })
    return sorted(results, key=lambda item: item["batch_size"])


def add_panel(drawing, data, bottom, height, y_min, y_max, ticks, y_label,
              value_key, color, tick_format, label_format=None,
              error_key=None):
    left = 82
    right = WIDTH - 34
    top = bottom + height
    width = right - left
    slot_width = width / len(data)
    bar_width = slot_width * 0.56

    def x_position(index):
        return left + (index + 0.5) * slot_width

    def y_position(value):
        return bottom + (value - y_min) * height / (y_max - y_min)

    add_text(drawing, left, top + 9, y_label, size=10)
    for tick in ticks:
        y = y_position(tick)
        drawing.add(Line(left, y, right, y, strokeColor=GRID, strokeWidth=0.7))
        add_text(drawing, left - 10, y - 4, tick_format(tick),
                 size=9, anchor="end", color=MUTED)

    drawing.add(Line(left, bottom, right, bottom, strokeColor=TEXT, strokeWidth=1))
    drawing.add(Line(left, bottom, left, top, strokeColor=TEXT, strokeWidth=1))

    for index, item in enumerate(data):
        x = x_position(index)
        y = y_position(item[value_key])
        drawing.add(Rect(
            x - bar_width / 2,
            bottom,
            bar_width,
            max(0, y - bottom),
            fillColor=color,
            strokeColor=None,
        ))

        if error_key is not None:
            low = max(y_min, item[value_key] - item[error_key])
            high = min(y_max, item[value_key] + item[error_key])
            y_low = y_position(low)
            y_high = y_position(high)
            drawing.add(Line(x, y_low, x, y_high,
                             strokeColor=TEXT, strokeWidth=1))
            drawing.add(Line(x - 5, y_low, x + 5, y_low,
                             strokeColor=TEXT, strokeWidth=1))
            drawing.add(Line(x - 5, y_high, x + 5, y_high,
                             strokeColor=TEXT, strokeWidth=1))

        formatted_value = (label_format or tick_format)(item[value_key])
        add_text(drawing, x, y + 9, formatted_value,
                 size=9, anchor="middle", color=color)
        add_text(drawing, x, bottom - 18, f"{item['batch_size']:,}",
                 size=9, anchor="middle", color=MUTED)

    add_text(drawing, (left + right) / 2, bottom - 38,
             "Batch size (signatures)", size=10, anchor="middle")


def create_figure(data):
    drawing = Drawing(WIDTH, HEIGHT)

    time_high = max(item["seconds"] + item["sd"] for item in data)
    time_step = 20
    time_max = math.ceil(time_high / time_step) * time_step
    time_ticks = list(range(0, time_max + 1, time_step))

    add_panel(
        drawing, data,
        bottom=310,
        height=145,
        y_min=0,
        y_max=time_max,
        ticks=time_ticks,
        y_label="Mean execution time (seconds)",
        value_key="seconds",
        color=TIME,
        tick_format=lambda value: f"{value:.1f}",
        label_format=lambda value: f"{value:.2f}",
        error_key="sd",
    )

    largest_memory = max(item["memory_mib"] for item in data)
    memory_step = 1000 if largest_memory <= 5000 else 4000
    memory_max = math.ceil(largest_memory / memory_step) * memory_step
    add_panel(
        drawing, data,
        bottom=65,
        height=145,
        y_min=0,
        y_max=memory_max,
        ticks=list(range(0, memory_max + 1, memory_step)),
        y_label="Mean peak resident memory (MiB)",
        value_key="memory_mib",
        color=MEMORY,
        tick_format=lambda value: f"{value:,.0f}",
    )

    return drawing


def main():
    parser = argparse.ArgumentParser(
        description="Plot Oracle batch-size timing and peak memory")
    parser.add_argument("input", type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--png", required=True, type=Path)
    arguments = parser.parse_args()

    figure = create_figure(read_results(arguments.input))
    arguments.pdf.parent.mkdir(parents=True, exist_ok=True)
    arguments.png.parent.mkdir(parents=True, exist_ok=True)
    renderPDF.drawToFile(figure, str(arguments.pdf))
    subprocess.run(
        [
            "pdftoppm", "-png", "-r", "200", "-singlefile",
            str(arguments.pdf), str(arguments.png.with_suffix("")),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print(f"Wrote {arguments.pdf}")
    print(f"Wrote {arguments.png}")


if __name__ == "__main__":
    main()
