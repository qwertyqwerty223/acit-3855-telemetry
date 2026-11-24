#!/bin/bash

# Directory containing the project root
PROJECT_DIR="$(pwd)"

# Threads, loops, and plan file; defaults: 10 threads, 1 loop, the main plan
THREADS=${1:-10}
LOOPS=${2:-1}
PLAN=${3:-acit-3855-IAM-telemetry-test-plan.jmx}
NAME="${PLAN%.jmx}"
NAME="${NAME##*/}"

# Locate the test plan file (tests/plans or root)
if [ -f "${PROJECT_DIR}/tests/plans/${PLAN}" ]; then
  PLAN_PATH="${PROJECT_DIR}/tests/plans/${PLAN}"
elif [ -f "${PROJECT_DIR}/${PLAN}" ]; then
  PLAN_PATH="${PROJECT_DIR}/${PLAN}"
elif [ -f "${PLAN}" ]; then
  PLAN_PATH="${PLAN}"
else
  echo "Error: Test plan '${PLAN}' not found in tests/plans/ or current directory!"
  exit 1
fi

REPORTS_DIR="${PROJECT_DIR}/tests/reports"
mkdir -p "${REPORTS_DIR}"

echo "Running jMeter with ${THREADS} threads and ${LOOPS} loops using ${PLAN_PATH}..."

# Clean up previous temporary run artifacts
rm -rf "${REPORTS_DIR}/results.jtl"
rm -rf "${REPORTS_DIR}/report"

jmeter \
  -n \
  -t "${PLAN_PATH}" \
  -Jthreads="${THREADS}" \
  -Jloops="${LOOPS}" \
  -l "${REPORTS_DIR}/results.jtl" \
  -e -o "${REPORTS_DIR}/report"

# Preserve named copies of the run
cp "${REPORTS_DIR}/results.jtl" "${REPORTS_DIR}/results-${NAME}.jtl"
rm -rf "${REPORTS_DIR}/report-${NAME}"
cp -r "${REPORTS_DIR}/report" "${REPORTS_DIR}/report-${NAME}"
echo "Test complete! HTML report saved to: ${REPORTS_DIR}/report-${NAME}/index.html"
