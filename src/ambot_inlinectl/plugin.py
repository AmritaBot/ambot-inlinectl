from pathlib import Path

import click
from amctl.uv_util import UvOperator

from ._compat import (
    PyprojectNotFoundError,
    find_pyproject,
    iter_dir_plugins,
    iter_dist_plugins,
    modify_plugin_list,
)
from .cli import plugin

#  helpers: pyproject.toml


def _find_pyproject(start_dir: Path | None = None) -> Path | None:
    """向上查找 ``pyproject.toml``。

    实现已下沉到 ``amrita.utils.pyproject_io``，CLI 与 WebUI 共用一份。
    """
    return find_pyproject(start_dir)


def _modify_tool_amrita_plugins(package: str, *, remove: bool = False) -> bool:
    """在 ``[tool.amrita.plugins]`` 中添加或移除一个插件条目。

    实现同样在 ``amrita.utils.pyproject_io``；这里只把中性异常转回
    ``click.ClickException``，保持 CLI 的报错文案与退出码不变。

    Returns:
        ``True`` 表示实际发生了修改，``False`` 表示无需修改。
    """
    try:
        return modify_plugin_list(package, target="amrita", remove=remove)
    except PyprojectNotFoundError as e:
        raise click.ClickException("未找到 pyproject.toml") from e


#  helpers: plugin discovery


def _get_installed_plugins(prefix: str) -> list[tuple[str, str]]:
    """获取以指定前缀开头的 pip 安装包。"""
    return iter_dist_plugins(prefix)


def _get_directory_plugins(dir_path: Path) -> list[str]:
    """扫描目录下的插件子目录（排除以 _ 或 . 开头的目录）。"""
    return iter_dir_plugins(dir_path)


#  commands


@plugin.command("list")
def list_plugins():
    """嗅探并列出环境内所有已安装的插件

    包括:
    - amrita_plugin_* (pip 安装的 Amrita 插件)
    - nonebot_plugin_* (pip 装的 NoneBot 插件)
    - plugins/ 目录 (本地 Amrita 插件)
    - src/plugins/ 目录 (本地 NoneBot 插件)
    """
    # 1. amrita_plugin_* (Amrita 插件 - pip)
    amrita_pkg = _get_installed_plugins("amrita_plugin_")

    # 2. nonebot_plugin_* (NoneBot 插件 - pip)
    nonebot_pkg = _get_installed_plugins("nonebot_plugin_")

    # 3. plugins/ 目录 (Amrita 插件 - 本地)
    amrita_dir = _get_directory_plugins(Path("plugins"))

    # 4. src/plugins/ 目录 (NoneBot 插件 - 本地)
    nonebot_dir = _get_directory_plugins(Path("src/plugins"))

    total = len(amrita_pkg) + len(amrita_dir) + len(nonebot_pkg) + len(nonebot_dir)
    if total == 0:
        click.echo(click.style("未发现任何插件。", fg="yellow"))
    else:
        # Amrita 插件 — pip
        if amrita_pkg:
            click.echo(click.style("\n📦 Amrita 插件 (pip):", fg="cyan", bold=True))
            for name, version in amrita_pkg:
                click.echo(
                    f"  • {name}  {click.style('v' + version, fg='bright_black')}"
                )

        # Amrita 插件 — plugins/
        if amrita_dir:
            click.echo(
                click.style("\n📁 Amrita 插件 (plugins/):", fg="cyan", bold=True)
            )
            for name in amrita_dir:
                click.echo(f"  • {name}")

        # NoneBot 插件 — pip
        if nonebot_pkg:
            click.echo(click.style("\n📦 NoneBot 插件 (pip):", fg="green", bold=True))
            for name, version in nonebot_pkg:
                click.echo(
                    f"  • {name}  {click.style('v' + version, fg='bright_black')}"
                )

        # NoneBot 插件 — src/plugins/
        if nonebot_dir:
            click.echo(
                click.style("\n📁 NoneBot 插件 (src/plugins/):", fg="green", bold=True)
            )
            for name in nonebot_dir:
                click.echo(f"  • {name}")

        click.echo(f"\n{'' * 58}")
        click.echo(f"  共 {click.style(str(total), bold=True)} 个插件")


@plugin.command("add")
@click.argument("package")
def plugin_add(package: str):
    """安装插件并注册到 [tool.amrita.plugins]

    - 调用 uv add 安装包
    - 将包名写入 pyproject.toml 的 [tool.amrita.plugins] 列表
    """
    uv = UvOperator()
    try:
        click.echo(f"正在安装 {package} ...")
        output = uv.add(package)
        click.echo(output, nl=False)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e

    try:
        _modify_tool_amrita_plugins(package)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"修改 pyproject.toml 失败: {e}") from e


@plugin.command("remove")
@click.argument("package")
def plugin_remove(package: str):
    """卸载插件并从 [tool.amrita.plugins] 移除

    - 调用 uv remove 卸载包
    - 将包名从 pyproject.toml 的 [tool.amrita.plugins] 列表中移除
    """
    uv = UvOperator()
    try:
        click.echo(f"正在卸载 {package} ...")
        output = uv.remove(package)
        click.echo(output, nl=False)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e

    try:
        _modify_tool_amrita_plugins(package, remove=True)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"修改 pyproject.toml 失败: {e}") from e
