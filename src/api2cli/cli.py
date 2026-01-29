"""CLI entry point for api2cli."""

import typer
from api2cli import __version__

app = typer.Typer()


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        typer.echo(f"api2cli version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    )
):
    """Convert APIs to CLI tools."""
    pass


def cli():
    """Entry point for the CLI."""
    app()
