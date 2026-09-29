#!/usr/bin/env bash
#
# Model-check the power-handover protocol with TLC.
#
#   ./run.sh
#
# Runs the safe configuration plus the three deliberately-relaxed ones and
# asserts the documented outcome of each. Exit status is non-zero if any run
# disagrees with the documentation, so this doubles as a regression test.
set -euo pipefail

cd "$(dirname "$0")"

TLA_JAR="${TLA_JAR:-tla2tools.jar}"
if [ ! -f "$TLA_JAR" ]; then
  echo "tla2tools.jar not found - downloading (needs java 11+)"
  curl -sL -o "$TLA_JAR" https://github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar
fi

if ! command -v java >/dev/null 2>&1; then
  echo "java not found - install a JRE (e.g. apt-get install openjdk-17-jre-headless)" >&2
  exit 1
fi

run_tlc() {
  java -XX:+UseParallelGC -cp "$TLA_JAR" tlc2.TLC -config "$1" -workers auto PowerHandover.tla 2>&1
}

pass=0
fail=0

expect_clean() {
  local cfg=$1 out
  out=$(run_tlc "$cfg" || true)
  if grep -q "No error has been found" <<<"$out"; then
    echo "  PASS  $cfg - no invariant violated"
    pass=$((pass + 1))
  else
    echo "  FAIL  $cfg - expected a clean run"
    tail -20 <<<"$out"
    fail=$((fail + 1))
  fi
}

expect_violation() {
  local cfg=$1 inv=$2 out
  out=$(run_tlc "$cfg" || true)
  if grep -q "Error: Invariant $inv is violated" <<<"$out"; then
    echo "  PASS  $cfg - $inv violated, as designed"
    pass=$((pass + 1))
  else
    echo "  FAIL  $cfg - expected $inv to be violated"
    tail -20 <<<"$out"
    fail=$((fail + 1))
  fi
}

echo "safe protocol (all guards in place)"
expect_clean PowerHandover.cfg

echo "deliberately relaxed guards (each must produce its counterexample)"
expect_violation PowerHandoverBuggy_separation.cfg SeparationOfPowers
expect_violation PowerHandoverBuggy_human.cfg HumanRetainsAuthorization
expect_violation PowerHandoverBuggy_budget.cfg AuthorityBudget

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
