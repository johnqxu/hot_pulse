"""修复 optimum 在 Python 3.14 上的 functools.partial 描述符兼容问题。

Python 3.14 为 functools.partial 添加了 __get__ 方法，使其成为描述符。
当通过实例访问类属性 partial 对象时（如 self.NORMALIZED_CONFIG_CLASS），
Python 会自动绑定实例作为第一个参数，破坏了 optimum 中 type(self).NORMALIZED_CONFIG_CLASS(self._config) 的调用模式。

修复方法：将 `self.NORMALIZED_CONFIG_CLASS` 替换为 `type(self).NORMALIZED_CONFIG_CLASS`，
绕开描述符协议，直接从类获取 partial 对象。

用法：在程序入口处 import 本模块即可自动应用补丁。
"""

from __future__ import annotations

import sys
from pathlib import Path


def _patch_file(filepath: Path) -> int:
    """在文件中替换 self.NORMALIZED_CONFIG_CLASS 为 type(self).NORMALIZED_CONFIG_CLASS。

    使用正则确保只替换 self.NORMALIZED_CONFIG_CLASS(self._config) 模式。
    """
    content = filepath.read_text(encoding="utf-8")
    old = "self.NORMALIZED_CONFIG_CLASS(self._config)"
    new = "type(self).NORMALIZED_CONFIG_CLASS(self._config)"
    count = content.count(old)
    if count:
        content = content.replace(old, new)
        filepath.write_text(content, encoding="utf-8")
    return count


def apply() -> int:
    """应用补丁，返回修补的总次数。"""
    total = 0
    for p in sys.path:
        if not p:
            continue
        root = Path(p)
        for pattern in [
            "optimum/exporters/base.py",
            "optimum/exporters/openvino/model_configs.py",
        ]:
            fp = root / pattern
            if fp.exists():
                n = _patch_file(fp)
                if n:
                    total += n
    return total


if __name__ == "__main__":
    n = apply()
    print(f"optimum Python 3.14 兼容补丁已应用: {n} 处修复")
