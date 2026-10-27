#!/usr/bin/env python3

import argparse
import csv
import os
import subprocess
import time
from pathlib import Path


def run_timed(command, threads=None):
    environment = os.environ.copy()
    if threads is not None:
        environment["OMP_NUM_THREADS"] = str(threads)

    start = time.perf_counter()
    subprocess.run(
        command,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=environment,
    )
    return time.perf_counter() - start


def write_signatures(original, dataset, destination):
    with destination.open("wb") as output:
        subprocess.run(
            [str(original), "-r", "-b", str(dataset)],
            check=True,
            stdout=output,
            stderr=subprocess.DEVNULL,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark sequential and OpenMP ssdeep builds.")
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--modified", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=1)
    arguments = parser.parse_args()

    original = arguments.original.resolve()
    modified = arguments.modified.resolve()
    hashing_data = (arguments.data / "hashing").resolve()
    comparison_data = (arguments.data / "comparison").resolve()

    for path in (original, modified, hashing_data, comparison_data):
        if not path.exists():
            raise SystemExit(f"Missing required path: {path}")

    signatures = arguments.data / "comparison-signatures.ssdeep"
    write_signatures(original, comparison_data, signatures)

    hash_original = [str(original), "-r", str(hashing_data)]
    hash_modified = [str(modified), "-r", str(hashing_data)]
    compare_original = [str(original), "-x", "-t", "100", str(signatures)]
    compare_modified = [str(modified), "-x", "-t", "100", str(signatures)]

    for _ in range(arguments.warmups):
        run_timed(hash_original)
        run_timed(compare_original)

    rows = []
    for repeat in range(1, arguments.repeats + 1):
        rows.append({
            "stage": "hashing",
            "implementation": "original",
            "threads": 1,
            "repeat": repeat,
            "seconds": run_timed(hash_original),
        })
        rows.append({
            "stage": "comparison",
            "implementation": "original",
            "threads": 1,
            "repeat": repeat,
            "seconds": run_timed(compare_original),
        })

        for threads in arguments.threads:
            rows.append({
                "stage": "hashing",
                "implementation": "modified",
                "threads": threads,
                "repeat": repeat,
                "seconds": run_timed(hash_modified, threads),
            })
            rows.append({
                "stage": "comparison",
                "implementation": "modified",
                "threads": threads,
                "repeat": repeat,
                "seconds": run_timed(compare_modified, threads),
            })

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=["stage", "implementation", "threads", "repeat", "seconds"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(f"{row['stage']:10} {row['implementation']:8} "
              f"threads={row['threads']:2} repeat={row['repeat']:2} "
              f"seconds={row['seconds']:.6f}")
    print(f"Results written to {arguments.output}")


if __name__ == "__main__":
    main()
