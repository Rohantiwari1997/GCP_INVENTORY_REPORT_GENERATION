#!/usr/bin/env bash
set -euo pipefail
python3 -m pip install --upgrade pip setuptools wheel
python3 setup.py sdist bdist_wheel
echo "Built package in dist/"