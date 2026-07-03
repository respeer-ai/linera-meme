#!/usr/bin/env bash
set -euo pipefail

# Install cargo-llvm-cov first: cargo install cargo-llvm-cov
# Report: target/llvm-cov/html/index.html

# Bound memory and parallelism to avoid host lockups.
ulimit -v 20971520
export CARGO_BUILD_JOBS=1

cargo llvm-cov \
  --workspace \
  --html \
  --output-dir target/llvm-cov \
  -- \
  --test-threads=1
