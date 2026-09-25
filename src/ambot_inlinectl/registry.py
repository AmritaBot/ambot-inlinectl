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

entry point 的值支持标准 extras 语法，用来声明加载方式：

.. code-block:: toml

   [project.entry-points."ambot.commands"]
   memory = "my_pkg.cli:memory [full_load]"

带 ``full_load`` 的 entry point 在列表阶段（``ambot --help`` / ``ambot cmds``）
只暴露名称、不触发加载；真正被调用时才先 ``amrita.init()`` +
``amrita.load_plugins()``，再 ``ep.load()``。用于目标模块位于插件包内、且该包
import 期依赖插件加载器上下文（例如 ``nonebot.require(...)``）的场景。

entry point 之间出现同名命令时（``full_load`` 的也在内），按 ``(名称, 目标)``
排序后取先出现的一个，并往 stderr 告警，避免结果依赖安装顺序。
"""

from __future__ import annotations

import os
from collections.abc import Callable
from importlib.metadata import EntryPoint, entry_points
from typing import Any

import click

ENTRY_POINT_GROUP = "ambot.commands"
"""第三方包声明 ambot 子命令所使用的 entry point 组名。"""

FULL_LOAD_EXTRA = "full_load"
"""声明该 extra 的 entry point 会先自举 Amrita 再加载目标。

用法（``pyproject.toml``）::

    [project.entry-points."ambot.commands"]
    memory = "my_pkg.cli:memory [full_load]"

这类 entry point 以 entry point 名作为命令名（约定单个命令），并且在列表阶段
不会触发加载，因此 ``ambot --help`` 不受影响。
"""

COMMAND_CONTEXT_ENV = "AMBOT_COMMAND_CONTEXT"
"""自举 ``full_load`` entry point 前写入的环境变量（值为 ``"1"``）。

插件可据此判断自己是被 ``ambot <cmd>`` 拉起来的、而非在跑 bot，从而跳过
启动期的交互式检查 —— 否则维护命令可能被自己的启动检查挡在门外。
"""

_registry: dict[str, click.Command] = {}
_shadowed: set[str] = set()
_entry_point_cache: dict[str, click.Command] | None = None
_deferred_entry_point_cache: dict[str, click.Command] = {}
_bootstrap_done = False


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
        name: 命令名，省略时取 ``command.name``。显式传空串会报错。
        replace: 为 ``True`` 时允许覆盖同名命令，并优先于 ambot 自带命令。

    Returns:
        传入的 ``command``，方便链式使用。

    Raises:
        TypeError: ``command`` 不是 ``click.Command``。
        ValueError: 名称为空，或与已注册命令重名且未开启 ``replace``。
    """
    if not isinstance(command, click.Command):
        raise TypeError(f"需要 click.Command，收到 {type(command).__name__}")

    raw_name = name if name is not None else command.name
    cmd_name = _normalize(raw_name or "")
    if not cmd_name:
        raise ValueError("注册子命令需要一个非空名称")

    if cmd_name in _registry and not replace:
        raise ValueError(f"子命令 {cmd_name!r} 已被注册，如需覆盖请传 replace=True")

    command.name = cmd_name
    _registry[cmd_name] = command
    if replace:
        _shadowed.add(cmd_name)
    else:
        _shadowed.discard(cmd_name)
    return command


def unregister_command(name: str) -> bool:
    """移除一个已注册的子命令，返回是否真的移除了。"""
    cmd_name = _normalize(name)
    _shadowed.discard(cmd_name)
    return _registry.pop(cmd_name, None) is not None


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


def get_registered_command(name: str) -> click.Command | None:
    """按名称取一个进程内注册的子命令。"""
    return _registry.get(_normalize(name))


def overridden_commands() -> dict[str, click.Command]:
    """返回声明覆盖 ambot 自带命令的子命令（副本）。"""
    return {name: _registry[name] for name in sorted(_shadowed) if name in _registry}


def is_overridden(name: str) -> bool:
    """该名称是否以 ``replace=True`` 注册、应当优先于 ambot 自带命令。"""
    return _normalize(name) in _shadowed


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


def _add_entry_point_command(
    found: dict[str, click.Command],
    name: str,
    command: click.Command,
    origin: str,
) -> None:
    """写入 entry point 命令表，同名时保留先出现的一个并告警。"""
    if name in found:
        _warn(f"子命令 {name!r} 已被占用，忽略来自 {origin} 的重复定义")
        return
    command.name = name
    found[name] = command


def _iter_entry_points() -> list[EntryPoint]:
    """按 ``(名称, 目标)`` 排序后的 entry point 列表（不触发加载）。"""
    return sorted(
        entry_points(group=ENTRY_POINT_GROUP),
        key=lambda ep: (ep.name, ep.value),
    )


def needs_full_load(ep: EntryPoint) -> bool:
    """该 entry point 是否声明了 ``full_load`` extra。"""
    return FULL_LOAD_EXTRA in ep.extras


def deferred_entry_point_names() -> list[str]:
    """需要自举的 entry point 名称（只读元信息，不加载目标，已去重）。"""
    return sorted(
        {_normalize(ep.name) for ep in _iter_entry_points() if needs_full_load(ep)}
    )


