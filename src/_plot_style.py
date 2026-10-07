"""绘图样式: CJK 字体探测 + unicode_minus。

两个分析脚本统一 import 本模块, 改字体逻辑只改这一处。
导入即生效, 无需调用任何函数。
"""
import warnings

import matplotlib
from matplotlib import font_manager

_CJK_CANDIDATES = (
    "Noto Sans CJK SC", "Noto Sans CJK JP", "Source Han Sans SC",
    "WenQuanYi Zen Hei", "WenQuanYi Micro Hei", "SimHei", "Microsoft YaHei",
)

_installed = {f.name for f in font_manager.fontManager.ttflist}
_cjk_found = [n for n in _CJK_CANDIDATES if n in _installed]

if _cjk_found:
    matplotlib.rcParams["font.sans-serif"] = _cjk_found + ["DejaVu Sans"]
else:
    warnings.warn(
        "未探测到 CJK 字体: 中文标题将渲染成方块 (□□□)。"
        "请安装例如 fonts-noto-cjk 后重跑。",
        RuntimeWarning,
        stacklevel=2,
    )
    matplotlib.rcParams["font.sans-serif"] = ["DejaVu Sans"]

matplotlib.rcParams["axes.unicode_minus"] = False
