#!/bin/bash
# Re-run every check on September + October: add October transactions to September's, replace master files.
set -e
cd "$(dirname "$0")"
python3 engine/merge.py data/september data/october data/merged
cd engine && BANKROWS=1 python3 run.py ../data/merged ../output
