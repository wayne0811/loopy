"""CLI interface for Loopy."""

import sys
import signal
import logging
import click
from .loop import Loop
from .models import ItemStatus

logging.basicConfig()


def handler(signum, frame):
    match signum:
        case signal.SIGTERM:
            sys.exit(1)


signal.signal(signal.SIGTERM, handler)


@click.group(invoke_without_command=True)
@click.option("--id", "loop_id", envvar="LOOPY_ID", help="Loop identifier")
@click.option("--db", "db_path", envvar="LOOPY_DB", help="Database path")
@click.pass_context
def main(ctx, loop_id, db_path):
    """Run commands in a persistent, durable loop."""
    ctx.ensure_object(dict)
    ctx.obj["loop_id"] = loop_id
    ctx.obj["db_path"] = db_path

    # Validate --id is required for commands that need it
    if ctx.invoked_subcommand in [
        "create",
        "run",
        "reset",
        "delete",
        "cmd",
        "copy-from",
        "read-items",
        "list-items",
        "edit-items",
    ]:
        if not loop_id:
            click.echo(f"Loop ID required for {ctx.invoked_subcommand} command")
            sys.exit(1)

    # Validate loop exists for commands that need it (except create which creates)
    if ctx.invoked_subcommand in [
        "run",
        "reset",
        "delete",
        "cmd",
        "read-items",
        "list-items",
        "edit-items",
    ]:
        loop = Loop(loop_id, db_path=db_path)
        if not loop.exists():
            click.echo(f"Loop {loop_id} not found")
            sys.exit(1)

    # If no subcommand, default to list
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_)


@main.command()
@click.argument("command", nargs=-1, required=True)
@click.pass_context
def create(ctx, command):
    """Create a new loop."""
    loop_id = ctx.obj["loop_id"]

    if "{}" not in command:
        command = list(command) + ["{}"]
    cmd_str = " ".join(command)

    # Read items from stdin
    click.echo("Reading items from standard input", err=True)
    items = [line.strip() for line in sys.stdin if line.strip()]

    try:
        Loop.create(loop_id, cmd_str, items, db_path=ctx.obj["db_path"])
        click.echo(f"Loop {loop_id} created")
    except ValueError as e:
        click.echo(str(e))
        sys.exit(1)


@main.command()
@click.option(
    "--continue-on-failure", is_flag=True, help="Continue processing even if items fail"
)
@click.pass_context
def run(ctx, continue_on_failure):
    """Run an existing loop."""
    loop_id = ctx.obj["loop_id"]

    loop = Loop(loop_id, db_path=ctx.obj["db_path"])
    success = loop.run(continue_on_failure)
    sys.exit(0 if success else 1)


@main.command()
@click.pass_context
def reset(ctx):
    """Reset loop to start from beginning."""
    loop_id = ctx.obj["loop_id"]

    loop = Loop(loop_id, db_path=ctx.obj["db_path"])
    loop.reset()
    click.echo(f"Loop {loop_id} reset")


@main.command()
@click.pass_context
def delete(ctx):
    """Delete a loop."""
    loop_id = ctx.obj["loop_id"]

    loop = Loop(loop_id, db_path=ctx.obj["db_path"])
    loop.delete()
    click.echo(f"Loop {loop_id} deleted")


@main.command(name="edit-cmd")
@click.argument("command", nargs=-1, required=True)
@click.pass_context
def cmd(ctx, command):
    """Update loop command."""
    loop_id = ctx.obj["loop_id"]

    if "{}" not in command:
        command = list(command) + ["{}"]
    cmd_str = " ".join(command)
    loop = Loop(loop_id, db_path=ctx.obj["db_path"])
    loop.update_command(cmd_str)
    click.echo(f"Loop {loop_id} command updated")


@main.command("copy-from")
@click.argument("source_id")
@click.pass_context
def copy_from(ctx, source_id):
    """Copy from another loop."""
    loop_id = ctx.obj["loop_id"]

    source_loop = Loop(source_id, db_path=ctx.obj["db_path"])

    if not source_loop.exists():
        click.echo(f"Source loop {source_id} not found")
        sys.exit(1)

    source_loop.copy_to(loop_id)
    click.echo(f"Loop {source_id} copied to {loop_id}")


@main.command("read-items")
@click.option("--append", is_flag=True, help="Append items to existing loop items")
@click.option("--replace", is_flag=True, help="Replace all loop items")
@click.pass_context
def read_items(ctx, append, replace):
    """Read items from stdin and add to loop."""
    if append and replace:
        click.echo("--append and --replace are mutually exclusive")
        sys.exit(1)

    if not append and not replace:
        click.echo("Either --append or --replace must be specified")
        sys.exit(1)

    loop_id = ctx.obj["loop_id"]

    # Read items from stdin
    items = [line.strip() for line in sys.stdin if line.strip()]

    if not items:
        click.echo("No items provided via stdin")
        sys.exit(1)

    loop = Loop(loop_id, db_path=ctx.obj["db_path"])

    if replace:
        loop.replace_items(items)
        click.echo(f"Replaced items in loop {loop_id}")
    else:
        loop.add_items(items)
        click.echo(f"Added items to loop {loop_id}")


@main.command("edit-items")
@click.pass_context
def edit_items(ctx):
    """Edit loop items in a text editor."""
    loop_id = ctx.obj["loop_id"]
    loop = Loop(loop_id, db_path=ctx.obj["db_path"])

    # Get current items
    current_items = loop.list_items()
    initial_text = "\n".join([item for item, _, _ in current_items])

    # Open editor
    edited_text = click.edit(initial_text)

    if edited_text is None:
        click.echo("Edit cancelled")
        return

    # Parse edited items
    new_items = [
        line.strip() for line in edited_text.strip().split("\n") if line.strip()
    ]

    # Replace items
    loop.replace_items(new_items)
    click.echo(f"Updated items in loop {loop_id}")


@main.command("list-items")
@click.option("--raw", is_flag=True, help="Print only item names without status")
@click.pass_context
def list_items(ctx, raw):
    """List items in a loop."""
    loop_id = ctx.obj["loop_id"]
    loop = Loop(loop_id, db_path=ctx.obj["db_path"])
    items = loop.list_items()

    if not items:
        click.echo("No items found", err=True)
        return

    for item, status, attempts in items:
        if raw:
            click.echo(item)
        elif status == ItemStatus.PENDING:
            click.echo(f"  {item}")
        elif status == ItemStatus.SUCCESS:
            click.echo(f"✓ {item}")
        else:
            click.echo(f"✗ {item} (failed {attempts} times)")


@main.command()
@click.pass_context
def clean(ctx):
    """Remove loops where all items are completed."""
    loops = Loop.list_all(db_path=ctx.obj["db_path"])
    cleaned_count = 0

    for loop_id, command, status, pending, failed, done, total in loops:
        if total > 0 and pending == 0 and failed == 0:
            loop = Loop(loop_id, db_path=ctx.obj["db_path"])
            loop.delete()
            click.echo(f"Cleaned loop {loop_id}")
            cleaned_count += 1

    if cleaned_count == 0:
        click.echo("No completed loops to clean")
    else:
        click.echo(f"Cleaned {cleaned_count} completed loops")


@main.command(name="list")
@click.pass_context
def list_(ctx):
    """List all loops."""
    loops = Loop.list_all(db_path=ctx.obj["db_path"])

    if not loops:
        click.echo("No loops found")
        return

    for loop_id, command, status, pending, failed, done, total in loops:
        click.echo(f"{loop_id}: {command} ({pending}/{failed}/{done}/{total})")


if __name__ == "__main__":
    main()
