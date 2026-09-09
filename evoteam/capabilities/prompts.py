"""读取已登记 Prompt；通过映射解析引用，不允许任意文件路径。"""

from importlib.resources import files
from types import MappingProxyType

from evoteam.domain.common import AssetRef

PROMPT_FILES = MappingProxyType(
    {
        ("planner", "v0"): "planner/v0.md",
        ("executor", "v0"): "executor/v0.md",
        ("executor", "v1-resource-check"): "executor/v1-resource-check.md",
        ("critic", "v0"): "critic/v0.md",
        ("verifier", "v0"): "verifier/v0.md",
    }
)


def load_prompt(ref: AssetRef) -> str:
    """未知引用直接 KeyError；不回退到其他版本。"""
    relative_path = PROMPT_FILES[(ref.id, ref.version)]
    return files("evoteam.prompts").joinpath(relative_path).read_text(encoding="utf-8")
