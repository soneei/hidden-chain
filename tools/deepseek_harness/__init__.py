"""DeepSeek Harness — 通用 DeepSeek API 封装层（中立工具模块）。

被 Hidden Chain（健康项目）与 知泉 Tomomi（谈判副驾）等共同复用。

用法：
    from deepseek_harness import DeepSeekHarness
    h = DeepSeekHarness()
    h.chat("你好")
    h.chat_json("提取信息", schema_hint='{"key": "value"}')
"""

from .harness import DeepSeekHarness, DeepSeekError  # noqa: F401

__all__ = ["DeepSeekHarness", "DeepSeekError"]
__version__ = "0.1.0"
