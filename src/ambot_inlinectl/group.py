"""ambot 根命令使用的惰性 click Group。"""

from __future__ import annotations

import click

from .registry import (
    load_entry_point_commands,
    overridden_commands,
    registered_commands,
)


def _swap_separators(name: str) -> str:
    """把命令名里的连字符与下划线互换。

    click 对自动推导出的命令名会把下划线转成连字符，而显式指定的名字
    原样保留。这里做一次兜底，让 ``ambot run-in-sub`` 与
    ``ambot run_in_sub`` 都能命中同一个命令。
    """
    if "-" in name:
        return name.replace("-", "_")
    return name.replace("_", "-")


class AmbotGroup(click.Group):
    """惰性解析子命令的 click Group。

    查找顺序：

    1. 以 ``replace=True`` 注册、显式声明覆盖的子命令
    2. ambot 自带命令
    3. 进程内注册的子命令
    4. ``ambot.commands`` entry point 声明的子命令

    自带命令优先于普通注册，避免插件无意间顶掉 ``run`` 之类的核心命令；
    确实需要覆盖时显式传 ``replace=True``。
    """

    def _resolve(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        cmd = overridden_commands().get(cmd_name)
        if cmd is not None:
            return cmd

        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        cmd = registered_commands().get(cmd_name)
        if cmd is not None:
            return cmd

        return load_entry_point_commands().get(cmd_name)

    def list_commands(self, ctx: click.Context) -> list[str]:
        names = set(overridden_commands())
        names.update(super().list_commands(ctx))
        names.update(registered_commands())
        names.update(load_entry_point_commands())
        return sorted(names)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        cmd = self._resolve(ctx, cmd_name)
        if cmd is None:
            cmd = self._resolve(ctx, _swap_separators(cmd_name))
        return cmd
