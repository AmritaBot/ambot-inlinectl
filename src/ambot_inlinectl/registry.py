"""ambot 子命令注册表。

``ambot`` 的根命令是一个惰性解析的 :class:`click.Group`，子命令来源有三处：

1. ambot 自带命令（``run`` / ``nb`` / ``orm`` / ``plugin`` ...）
2. 进程内注册 —— :func:`register_command` 或 :func:`command`
3. 跨包注册 —— 第三方包通过 entry point 声明

entry point 组名为 ``ambot.commands``：

.. code-block:: toml

   [project.entry-points."ambot.commands"]
   doctor = "my_pkg.cli:doctor"

entry point 指向的对象可以是：

* 一个 ``click.Command``（``click.Group`` 亦可）
* 一个零参可调用对象，返回 ``click.Command``、``click.Command`` 序列，
  或 ``None``（返回 ``None`` 表示它已自行调用 :func:`register_command`）

单个 entry point 对应单个命令时，命令名以 entry point 名为准，便于包作者
用同一份实现暴露别名；返回多个命令时，各自使用命令自身的名称。
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

import click

ENTRY_POINT_GROUP = "ambot.commands"
"""第三方包声明 ambot 子命令所使用的 entry point 组名。"""

_registry: dict[str, click.Command] = {}
_overrides: dict[str, click.Command] = {}
_entry_point_cache: dict[str, click.Command] | None = None


def _normalize(name: str) -> str:
    """去掉首尾空白。命令名原样使用，不做下划线/连字符改写。"""
    return name.strip()


def _warn(message: str) -> None:
    click.secho(f"[ambot] {message}", fg="yellow", err=True)


def register_command(
    command: click.Command,
    name: str | None = None,
    *,
    replace: bool = False,
) -> click.Command:
    """把一个 click 命令注册为 ``ambot <name>`` 子命令。

    Args:
        command: 要注册的命令对象。
        name: 命令名，省略时取 ``command.name``。
        replace: 为 ``True`` 时允许覆盖 ambot 自带命令（例如 ``run``）。

    Returns:
        传入的 ``command``，方便链式使用。

    Raises:
        TypeError: ``command`` 不是 ``click.Command``。
        ValueError: 名称为空，或与已注册命令重名且未开启 ``replace``。
    """
    if not isinstance(command, click.Command):
        raise TypeError(f"需要 click.Command，收到 {type(command).__name__}")

    cmd_name = _normalize(name or command.name or "")
    if not cmd_name:
        raise ValueError("注册子命令需要一个非空名称")

    if cmd_name in _registry and not replace:
        raise ValueError(f"子命令 {cmd_name!r} 已被注册，如需覆盖请传 replace=True")

    command.name = cmd_name
    if replace:
        _overrides[cmd_name] = command
    else:
        _overrides.pop(cmd_name, None)
        _registry[cmd_name] = command
    return command


def unregister_command(name: str) -> bool:
    """移除一个已注册的子命令，返回是否真的移除了。"""
    cmd_name = _normalize(name)
    removed = _registry.pop(cmd_name, None) is not None
    return _overrides.pop(cmd_name, None) is not None or removed


def command(
    name: str | Callable[..., Any] | None = None,
    *,
    replace: bool = False,
    **attrs: Any,
) -> Callable[..., click.Command]:
    """把被装饰函数注册为子命令的装饰器。

    用法与 ``click.command`` 一致，额外支持 ``replace``：

    .. code-block:: python

       @command("doctor")
       def doctor() -> None:
           \"\"\"Check the project health.\"\"\"

       @command(replace=True)
       def run() -> None:
           ...  # 覆盖 ambot 自带的 run
    """

    def decorator(func: Callable[..., Any]) -> click.Command:
        cmd = click.command(name if isinstance(name, str) else None, **attrs)(func)
        return register_command(cmd, replace=replace)

    if callable(name):  # 裸用 @command
        return decorator(name)
    return decorator


def registered_commands() -> dict[str, click.Command]:
    """返回当前进程内注册的子命令（副本）。"""
    return dict(_registry)


def overridden_commands() -> dict[str, click.Command]:
    """返回声明覆盖 ambot 自带命令的子命令（副本）。"""
    return dict(_overrides)


def _coerce_commands(obj: Any, origin: str) -> list[click.Command]:
    """把 entry point 的加载结果整理成命令列表。"""
    if isinstance(obj, click.Command):
        return [obj]

    if callable(obj):
        result = obj()
        if result is None:
            return []  # 它已自行调用 register_command
        if isinstance(result, click.Command):
            return [result]
        if isinstance(result, (list, tuple)):
            return [item for item in result if isinstance(item, click.Command)]

    raise TypeError(f"{origin} 未返回 click.Command")


def load_entry_point_commands(*, force: bool = False) -> dict[str, click.Command]:
    """扫描并缓存 ``ambot.commands`` entry point 声明的子命令。

    加载失败只告警并跳过，不会中断 CLI。
    """
    global _entry_point_cache

    if _entry_point_cache is not None and not force:
        return dict(_entry_point_cache)

    found: dict[str, click.Command] = {}
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        origin = f"entry point {ep.name!r}"
        try:
            commands = _coerce_commands(ep.load(), origin)
        except Exception as exc:
            _warn(f"加载子命令 {ep.name!r} 失败：{exc}")
            continue

        if len(commands) == 1:
            cmd_name = _normalize(ep.name)
            commands[0].name = cmd_name
            found[cmd_name] = commands[0]
            continue

        for cmd in commands:
            cmd_name = _normalize(cmd.name or "")
            if cmd_name:
                found[cmd_name] = cmd

    _entry_point_cache = found
    return dict(found)


def clear_entry_point_cache() -> None:
    """清空 entry point 缓存（测试或热加载时使用）。"""
    global _entry_point_cache
    _entry_point_cache = None
