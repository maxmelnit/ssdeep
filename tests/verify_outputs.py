#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command, threads=None):
    environment = os.environ.copy()
    if threads is not None:
        environment["OMP_NUM_THREADS"] = str(threads)
    return subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    ).stdout


def require_equal(label, expected, actual):
    if expected != actual:
        raise RuntimeError(f"{label}: modified output differs from original")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_outputs.py ORIGINAL MODIFIED")

    original = Path(sys.argv[1]).resolve()
    modified = Path(sys.argv[2]).resolve()
    repository = Path(__file__).resolve().parents[1]

    with tempfile.TemporaryDirectory(prefix="ssdeep-output-test-") as temporary:
        dataset = Path(temporary) / "dataset"
        dataset.mkdir()

        sources = [
            repository / "original" / "main.cpp",
            repository / "original" / "match.cpp",
            repository / "original" / "fuzzy.c",
        ]
        for index in range(160):
            source = sources[index % len(sources)]
            shutil.copyfile(source, dataset / f"file-{index:03d}{source.suffix}")

        commands = [
            ["-r", "-b", str(dataset)],
            ["-d", "-r", "-b", str(dataset)],
            ["-p", "-r", "-b", str(dataset)],
        ]

        thread_counts = (1, 2, 4, 8, 10, 12, 16, 20, 24)

        for arguments in commands:
            expected = run([str(original), *arguments])
            for threads in thread_counts:
                actual = run([str(modified), *arguments], threads)
                require_equal(f"{' '.join(arguments)} with {threads} threads",
                              expected, actual)

        signatures = Path(temporary) / "signatures.ssdeep"
        signatures.write_bytes(run([str(original), "-r", "-b", str(dataset)]))
        signature_arguments = ["-x", "-t", "0", str(signatures)]
        expected = run([str(original), *signature_arguments])
        for threads in thread_counts:
            actual = run([str(modified), *signature_arguments], threads)
            require_equal(f"signature comparison with {threads} threads",
                          expected, actual)

    print("All hashing and comparison outputs match the original.")


if __name__ == "__main__":
    main()
