#!/usr/bin/env python3
"""Run bronze → silver → gold transforms."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.transforms import run_full_pipeline


def main() -> None:
    result = run_full_pipeline()
    print("Pipeline complete:", result)


if __name__ == "__main__":
    main()
