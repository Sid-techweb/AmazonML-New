#!/bin/bash
cd "/c/Users/Siddharth/Desktop/amazon Ml/amazon-ml-challenge-2026/experiments/v4"
LOG=tx.log
PY="/c/Users/Siddharth/Desktop/amazon Ml/amazon-ml-challenge-2026/.venv/Scripts/python.exe"
for cfg in "tx_us2in_base US India base 255 200 0.15" "tx_us2in_mono US India mono 127 400 0.15"; do
  set -- $cfg
  for i in 1 2 3; do
    echo "=== $1 attempt $i $(date +%H:%M:%S)" >> $LOG
    if "$PY" -u -W ignore tx.py $1 $2 $3 $4 $5 $6 $7 >> $LOG 2>&1; then echo "=== $1 OK $(date +%H:%M:%S)" >> $LOG; break; fi
    echo "=== $1 FAILED $(date +%H:%M:%S)" >> $LOG; sleep 60
  done
done
echo "=== TX DONE $(date +%H:%M:%S)" >> $LOG
