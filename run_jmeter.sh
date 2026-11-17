#!/bin/bash

# Directory containing the test plans (current directory)
PROJECT_DIR="$(pwd)"

# Threads, loops, and plan file; defaults: 10 threads, 1 loop, the original plan
THREADS=${1:-10}
LOOPS=${2:-1}
PLAN=${3:-acit-3855-IAM-telemetry-test-plan.jmx}
NAME="${PLAN%.jmx}"

echo "Running jMeter with ${THREADS} threads and ${LOOPS} loops using ${PLAN}..."

# Clean up previous results
rm -rf "${PROJECT_DIR}/results.jtl"
rm -rf "${PROJECT_DIR}/report"

jmeter \
  -n \
  -t "${PROJECT_DIR}/${PLAN}" \
  -Jthreads="${THREADS}" \
  -Jloops="${LOOPS}" \
  -l "${PROJECT_DIR}/results.jtl" \
  -e -o "${PROJECT_DIR}/report"

# Keep a copy of this run's raw results and report, named after the plan
cp "${PROJECT_DIR}/results.jtl" "${PROJECT_DIR}/results-${NAME}.jtl"
rm -rf "${PROJECT_DIR}/report-${NAME}"
cp -r "${PROJECT_DIR}/report" "${PROJECT_DIR}/report-${NAME}"
