"""Run one frozen N4 comparison; --preflight-only never creates a model runtime."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from evoteam.evolution.datasets import ManifestDatasets
from evoteam.experiment_manifest import prepare_experiment
from evoteam.n4_campaign import campaign_request_bound, execute_campaign
from evoteam.runtime.openjiuwen.adapter import OpenJiuwenRuntimeAdapter
from evoteam.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    raw = json.loads(args.config.read_text(encoding="utf-8"))
    if "expected_model" not in raw:
        parser.error("N4 比较必须显式登记 expected_model")
    prepared = prepare_experiment(
        repository,
        args.config.resolve(),
        args.output.resolve(),
        Settings(**dict[str, Any](_env_file=args.env_file)),
    )
    bound = campaign_request_bound(prepared.config, ManifestDatasets(prepared.manifest))
    if bound > prepared.config["maximum_model_requests"]:
        raise ValueError("完整实验所需请求超过预算")
    if args.preflight_only:
        print(
            json.dumps(
                {
                    "status": "preflight_only",
                    "maximum_requests": bound,
                    "note": "此目录已保留；真实执行使用新的输出目录，禁止隐式续跑",
                }
            )
        )
        return
    result = asyncio.run(
        execute_campaign(
            prepared, args.output.resolve(), OpenJiuwenRuntimeAdapter(models=(prepared.model,))
        )
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "requests_used": result["requests_used"],
                "promoted": result["promoted"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
