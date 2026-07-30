#!/usr/bin/env python3
"""
Thin convenience wrapper so you can still run:
    python3 run_benchmark.py [args...]
instead of `python3 -m branchoff`. All real logic lives in the
branchoff/ package.
"""
from branchoff.cli import main

if __name__ == "__main__":
    main()
