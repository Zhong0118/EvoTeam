"""python -m evoteam 入口；导入模块时不解析命令行。"""

from evoteam.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
