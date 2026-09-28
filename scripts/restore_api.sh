#!/bin/bash
# WARNING: This script OVERWRITES api.py with an old recovered version.
# Do NOT run this unless you intentionally want to restore the old api.py.
# It will destroy any changes made to api.py since the recovery snapshot.
# Run once: reconstruct api.py from parts (recovery from accidental placeholder)
set -e
cd "$(dirname "$0")/.."
cat scripts/api_restore_part*.b64 | base64 -d > api.py
echo "Restored api.py ($(wc -c < api.py) bytes)"
python3 -m py_compile api.py && echo "syntax OK"
