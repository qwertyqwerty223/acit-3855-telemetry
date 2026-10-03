#!/bin/bash

# Directory containing the test plan (current directory)
PROJECT_DIR="$(pwd)"

# Variables for threads and loops, defaulting to 10 (1 for loops) if not provided
THREADS=${1:-10}
LOOPS=${2:-1}

echo "Running jMeter with ${THREADS} threads and ${LOOPS} loops..."

# Clean up previous results
rm -rf "${PROJECT_DIR}/results.jtl"
rm -rf "${PROJECT_DIR}/report"

# Run jMeter headless
# Note: if `jmeter` is not in your PATH, you may need to replace `jmeter` 
# with the full path to your jmeter executable or use the java -jar approach from the lab.
jmeter \
  -n \
  -t "${PROJECT_DIR}/acit-3855-IAM-telemetry-test-plan.jmx" \
  -Jthreads="${THREADS}" \
  -Jloops="${LOOPS}" \
  -l "${PROJECT_DIR}/results.jtl" \
  -e -o "${PROJECT_DIR}/report"
