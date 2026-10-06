"""兼容层：把已下沉到 :mod:`amrita.utils` 的能力再导出给本包。

这些函数原先内联在 :mod:`ambot_inlinectl.plugin` 里，现在由 amrita 统一提供，
CLI 与 WebUI 共用同一份实现。本模块只负责搬运与再导出，不承载业务逻辑，
也不再保留第二份实现——那正是这次下沉要消除的东西。

要求 ``amrita>=1.11.0``（首个提供 ``amrita.utils.pyproject_io`` 的版本）。
版本过旧时给出可操作的报错，而不是让调用方撞上一个语焉不详的
``ModuleNotFoundError``。
"""

from __future__ import annotations

_MIN_AMRITA = "1.11.0"

try:
    from amrita.utils.plugin_discovery import (
        AMRITA_DIST_PREFIX,
        NONEBOT_DIST_PREFIX,
        DiscoveredPlugin,
        PluginKind,
        builtin_plugins_dir,
        discover_plugins,
        is_builtin,
        iter_dir_plugins,
        iter_dist_plugins,
        normalize_dist_name,
    )
    from amrita.utils.pyproject_io import (
        PluginTarget,
        PyprojectNotFoundError,
        find_pyproject,
        load_pyproject,
        modify_plugin_list,
        read_plugin_list,
        resolve_module_name,
        save_pyproject,
    )
except ImportError as exc:  # pragma: no cover - 仅在 amrita 过旧时触发
    raise ImportError(
        f"ambot-inlinectl 需要 amrita>={_MIN_AMRITA}"
        "（该版本起提供 amrita.utils.pyproject_io / plugin_discovery）。"
        "当前环境中的 amrita 过旧或缺失，请升级后再试。"
    ) from exc

__all__ = [
    "AMRITA_DIST_PREFIX",
    "NONEBOT_DIST_PREFIX",
    "DiscoveredPlugin",
    "PluginKind",
    "PluginTarget",
    "PyprojectNotFoundError",
    "builtin_plugins_dir",
    "discover_plugins",
    "find_pyproject",
    "is_builtin",
    "iter_dir_plugins",
    "iter_dist_plugins",
    "load_pyproject",
    "modify_plugin_list",
    "normalize_dist_name",
    "read_plugin_list",
    "resolve_module_name",
    "save_pyproject",
]
