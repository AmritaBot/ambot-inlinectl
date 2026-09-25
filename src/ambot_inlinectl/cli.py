import subprocess

import amrita
import click
from amrita import prepare_nb_cli, prepare_orm

from .group import AmbotGroup
from .registry import (
    ENTRY_POINT_GROUP,
    deferred_entry_point_names,
    load_entry_point_commands,
    overridden_commands,
    registered_commands,
)


@click.group(cls=AmbotGroup)
def main():
    """Ambot Inline Control"""
    pass


@click.group()
def plugin():
    """Manage plugins"""
    pass


@main.command("nb", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def call_nb_cli(args):
    """Execute nb-cli"""
    prepare_nb_cli()(list(args))


@main.command("orm", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def call_orm_cli(args):
    """Execute orm-cli"""
    prepare_orm()(list(args), standalone_mode=False)


@main.command("run")
def run():
    """Run the bot"""
    click.echo("Starting...")
    amrita.init()
    amrita.load_plugins()
    amrita.run()


@main.command("run_in_sub")
def run_in_sub():
    """Run the bot in a subprocess"""
    click.echo("Running in subprocess...")
    subprocess.call(["ambot", "run"])


@main.command("cmds")
def list_cmds():
    """列出所有子命令及其来源"""
    # 先加载 entry point：自行注册的命令会在这一步进入进程内注册表
    external = sorted(load_entry_point_commands())
    deferred = deferred_entry_point_names()
    builtin = sorted(name for name, cmd in main.commands.items() if not cmd.hidden)
    overrides = sorted(overridden_commands())
    registered = sorted(set(registered_commands()) - set(overrides))

    def _section(title: str, names: list[str]) -> None:
        if not names:
            return
        click.echo(click.style(f"\n{title}", fg="cyan", bold=True))
        for name in names:
            click.echo(f"  • {name}")

    _section("ambot 自带命令:", builtin)
    _section("显式覆盖:", overrides)
    _section("进程内注册:", registered)
    _section(f"entry point ({ENTRY_POINT_GROUP}):", external)
    _section("entry point (full_load，调用时自举):", deferred)

    all_names = set(builtin) | set(overrides) | set(registered) | set(external)
    all_names |= set(deferred)
    click.echo(f"\n  共 {click.style(str(len(all_names)), bold=True)} 个子命令")


@main.command("moo", hidden=True)
def moo():
    """Moo!"""
    click.echo(r"""
  ---------------------
< Ambot says: Mooooo! >
  ---------------------
         \   ^__^
          \  (oo)\_______
             (__)\       )\/\
                 ||----w |
                 ||     ||
""")


main.add_command(plugin)
