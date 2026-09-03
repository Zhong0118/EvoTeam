# EvoTeam 开发环境说明

## 当前环境

```text
Python 3.12
uv
openJiuwen Core
```

当前仓库初始化阶段只维护：

```text
main
```

暂不提前创建多人分支。

---

## 本地初始化

项目第一次创建：

```bash
uv init --app .
uv python pin 3.12
uv venv --python 3.12
```

验证：

```bash
uv run python --version
```

应看到：

```text
Python 3.12.x
```

不要求执行：

```bash
source .venv/bin/activate
```

团队统一优先：

```bash
uv run ...
```

---

## 安装依赖

```bash
uv add openjiuwen
```

开发工具：

```bash
uv add --dev pytest pytest-asyncio ruff pyright
```

后续按需：

```bash
uv add fastapi "uvicorn[standard]" pydantic pydantic-settings
```

不要使用：

```bash
pip install ...
conda install ...
```

作为项目依赖管理方式。

---

## 队友初始化

Clone 后：

```bash
uv sync
uv run python --version
```

如果本机没有 Python 3.12：

```bash
uv python install 3.12
uv sync
```

---

## Git 当前策略

当前：

```text
main only
```

适合完成：

- 环境；
- 文档；
- 基础目录；
- openJiuwen 最小验证。

真正进入多人并行功能开发后：

```text
feat/<task>
fix/<task>
docs/<task>
```

然后 PR 回：

```text
main
```

原则：

> 分支属于任务，不属于个人。

---

## 必须提交

```text
pyproject.toml
uv.lock
.python-version
.env.example
```

不要提交：

```text
.venv/
.env
*.db
.DS_Store
```

---

## 推荐命令

```bash
uv sync
uv run pytest
uv run ruff check .
```

---

## 当前优先级

```text
产品设计
↓
架构设计
↓
实验设计
↓
阶段汇报
↓
再进入 MVP
```
