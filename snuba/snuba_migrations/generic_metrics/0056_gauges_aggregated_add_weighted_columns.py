from typing import Sequence

from snuba.clickhouse.columns import Column
from snuba.clusters.storage_sets import StorageSetKey
from snuba.migrations import migration, operations
from snuba.migrations.columns import MigrationModifiers
from snuba.migrations.operations import OperationTarget, SqlOperation
from snuba.utils.schemas import AggregateFunction, Float, UInt


class Migration(migration.ClickhouseNodeMigration):
    blocking = False
    local_table_name = "generic_metric_gauges_aggregated_local"
    dist_table_name = "generic_metric_gauges_aggregated_dist"
    storage_set_key = StorageSetKey.GENERIC_METRICS_GAUGES

    columns: Sequence[tuple[Column[MigrationModifiers], str | None]] = [
        (
            Column(
                "sum_weighted",
                AggregateFunction(
                    "sum",
                    [Float(64)],
                    MigrationModifiers(codecs=["ZSTD(1)"]),
                ),
            ),
            "sum",
        ),
        (
            Column(
                "count_weighted",
                AggregateFunction(
                    "sum",
                    [UInt(64)],
                    MigrationModifiers(codecs=["ZSTD(1)"]),
                ),
            ),
            "count",
        ),
    ]

    def forwards_ops(self) -> Sequence[SqlOperation]:
        return [
            operations.AddColumn(
                storage_set=self.storage_set_key,
                table_name=table_name,
                column=column,
                after=after,
                target=target,
            )
            for column, after in self.columns
            for table_name, target in [
                (self.local_table_name, OperationTarget.LOCAL),
                (self.dist_table_name, OperationTarget.DISTRIBUTED),
            ]
        ]

    def backwards_ops(self) -> Sequence[SqlOperation]:
        return [
            operations.DropColumn(
                storage_set=self.storage_set_key,
                table_name=table_name,
                column_name=column.name,
                target=target,
            )
            for column, _ in self.columns
            for table_name, target in [
                (self.dist_table_name, OperationTarget.DISTRIBUTED),
                (self.local_table_name, OperationTarget.LOCAL),
            ]
        ]
