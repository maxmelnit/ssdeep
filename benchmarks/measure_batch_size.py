#!/usr/bin/env python3

import argparse
import csv
import os
import random
import statistics
import subprocess
import tempfile
import time
from collections import defaultdict
from pathlib import Path


def run_command(executable, signatures, threads, measure_memory):
    environment = os.environ.copy()
    environment["OMP_NUM_THREADS"] = str(threads)
    environment["OMP_PROC_BIND"] = "spread"
    environment["OMP_PLACES"] = "cores"
    command = [str(executable), "-x", "-t", "100", str(signatures)]

    if not measure_memory:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
        )
        return None

    with tempfile.NamedTemporaryFile(prefix="ssdeep-time-", delete=False) as output:
        metrics_path = Path(output.name)

    try:
        measured_command = [
            "/usr/bin/time", "-v", "-o", str(metrics_path), *command
        ]
        started = time.perf_counter()
        subprocess.run(
            measured_command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
        )
        seconds = time.perf_counter() - started

        maximum_rss_kib = None
        for line in metrics_path.read_text().splitlines():
            if "Maximum resident set size (kbytes):" in line:
                maximum_rss_kib = int(line.rsplit(":", 1)[1].strip())
                break
        if maximum_rss_kib is None:
            raise RuntimeError("GNU time did not report maximum resident set size")
        return seconds, maximum_rss_kib
    finally:
        metrics_path.unlink(missing_ok=True)


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as destination:
        writer = csv.DictWriter(
            destination, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Measure comparison time and peak memory by batch size")
    parser.add_argument(
        "--executable-template", required=True,
        help="executable path containing {size}")
    parser.add_argument("--signatures", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--threads", type=int, default=24)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument(
        "--sizes", type=int, nargs="+",
        default=[1024, 4096, 8192, 16384, 32768])
    arguments = parser.parse_args()

    executables = {
        size: Path(arguments.executable_template.format(size=size)).resolve()
        for size in arguments.sizes
    }
    missing = [str(path) for path in executables.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing executables: " + ", ".join(missing))
    signatures = arguments.signatures.resolve()
    if not signatures.is_file():
        raise SystemExit(f"missing signatures: {signatures}")

    for size in arguments.sizes:
        for _ in range(arguments.warmups):
            run_command(executables[size], signatures, arguments.threads, False)

    rows = []
    random_generator = random.Random(401)
    for repeat in range(1, arguments.repeats + 1):
        order = list(arguments.sizes)
        random_generator.shuffle(order)
        for size in order:
            seconds, maximum_rss_kib = run_command(
                executables[size], signatures, arguments.threads, True)
            row = {
                "batch_size": size,
                "threads": arguments.threads,
                "repeat": repeat,
                "seconds": seconds,
                "maximum_rss_kib": maximum_rss_kib,
            }
            rows.append(row)
            print(
                f"batch={size:5} repeat={repeat} seconds={seconds:.3f} "
                f"max_rss={maximum_rss_kib / 1024:.1f} MiB",
                flush=True,
            )

    write_csv(
        arguments.output,
        rows,
        ["batch_size", "threads", "repeat", "seconds", "maximum_rss_kib"],
    )

    by_size = defaultdict(list)
    for row in rows:
        by_size[row["batch_size"]].append(row)

    summary = []
    for size in sorted(by_size):
        timings = [row["seconds"] for row in by_size[size]]
        memory = [row["maximum_rss_kib"] for row in by_size[size]]
        summary.append({
            "batch_size": size,
            "threads": arguments.threads,
            "mean_seconds": statistics.mean(timings),
            "median_seconds": statistics.median(timings),
            "standard_deviation_seconds": statistics.stdev(timings),
            "mean_maximum_rss_kib": statistics.mean(memory),
            "maximum_rss_kib": max(memory),
        })

    write_csv(
        arguments.summary,
        summary,
        [
            "batch_size", "threads", "mean_seconds", "median_seconds",
            "standard_deviation_seconds", "mean_maximum_rss_kib",
            "maximum_rss_kib",
        ],
    )

    print("\nSummary:")
    for row in summary:
        print(
            f"batch={row['batch_size']:5} "
            f"mean={row['mean_seconds']:.3f}s "
            f"median={row['median_seconds']:.3f}s "
            f"max_rss={row['mean_maximum_rss_kib'] / 1024:.1f} MiB"
        )


if __name__ == "__main__":
    main()
