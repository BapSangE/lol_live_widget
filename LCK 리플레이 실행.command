#!/bin/zsh
cd "${0:A:h}"
exec .venv312/bin/python scripts/run_lck_replay.py
