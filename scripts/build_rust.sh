#!/bin/bash
# Build Rust code for both Python (PyO3) and JavaScript (WASM)
#
# Run this after ANY changes to rust/src/**/*.rs
#
# Usage: ./scripts/build_rust.sh

set -e

echo "Building Rust for Python (PyO3)..."
poetry run maturin develop --release

echo ""
echo "Building Rust for JavaScript (WASM)..."
wasm-pack build rust/ --target web --out-dir ../imagestag/filters/js/wasm --features wasm --no-default-features

echo ""
echo "✓ Both Python and WASM bindings rebuilt successfully"
