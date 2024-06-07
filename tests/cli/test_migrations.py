from typing import Optional, Sequence

import pytest
from click import Command
from click.testing import CliRunner

from snuba.cli.migrations import list, migrate, reverse, reverse_in_progress, run


def _check_run(
    runner: CliRunner, func: Command, args: Optional[Sequence[str]] = None
) -> None:
    result = runner.invoke(func, args)
    assert result.exit_code == 0, (func, args)


@pytest.mark.clickhouse_db(storage_keys=["trustme"])
def test_migrations_cli() -> None:
    runner = CliRunner()
    # test different combinations of arguments
    _check_run(runner, list)
    _check_run(runner, migrate, ["--force"])
    _check_run(runner, migrate, ["-g", "system", "--force"])
    _check_run(runner, migrate, ["--group", "system", "--force"])
    _check_run(
        runner,
        run,
        [
            "--force",
            "--dry-run",
            "--group",
            "system",
            "--migration-id",
            "0001_migrations",
        ],
    )
    _check_run(
        runner,
        reverse,
        [
            "--force",
            "--dry-run",
            "--group",
            "system",
            "--migration-id",
            "0001_migrations",
        ],
    )
    _check_run(runner, reverse_in_progress, ["--group", "system"])
    _check_run(runner, reverse_in_progress)
    _check_run(runner, migrate, ["--group", "system", "--check-dangerous"])
