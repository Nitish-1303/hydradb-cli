"""Deprecated ``fetch`` command group — aliases for ``hydradb inspect/list/relations``.

Each command warns once and delegates to the canonical implementation.
"""

import typer

from hydradb_cli.commands import _impl
from hydradb_cli.output import warn_deprecated

app = typer.Typer(help="[dim](deprecated)[/dim] Inspect stored data — use 'hydradb inspect/list/relations'.")


@app.command()
def content(
    source_id: str = typer.Argument(help="Source ID to fetch content for."),
    tenant_id: str | None = typer.Option(None, "--tenant-id", help="Database. Uses default if not specified."),
    sub_tenant_id: str | None = typer.Option(None, "--sub-tenant-id", help="Collection."),
    mode: str = typer.Option("content", "--mode", help="Fetch mode: 'content', 'url', or 'both'."),
) -> None:
    """[dim](deprecated)[/dim] Fetch source content — use 'hydradb inspect'."""
    warn_deprecated("fetch content", "inspect")
    _impl.do_inspect(source_id, mode=mode, tenant_id=tenant_id, sub_tenant_id=sub_tenant_id)


@app.command()
def sources(
    tenant_id: str | None = typer.Option(None, "--tenant-id", help="Database. Uses default if not specified."),
    sub_tenant_id: str | None = typer.Option(None, "--sub-tenant-id", help="Collection."),
    kind: str | None = typer.Option(None, "--kind", help="Filter by kind: 'knowledge' or 'memory'."),
    page: int | None = typer.Option(None, "--page", help="Page number (1-indexed)."),
    page_size: int | None = typer.Option(None, "--page-size", help="Items per page (1-100)."),
) -> None:
    """[dim](deprecated)[/dim] List ingested sources — use 'hydradb list'."""
    warn_deprecated("fetch sources", "list")
    _impl.do_list(kind=kind, page=page, page_size=page_size, tenant_id=tenant_id, sub_tenant_id=sub_tenant_id)


@app.command()
def relations(
    source_id: str = typer.Argument(help="Source ID to fetch graph relations for."),
    tenant_id: str | None = typer.Option(None, "--tenant-id", help="Database. Uses default if not specified."),
    sub_tenant_id: str | None = typer.Option(None, "--sub-tenant-id", help="Collection."),
    is_memory: bool | None = typer.Option(
        None, "--is-memory/--is-knowledge", help="Whether the source is a memory (vs knowledge)."
    ),
    limit: int | None = typer.Option(None, "--limit", help="Maximum number of relations to return."),
) -> None:
    """[dim](deprecated)[/dim] Fetch graph relations — use 'hydradb relations'."""
    warn_deprecated("fetch relations", "relations")
    kind = None if is_memory is None else ("memory" if is_memory else "knowledge")
    _impl.do_relations(source_id, kind=kind, limit=limit, tenant_id=tenant_id, sub_tenant_id=sub_tenant_id)