def _bootstrap() -> None:
    """Amrita 初始化 + 插件加载，让插件包内模块可以被 import。

    与 ``ambot orm`` 内部 ``amrita.prepare_orm()`` 的前两步一致；幂等。
    """
    global _bootstrap_done
    if _bootstrap_done:
        return
    # 告知插件当前处于 `ambot <cmd>` 命令上下文（而非在跑 bot），使其跳过启动期的交互式检查。
    os.environ[COMMAND_CONTEXT_ENV] = "1"
    import amrita

    amrita.init()
    amrita.load_plugins()
    _bootstrap_done = True


def _load_deferred_target(ep: EntryPoint) -> click.Command | None:
    """自举后加载 ``full_load`` entry point 的目标，失败只告警。

    目标返回 ``None`` 表示它已自行调用 :func:`register_command`，此时按
    entry point 名取回**本次新注册**的命令。
    """
    origin = f"entry point {ep.name!r}"
    _bootstrap()
    before = dict(_registry)
    try:
        commands = _coerce_commands(ep.load(), origin)
    except Exception as exc:
        _warn(f"加载子命令 {ep.name!r} 失败：{exc}")
        return None
    if not commands:
        cmd_name = _normalize(ep.name)
        registered = _registry.get(cmd_name)
        if registered is not None and registered is not before.get(cmd_name):
            return registered
        return None
    if len(commands) > 1:
        _warn(f"{origin} 声明了 full_load，但返回多个命令，仅取第一个")
    return commands[0]


class DeferredCommand(click.Command):
    """``full_load`` entry point 的惰性代理。

    click 的 ``format_commands`` 会为每个列出的子命令调用 ``get_command``
    取短帮助，因此代理本身必须能在**不自举**的前提下被创建与展示。真正
    加载发生在 click 为该命令建立上下文时（``make_context``），也就是用户
    确实执行了 ``ambot <name> ...`` 的那一刻。
    """

    def __init__(self, name: str, entry_point: EntryPoint, help_text: str) -> None:
        super().__init__(name=name, help=help_text)
        self._entry_point = entry_point
        self._real: click.Command | None = None

    def resolve_target(self) -> click.Command:
        """自举并加载真实命令（只加载一次）。

        Raises:
            click.ClickException: 目标加载失败（插件无法启动等）。
        """
        if self._real is None:
            real = _load_deferred_target(self._entry_point)
            if real is None:
                raise click.ClickException(
                    f"子命令 {self.name!r} 加载失败，请检查插件能否正常启动"
                )
            self._real = real
        return self._real

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: click.Context | None = None,
        **extra: Any,
    ) -> click.Context:
        # 完全交给真实命令建上下文：--help、参数解析、no_args_is_help 等行为与直接注册的命令一致。
        return self.resolve_target().make_context(
            info_name, args, parent=parent, **extra
        )

    def invoke(self, ctx: click.Context) -> Any:
        # 仅在代理被当作顶层命令直接调用时走到这里。
        return self.resolve_target().invoke(ctx)


def load_deferred_entry_point_command(name: str) -> click.Command | None:
    """按名取 ``full_load`` entry point 的惰性代理（不触发自举）。

    只按 entry point 名匹配（``full_load`` 约定为单个命令）。同名 entry
    point 多于一个时，与普通 entry point 一致：按 ``(名称, 目标)`` 排序取
    先出现的一个，并往 stderr 告警。
    """
    cmd_name = _normalize(name)
    cached = _deferred_entry_point_cache.get(cmd_name)
    if cached is not None:
        return cached

    matches = [
        ep
        for ep in _iter_entry_points()
        if _normalize(ep.name) == cmd_name and needs_full_load(ep)
    ]
    if not matches:
        return None

    if len(matches) > 1:
        ignored = "、".join(repr(ep.value) for ep in matches[1:])
        _warn(f"子命令 {cmd_name!r} 有多个 full_load entry point，忽略 {ignored}")

    proxy = DeferredCommand(
        name=cmd_name,
        entry_point=matches[0],
        help_text=f"来自 {matches[0].value}（首次调用时加载插件）",
    )
    _deferred_entry_point_cache[cmd_name] = proxy
    return proxy


def load_entry_point_commands(*, force: bool = False) -> dict[str, click.Command]:
    """扫描并缓存 ``ambot.commands`` entry point 声明的子命令。

    声明了 ``full_load`` 的项不在此处加载（见
    :func:`load_deferred_entry_point_command`）。加载失败只告警并跳过，
    不会中断 CLI。
    """
    global _entry_point_cache

    if _entry_point_cache is not None and not force:
        return dict(_entry_point_cache)

    found: dict[str, click.Command] = {}

    for ep in _iter_entry_points():
        if needs_full_load(ep):
            continue
        origin = f"entry point {ep.name!r}"
        try:
            commands = _coerce_commands(ep.load(), origin)
        except Exception as exc:
            _warn(f"加载子命令 {ep.name!r} 失败：{exc}")
            continue

        if len(commands) == 1:
            _add_entry_point_command(found, _normalize(ep.name), commands[0], origin)
            continue

        for cmd in commands:
            cmd_name = _normalize(cmd.name or "")
            if cmd_name:
                _add_entry_point_command(found, cmd_name, cmd, origin)

    _entry_point_cache = found
    return dict(found)


def clear_entry_point_cache() -> None:
    """清空 entry point 缓存（测试或热加载时使用）。"""
    global _entry_point_cache
    _entry_point_cache = None
    _deferred_entry_point_cache.clear()
