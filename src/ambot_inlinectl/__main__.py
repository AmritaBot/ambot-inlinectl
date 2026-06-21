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


if __name__ == "__main__":
    main()
