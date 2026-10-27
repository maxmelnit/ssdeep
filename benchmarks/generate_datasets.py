#!/usr/bin/env python3

import argparse
import random
import shutil
from pathlib import Path


def generate_files(directory, file_count, file_size, group_size, seed):
    directory.mkdir(parents=True, exist_ok=True)
    generated = 0

    for group in range((file_count + group_size - 1) // group_size):
        generator = random.Random(seed + group)
        base = bytearray(generator.randbytes(file_size))

        for variant in range(group_size):
            if generated == file_count:
                return

            contents = bytearray(base)
            if variant:
                change_size = min(max(file_size // 100, 64), 4096)
                available = max(1, file_size - change_size)
                start = (variant * 7919) % available
                contents[start:start + change_size] = generator.randbytes(change_size)

            filename = directory / f"group-{group:04d}-variant-{variant:02d}.bin"
            filename.write_bytes(contents)
            generated += 1


def main():
    parser = argparse.ArgumentParser(
        description="Generate deterministic ssdeep hashing and comparison datasets.")
    parser.add_argument("output", type=Path)
    parser.add_argument("--hash-files", type=int, default=64)
    parser.add_argument("--hash-size-mib", type=int, default=4)
    parser.add_argument("--compare-files", type=int, default=4096)
    parser.add_argument("--compare-size-kib", type=int, default=64)
    parser.add_argument("--group-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=401)
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args()

    if arguments.output.exists():
        if not arguments.force:
            raise SystemExit(
                f"{arguments.output} already exists; pass --force to replace it")
        shutil.rmtree(arguments.output)

    generate_files(
        arguments.output / "hashing",
        arguments.hash_files,
        arguments.hash_size_mib * 1024 * 1024,
        arguments.group_size,
        arguments.seed,
    )
    generate_files(
        arguments.output / "comparison",
        arguments.compare_files,
        arguments.compare_size_kib * 1024,
        arguments.group_size,
        arguments.seed + 100000,
    )

    hashing_size = arguments.hash_files * arguments.hash_size_mib
    comparison_size = arguments.compare_files * arguments.compare_size_kib / 1024
    print(f"Hashing dataset: {arguments.hash_files} files, {hashing_size} MiB")
    print(f"Comparison dataset: {arguments.compare_files} files, "
          f"{comparison_size:.0f} MiB")


if __name__ == "__main__":
    main()
