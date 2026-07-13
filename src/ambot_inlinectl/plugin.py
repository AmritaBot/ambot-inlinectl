from importlib.metadata import distributions
from pathlib import Path

import click
import tomlkit
from amctl.uv_util import UvOperator

from .cli import plugin

#  helpers: pyproject.toml


def _find_pyproject(start_dir: Path | None = None) -> Path | None:
    """向上查找 ``pyproject.toml``。"""
    current = Path.cwd() if start_dir is None else start_dir.resolve()
    while True:
        candidate = current / "pyproject.toml"
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _modify_tool_amrita_plugins(package: str, *, remove: bool = False) -> bool:
    """在 ``[tool.amrita.plugins]`` 中添加或移除一个插件条目。

    使用 ``tomlkit`` 以保留原有格式和注释。

    Returns:
        ``True`` 表示实际发生了修改，``False`` 表示无需修改。
    """
    pp = _find_pyproject()
    if pp is None:
        raise click.ClickException("未找到 pyproject.toml")

    doc = tomlkit.parse(pp.read_text(encoding="utf-8"))
    package = package.replace("-", "_").lower()

    # 确保 [tool] 和 [tool.amrita] 存在
    tool = doc.setdefault("tool", tomlkit.table())
    amrita_section = tool.setdefault("amrita", tomlkit.table())
    plugins = amrita_section.setdefault("plugins", tomlkit.array())

    # 转换为多行数组格式以保持美观
    if hasattr(plugins, "multiline"):
        plugins.multiline(True)

    if remove:
        if package in plugins:
            # tomlkit 的 Array 没有直接 remove 值的方法，构造新列表
            new_arr = tomlkit.array()
            new_arr.multiline(True)
            for item in plugins:
                if str(item).strip('"') != package:
                    new_arr.append(item)
            amrita_section["plugins"] = new_arr
            pp.write_text(tomlkit.dumps(doc), encoding="utf-8")
            return True
        return False
    else:
        if package not in plugins:
            plugins.append(package)
            pp.write_text(tomlkit.dumps(doc), encoding="utf-8")
            return True
        return False


#  helpers: plugin discovery


def _get_installed_plugins(prefix: str) -> list[tuple[str, str]]:
    """获取以指定前缀开头的 pip 安装包。"""
    result = []
    for dist in distributions():
        name = dist.metadata["Name"]
        if name.startswith(prefix):
            result.append((name, dist.version))
    return sorted(result)


def _get_directory_plugins(dir_path: Path) -> list[str]:
    """扫描目录下的插件子目录（排除以 _ 或 . 开头的目录）。"""
    if not dir_path.exists() or not dir_path.is_dir():
        return []
    result = [
        entry.name
        for entry in dir_path.iterdir()
        if entry.is_dir()
        and not entry.name.startswith("_")
        and not entry.name.startswith(".")
    ]
    return sorted(result)


#  commands


@plugin.command("list")
def list_plugins():
    """嗅探并列出环境内所有已安装的插件

    包括:
    - amrita_plugin_* (pip 安装的 Amrita 插件)
    - nonebot_plugin_* (pip 安装的 NoneBot 插件)
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
