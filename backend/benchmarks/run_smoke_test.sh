#!/bin/bash
set -euo pipefail

echo "========================================================"
echo " SmartKids Oracle ARM64 TTS Live Smoke Test Harness"
echo " Target: Ampere A1 (2 OCPU / 12 GB RAM) Ubuntu 22.04"
echo "========================================================"

# 1. System Hardware Verification
echo "[1/4] Checking Hardware Profile..."
uname -m
nproc
free -h

# 2. Python & PyTorch Verification
echo "[2/4] Verifying Python Environment..."
python3 --version

# 3. Execute Arabic Hamza & Tokenizer Benchmark
echo "[3/4] Running Hamza & Performance Benchmark..."
python3 /backend/benchmarks/benchmark_oracle_arm64.py

# 4. Result Inspection
echo "[4/4] Output Results:"
cat /backend/benchmarks/benchmark_results.json
echo "Smoke test completed."
