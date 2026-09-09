"""离线配置预览与明确标记的无模型在线演示。"""

import argparse
import asyncio
import sys
from collections.abc import Sequence
from contextlib import redirect_stdout
from pathlib import Path

from evoteam.bootstrap import build_v0_strategy
from evoteam.demo import run_demo
from evoteam.domain.common import AssetRef
from evoteam.domain.role import ROLE_POOL
from evoteam.domain.strategy import Strategy
from evoteam.domain.task import Task
from evoteam.entrypoints import initialize_database, observe_history, run_task
from evoteam.monitoring.policy import EvolutionPolicy
from evoteam.settings import Settings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EvoTeam：配置预览与无模型闭环演示")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("roles", help="列出固定 Role Pool")
    v0 = commands.add_parser("v0", help="输出 DRAFT 配置，不运行 Agent")
    v0.add_argument("--model-id", required=True, help="登记的模型标识；预览可以使用占位值")
    v0.add_argument("--model-version", required=True, help="固定模型版本")
    demo = commands.add_parser("demo", help="Fake Runtime + 真实调度/评价/SQLite，无模型演示")
    demo.add_argument("--database", type=Path, required=True, help="全新 SQLite 文件路径")
    init = commands.add_parser("init", help="显式登记初始 CURRENT 策略和模型绑定，不调用模型")
    init.add_argument("--database", type=Path, required=True)
    init.add_argument("--strategy", type=Path, required=True)
    run = commands.add_parser("run", help="通过真实 openJiuwen 执行任务并封存")
    run.add_argument("--database", type=Path, required=True)
    run.add_argument("--task", type=Path, required=True)
    run.add_argument("--strategy-id", required=True)
    observe = commands.add_parser("observe", help="观察线上历史，不调用模型或启动演进")
    observe.add_argument("--database", type=Path, required=True)
    observe.add_argument("--strategy-id", required=True)
    observe.add_argument("--task-scope", required=True)
    observe.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "roles":
        for role in ROLE_POOL.values():
            print(f"{role.role.value}: {role.responsibility}")
    elif args.command == "demo":
        try:
            sealed = asyncio.run(run_demo(args.database))
        except OSError as exc:
            parser.error(str(exc))
        print(sealed.model_dump_json(indent=2))
    elif args.command in {"init", "run", "observe"}:
        try:
            if args.command == "init":
                strategy = Strategy.model_validate_json(args.strategy.read_text())
                asyncio.run(initialize_database(args.database, strategy, Settings()))
                print('{"initialized": true}')
            elif args.command == "run":
                task = Task.model_validate_json(args.task.read_text())
                # SDK 默认向 stdout 写日志；CLI 保持 stdout 只含机器可读结果。
                with redirect_stdout(sys.stderr):
                    sealed = asyncio.run(
                        run_task(
                            args.database, task, strategy_id=args.strategy_id, settings=Settings()
                        )
                    )
                print(sealed.model_dump_json(indent=2))
                return 0 if sealed.evaluation.metrics.success else 1
            else:
                policy = EvolutionPolicy.model_validate_json(args.policy.read_text())
                result = asyncio.run(
                    observe_history(
                        args.database,
                        strategy_id=args.strategy_id,
                        task_scope=args.task_scope,
                        policy=policy,
                    )
                )
                print(result.model_dump_json(indent=2))
        except (OSError, ValueError) as exc:
            # 配置验证错误可能携带原始输入；只报告类型，不打印凭据或文件内容。
            parser.error(f"输入或配置不合法（{type(exc).__name__}），请检查文件和 .env")
    else:
        strategy = build_v0_strategy(
            model_ref=AssetRef(id=args.model_id, version=args.model_version),
        )
        print(strategy.model_dump_json(indent=2))
    return 0
