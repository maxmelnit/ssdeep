To see the full performance report, see [performance_report.pdf](performance_report.pdf).

## Contents

I got the original ssdeep code from
[the ssdeep GitHub repository](https://github.com/ssdeep-project/ssdeep),
using commit `5ae3e5363281eacfac6292aebe77ebb0bde18c6e`.
There is an original copy in `original/` and made my parallelization
changes in `modified/`.

- `original/`: unmodified upstream source, before parallelization.
- `modified/`: source after my parallelization/changes.
- `CMakeLists.txt`: builds both versions in the same Release configuration.
- `tests/`: automated output-equivalence test.
- `benchmarks/`: data generation, timing, profiling and plotting scripts.
- `results/`: recorded measurements and report figures.

## Software requirements

- Linux or macOS, with C11 and C++11 compilers.
- CMake 3.16 or newer.
- OpenMP: GNU OpenMP with GCC, or LLVM libomp with Apple Clang.
- Python 3.9 or newer for the test and dataset scripts.
- Optional plotting tools: Python ReportLab and Poppler's `pdftoppm`.
- Optional profiling tools on Linux: `perf` and GNU `/usr/bin/time`.

I tested the build on Linux and macOS. The Windows files are still
included, but I didn't check a Windows OpenMP build.

## Hardware requirements

Both versions can run with one CPU core, but the modified version needs
multiple cores to benefit from parallelization. Set `OMP_NUM_THREADS` to
no more than the cores available to your job when measuring performance.

I tested this on an M2 Pro MacBook Pro with 10 CPU cores and 16 GB RAM,
and an Oracle Arm VM with 24 cores and 32 GB RAM. The memory and disk
space needed depend on the input:

- The source-file example below uses files already in this project, so
  there's nothing extra to download.
- The Oracle timing inputs require 1,216 MiB of storage, plus space for
  the build and output files.
- For 65,536 signatures, a batch of 1,024 used about 279 MiB of peak
  process memory. A full batch used about 16,409 MiB, so running that
  full-batch test needs more RAM. I used the 32 GB VM for this test.

## Compile both versions

Run the build and run commands from the main project folder, which
contains `CMakeLists.txt`, `original/` and `modified/`.

### Ubuntu with GCC

Install tools if needed:

```sh
sudo apt update
sudo apt install build-essential cmake python3
```

Build:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
```

The Oracle tests used Ubuntu 24.04 and GCC 13.3 with GNU OpenMP.

### macOS with Apple Clang

Install Xcode command-line tools if they aren't already installed:

```sh
xcode-select --install
```

With Homebrew installed, install CMake and libomp if needed:

```sh
brew install cmake libomp
```

Build:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DOpenMP_ROOT="$(brew --prefix libomp)"
cmake --build build --parallel
```

Both builds will make `build/bin/ssdeep-original` and
`build/bin/ssdeep-modified`.

## Run the program

We'll first answer the question: "do both versions create the same hashes?", and then "do both versions find the same similarities?". You can try the program on the files already in `original/` and `modified/`. Some files are the same between the two directories, and others have the changes made for this project.

Both programs read both folders. I'm using the source files as input
to check that the two versions produce the same results.

First, run both versions on these files. These commands save the hashes
in an `outputs/` directory, then compare the two output files:

```sh
mkdir -p outputs
build/bin/ssdeep-original -r original modified > outputs/original-hashes.ssdeep
OMP_NUM_THREADS=4 build/bin/ssdeep-modified -r original modified > outputs/modified-hashes.ssdeep
cmp outputs/original-hashes.ssdeep outputs/modified-hashes.ssdeep
```

The first command creates an `outputs` folder. Then I run the original
program and the modified program on the same files, saving their hashes
in separate files. The `>` symbol saves the output instead of showing it
in the terminal. Finally, `cmp` checks that the two files match exactly.
If it finishes successfully without printing anything, they match.

`-r` tells the program to include files inside subfolders.
`OMP_NUM_THREADS=4` tells the modified version to use four threads. You
can change that number for your machine. I save the results in `outputs/`
so they don't become extra input files the next time I run the commands.

## Check the comparisons

Next, I use the saved hashes to look for similar files. This time, both
programs read `outputs/original-hashes.ssdeep`. Using the same signature
file lets me check whether they find the same matches:

```sh
build/bin/ssdeep-original -x -t 0 outputs/original-hashes.ssdeep > outputs/original-matches.txt
OMP_NUM_THREADS=4 build/bin/ssdeep-modified -x -t 0 outputs/original-hashes.ssdeep > outputs/modified-matches.txt
cmp outputs/original-matches.txt outputs/modified-matches.txt
```

Again, I save each program's output in a separate file. The modified
version uses four threads, and `cmp` checks that its matches are exactly
the same as the original's, including the order they appear in.

`-x` tells ssdeep to compare the saved signatures. `-t 0` shows matches
with a score above zero. This is a similarity score, not a percentage
of identical bytes.

## Automated correctness test

To run the automated output checks:

```sh
ctest --test-dir build --output-on-failure
```

The test creates 160 temporary files from three upstream source files. It
checks hashing, directory comparison, pretty comparison and stored-signature
comparison with 1, 2, 4, 8, 10, 12, 16, 20 and 24 threads. It compares standard
output byte-for-byte and fails if either program returns an error. It also tests thread counts that may go over your machine's core count.

## Run the benchmarks

These tests measure how fast both versions run. First, I create the test
files, then time both programs, and finally summarize the results.

### 1. Create the test files

Run this command to create the same-sized dataset used for the Oracle
timing tests:

```sh
python3 benchmarks/generate_datasets.py benchmark-data \
  --hash-files 240 --hash-size-mib 4 \
  --compare-files 4096 --compare-size-kib 64
```

This creates two sets of files inside `benchmark-data/`:

- 240 files of 4 MiB each for the hashing test, totalling 960 MiB.
- 4,096 files of 64 KiB each for the comparison test, totalling 256 MiB.

The script generates groups of similar binary files with small differences.
It uses random seed 401 so it generates the same data each time.

### 2. Run both versions and record their times

The next command times hashing and comparison separately. It runs the
original program as the baseline, then runs the modified program with
1, 2, 4, 8, 12, 16, 20 and 24 threads. It records ten runs for each test.

These settings are for the 24-core Linux VM. You'll probably need to remove the higher thread counts, because I specifically cranked up the amount of cores on my VM for this test.

```sh
mkdir -p outputs
OMP_PROC_BIND=spread OMP_PLACES=cores \
python3 benchmarks/run_benchmarks.py \
  --original build/bin/ssdeep-original \
  --modified build/bin/ssdeep-modified \
  --data benchmark-data --output outputs/benchmark-results.csv \
  --threads 1 2 4 8 12 16 20 24 --repeats 10 --warmups 2
```

For the hashing test, both versions hash the 240 files. For the comparison
test, the script first uses the original program to generate signatures
from the 4,096 comparison files. Both versions then compare those same
signatures.

The script saves each measured time in `outputs/benchmark-results.csv`.
The two warm-up runs happen before recording times and only apply to
the original version.

`OMP_PROC_BIND=spread OMP_PLACES=cores` tells OpenMP to spread the threads
across CPU cores and keep them assigned there. The script times each
program from start to finish. It uses `-t 100` during comparison so the
program doesn't spend time printing matches.

### 3. Summarize the results

Once the tests finish, run:

```sh
python3 benchmarks/summarize_results.py \
  outputs/benchmark-results.csv outputs/benchmark-summary.csv
```

This reads the times and calculates the mean execution time,
standard deviation and speedup. It saves the summary in
`outputs/benchmark-summary.csv`.

These commands save your new measurements in `outputs/`.

## Change the comparison batch size

The modified program uses a batch size of 1,024 by default. This setting
is chosen when compiling the program, so changing it means building
the program again.

For example, these commands build a version that uses batches of up to
512 signatures:

```sh
cmake -S . -B build-batch-512 -DCMAKE_BUILD_TYPE=Release \
  -DSSDEEP_COMPARISON_BATCH_SIZE=512
cmake --build build-batch-512 --parallel
```

On macOS, use these commands instead:

```sh
cmake -S . -B build-batch-512 -DCMAKE_BUILD_TYPE=Release \
  -DSSDEEP_COMPARISON_BATCH_SIZE=512 \
  -DOpenMP_ROOT="$(brew --prefix libomp)"
cmake --build build-batch-512 --parallel
```

This puts the new program in `build-batch-512/`. It doesn't replace
the existing program in `build/`, so you can test both batch sizes.

To benchmark the 512-signature version, you replace this line in the
benchmark command:

```sh
--modified build/bin/ssdeep-modified \
```

with:

```sh
--modified build-batch-512/bin/ssdeep-modified \
```

Also change the output filename, for example to
`outputs/benchmark-results-batch-512.csv`, so you keep the results
from both tests.

The batch size is shared across all threads. It doesn't mean each
thread gets 512 signatures.

A batch is shared between threads; it is not the number of signatures
given to each thread.

## Recorded results and submission

I included some results from my previous runs.

The final Oracle thread-count CSVs are
`results/oracle-a1-24-final-raw.csv` and
`results/oracle-a1-24-final-summary.csv`. Their graph is
`results/oracle-a1-24-speedup.pdf`.

The large batch-size CSVs are `results/oracle-a1-65536-batch-raw.csv` and
`results/oracle-a1-65536-batch-summary.csv`. Their graph is
`results/oracle-a1-65536-batch-memory.pdf`.

Function profiling records and methods are in
`results/oracle-function-profiles-20261025/`.
