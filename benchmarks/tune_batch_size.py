#!/usr/bin/env python3

import argparse
import csv
import os
import random
import statistics
import subprocess
import time
from collections import defaultdict
from pathlib import Path


def run_once(executable, signatures, threads):
    environment = os.environ.copy()
    environment["OMP_NUM_THREADS"] = str(threads)
    command = [str(executable), "-x", "-t", "100", str(signatures)]

    started = time.perf_counter()
    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=environment,
    )
    return time.perf_counter() - started


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Compare ssdeep signature-comparison batch sizes")
    parser.add_argument(
        "--executable-template",
        required=True,
        help="executable path containing {size}")
    parser.add_argument("--signatures", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--threads", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument(
        "--sizes",
        type=int,
        nargs="+",
        default=[1, 4, 8, 10, 16, 32, 64, 128, 256, 512, 1024, 4096])
    arguments = parser.parse_args()

    executables = {
        size: Path(arguments.executable_template.format(size=size)).resolve()
        for size in arguments.sizes
    }
    missing = [str(path) for path in executables.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing executables: " + ", ".join(missing))
    if not arguments.signatures.is_file():
        raise SystemExit(f"missing signature file: {arguments.signatures}")

    for size in arguments.sizes:
        for _ in range(arguments.warmups):
            run_once(executables[size], arguments.signatures, arguments.threads)

    rows = []
    random_generator = random.Random(401)
    for repeat in range(1, arguments.repeats + 1):
        order = list(arguments.sizes)
        random_generator.shuffle(order)
        for size in order:
            seconds = run_once(
                executables[size], arguments.signatures, arguments.threads)
            rows.append({
                "batch_size": size,
                "threads": arguments.threads,
                "repeat": repeat,
                "seconds": seconds,
            })
            print(
                f"batch={size:4} threads={arguments.threads:2} "
                f"repeat={repeat:2} seconds={seconds:.6f}",
                flush=True,
            )

    write_csv(
        arguments.output,
        rows,
        ["batch_size", "threads", "repeat", "seconds"],
    )

    timings = defaultdict(list)
    for row in rows:
        timings[row["batch_size"]].append(row["seconds"])

    summary = []
    for size in sorted(timings):
        values = timings[size]
        summary.append({
            "batch_size": size,
            "threads": arguments.threads,
            "mean_seconds": statistics.mean(values),
            "median_seconds": statistics.median(values),
            "standard_deviation": statistics.stdev(values),
            "minimum_seconds": min(values),
            "maximum_seconds": max(values),
        })

    write_csv(
        arguments.summary,
        summary,
        [
            "batch_size",
            "threads",
            "mean_seconds",
            "median_seconds",
            "standard_deviation",
            "minimum_seconds",
            "maximum_seconds",
        ],
    )

    print("\nSummary:")
    for row in sorted(summary, key=lambda item: item["median_seconds"]):
        print(
            f"batch={row['batch_size']:4} "
            f"median={row['median_seconds']:.6f}s "
            f"mean={row['mean_seconds']:.6f}s "
            f"sd={row['standard_deviation']:.6f}s")


if __name__ == "__main__":
    main()
