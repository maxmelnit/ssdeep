#!/usr/bin/env bash
set -euo pipefail
build_dir=$(realpath "$1")
data_dir=$(realpath "$2")
output_dir=$3
mkdir -p "$output_dir"
output_dir=$(realpath "$output_dir")
export OMP_PROC_BIND=spread OMP_PLACES=cores
for workload in hashing comparison; do
  if [[ "$workload" == hashing ]]; then
    arguments=(-r "$data_dir/hashing")
  else
    arguments=(-x -t 100 "$data_dir/comparison-signatures.ssdeep")
  fi
  for implementation in original modified; do
    executable="$build_dir/bin/ssdeep-$implementation"
    if [[ "$implementation" == modified ]]; then
      export OMP_NUM_THREADS=24
    else
      export OMP_NUM_THREADS=1
    fi
    "$executable" "${arguments[@]}" > /dev/null
    for repeat in 1 2 3; do
      prefix="$output_dir/$workload-$implementation-$repeat"
      sudo -n env OMP_NUM_THREADS="$OMP_NUM_THREADS" OMP_PROC_BIND=spread OMP_PLACES=cores \
        perf record -e cycles:u -c 1000000 -o "$prefix.data" -- \
        "$executable" "${arguments[@]}" > /dev/null 2> "$prefix-record.txt"
      sudo -n perf report -i "$prefix.data" --stdio --no-children \
        --sort symbol --percent-limit 0.5 > "$prefix-report.txt"
      echo "Finished $workload $implementation repeat $repeat"
    done
  done
done
