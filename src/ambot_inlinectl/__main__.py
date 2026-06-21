import subprocess

import amrita
import click
from amrita import prepare_nb_cli, prepare_orm


@click.group()
def main():
    """Ambot Inline Control"""
    pass


@main.command("nb", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def call_nb_cli(args):
    prepare_nb_cli()(list(args))


@main.command("orm", context_settings={"ignore_unknown_options": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def call_orm_cli(args):
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


if __name__ == "__main__":
    main()
