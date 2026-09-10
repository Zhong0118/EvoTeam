"""Run the approved N4 fixed-v0 baseline without printing credentials."""

import argparse
import asyncio
import json
from pathlib import Path

from evoteam.experiment import run_baseline
from evoteam.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    report = asyncio.run(
        run_baseline(repository, args.config.resolve(), args.output.resolve(), Settings())
    )
    print(
        json.dumps(
            {"experiment_id": report["experiment_id"], "requests_used": report["requests_used"]}
        )
    )


if __name__ == "__main__":
    main()
