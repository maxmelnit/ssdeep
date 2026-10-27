# Final source function profiling — 25 October 2026

An isolated Release build was made from the local `original/`, `modified/`
and root `CMakeLists.txt` sources on the Oracle VM. No application source was
changed for profiling. The existing VM source still contained the old
128-signature guards; the isolated build uses the local final source without
those guards. This experiment does not replace the earlier timing results.

Remote build: `/home/ubuntu/ssdeep-profile-20261025-o4Lbgc/build`
Remote raw recordings: `/home/ubuntu/ssdeep-profile-20261025-o4Lbgc/profiles`
Dataset: `/home/ubuntu/ssdeep/benchmark-data`

Method: `benchmarks/profile_functions.sh` performs one unrecorded warm-up
per workload/version, followed by three independent perf recordings.
Hashing uses the existing 240 files of 4 MiB; comparison uses 4,096 stored
signatures with `-x -t 100`. Original runs use one thread; modified runs use
24, with `OMP_PROC_BIND=spread` and `OMP_PLACES=cores`.

`perf record -e cycles:u -c 1000000` samples user-space CPU cycles at a fixed
period. `perf report --stdio --no-children --sort symbol --percent-limit 0.5`
reports self sample shares. These percentages are not elapsed times and do
not quantify time waiting for storage. Compiler-inlined work is attributed
to its containing function. All twelve reports recorded zero lost samples.
Some library addresses are unresolved, but the application functions listed
below resolve by name.

The values below are arithmetic means of three per-run percentages. Duplicate
rows for `fuzzy_update` in hashing-original-2 were summed (65.31 + 34.50).
The `.constprop.0` suffix identifies a compiler-specialized version of
`copy_eliminate_sequences`.

| Workload/function | Original (%) | Modified, 24 threads (%) |
|---|---:|---:|
| Hashing: fuzzy_update | 99.79 | 99.63 |
| Comparison: copy_eliminate_sequences | 53.78 | 58.56 |
| Comparison: score_strings | 18.60 | 20.21 |

`fuzzy_update` processes input bytes and updates the hash. The two comparison
functions shorten repeated character sequences and score signature strings.
The profile supports targeting file hashing and signature comparisons as the
main CPU work. A larger percentage after parallelisation is not evidence that
the function became slower: each percentage is relative to that run's samples.
