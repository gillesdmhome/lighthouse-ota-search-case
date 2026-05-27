#!/usr/bin/env python3
"""Run ingestion + Market Insight APIs locally (no Docker)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    env = {**dict(**{"PYTHONPATH": str(ROOT)}), **dict(**{k: v for k, v in __import__("os").environ.items()})}
    print("Starting ingestion API on :8080 and Market Insight API on :8081")
    print("Press Ctrl+C to stop")

    ingestion = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "services.ingestion_api.main:app", "--host", "0.0.0.0", "--port", "8080"],
        cwd=ROOT,
        env=env,
    )
    insight = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "services.market_insight_api.main:app", "--host", "0.0.0.0", "--port", "8081"],
        cwd=ROOT,
        env=env,
    )
    try:
        ingestion.wait()
    except KeyboardInterrupt:
        ingestion.terminate()
        insight.terminate()


if __name__ == "__main__":
    main()
