#!/usr/bin/env python3

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Summarise ssdeep benchmark CSV data.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()

    grouped = defaultdict(list)
    with arguments.input.open(newline="") as source:
        for row in csv.DictReader(source):
            key = (row["stage"], row["implementation"], int(row["threads"]))
            grouped[key].append(float(row["seconds"]))

    original_baselines = {}
    modified_baselines = {}
    for stage in {key[0] for key in grouped}:
        original_baselines[stage] = statistics.mean(
            grouped[(stage, "original", 1)])
        modified_baselines[stage] = statistics.mean(
            grouped[(stage, "modified", 1)])

    summary = []
    for key in sorted(grouped):
        stage, implementation, threads = key
        measurements = grouped[key]
        mean_seconds = statistics.mean(measurements)
        deviation = statistics.stdev(measurements) if len(measurements) > 1 else 0.0
        speedup_vs_original = original_baselines[stage] / mean_seconds
        if implementation == "modified":
            parallel_speedup = modified_baselines[stage] / mean_seconds
        else:
            parallel_speedup = 1.0
        summary.append({
            "stage": stage,
            "implementation": implementation,
            "threads": threads,
            "mean_seconds": mean_seconds,
            "standard_deviation": deviation,
            "speedup_vs_original": speedup_vs_original,
            "parallel_speedup": parallel_speedup,
            "parallel_efficiency": parallel_speedup / threads,
        })

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=summary[0].keys(),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(summary)

    for row in summary:
        print(f"{row['stage']:10} {row['implementation']:8} "
              f"threads={row['threads']:2} mean={row['mean_seconds']:.6f}s "
              f"sd={row['standard_deviation']:.6f}s "
              f"vs_original={row['speedup_vs_original']:.3f} "
              f"parallel_speedup={row['parallel_speedup']:.3f} "
              f"efficiency={row['parallel_efficiency']:.3f}")


if __name__ == "__main__":
    main()
