from snuba.clickhouse.columns import UUID, Array, ColumnSet, DateTime, Float
from snuba.clickhouse.columns import SchemaModifiers as Modifiers
from snuba.clickhouse.columns import String, UInt
from snuba.clusters.storage_sets import StorageSetKey
from snuba.datasets.processors.querylog_processor import QuerylogProcessor
from snuba.datasets.schemas.tables import WritableTableSchema
from snuba.datasets.storage import WritableTableStorage
from snuba.datasets.storages.storage_key import StorageKey
from snuba.datasets.table_storage import build_kafka_stream_loader_from_settings
from snuba.utils.streams.topics import Topic

columns = ColumnSet(
    [
        ("request_id", UUID()),
        ("request_body", String()),
        ("referrer", String()),
        ("dataset", String()),
        ("projects", Array(UInt(64))),
        ("organization", UInt(64, Modifiers(nullable=True))),
        ("timestamp", DateTime()),
        ("duration_ms", UInt(32)),
        ("status", String()),
        # clickhouse_queries Nested columns.
        # This is expanded into arrays instead of being expressed as a
        # Nested column because, when adding new columns to a nested field
        # we need to provide a default for the entire array (each new column
        # is an array).
        # The same schema cannot be achieved with the Nested construct (where
        # we can only provide default for individual values), so, if we
        # use the Nested construct, this schema cannot match the one generated
        # by the migration framework (or by any ALTER statement).
        ("clickhouse_queries.sql", Array(String())),
        ("clickhouse_queries.status", Array(String())),
        ("clickhouse_queries.trace_id", Array(UUID(Modifiers(nullable=True)))),
        ("clickhouse_queries.duration_ms", Array(UInt(32))),
        ("clickhouse_queries.stats", Array(String())),
        ("clickhouse_queries.final", Array(UInt(8))),
        ("clickhouse_queries.cache_hit", Array(UInt(8))),
        ("clickhouse_queries.sample", Array(Float(32))),
        ("clickhouse_queries.max_threads", Array(UInt(8))),
        ("clickhouse_queries.num_days", Array(UInt(32))),
        ("clickhouse_queries.clickhouse_table", Array(String())),
        ("clickhouse_queries.query_id", Array(String())),
        # XXX: ``is_duplicate`` is currently not set when using the
        # ``Cache.get_readthrough`` query execution path. See GH-902.
        ("clickhouse_queries.is_duplicate", Array(UInt(8))),
        ("clickhouse_queries.consistent", Array(UInt(8))),
        ("clickhouse_queries.all_columns", Array(Array(String()))),
        ("clickhouse_queries.or_conditions", Array(UInt(8))),
        ("clickhouse_queries.where_columns", Array(Array(String()))),
        ("clickhouse_queries.where_mapping_columns", Array(Array(String()))),
        ("clickhouse_queries.groupby_columns", Array(Array(String()))),
        ("clickhouse_queries.array_join_columns", Array(Array(String()))),
    ]
)

# Note, we are using the simplified WritableTableSchema class here instead of
# the MergeTreeSchema that corresponds to the actual table engine. This is because
# the querylog table isn't generated by the old migration system.
schema = WritableTableSchema(
    columns=columns,
    local_table_name="querylog_local",
    dist_table_name="querylog_dist",
    storage_set_key=StorageSetKey.QUERYLOG,
)

storage = WritableTableStorage(
    storage_key=StorageKey.QUERYLOG,
    storage_set_key=StorageSetKey.QUERYLOG,
    schema=schema,
    query_processors=[],
    stream_loader=build_kafka_stream_loader_from_settings(
        processor=QuerylogProcessor(),
        default_topic=Topic.QUERYLOG,
    ),
)
