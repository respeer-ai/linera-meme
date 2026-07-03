#!/usr/bin/env bash
set -euo pipefail

# Install cargo-llvm-cov first: cargo install cargo-llvm-cov
# Report: target/llvm-cov/html/index.html

export CARGO_BUILD_JOBS=1

cargo llvm-cov \
  --workspace \
  --html \
  --output-dir target/llvm-cov \
  -- \
  --test-threads=1
