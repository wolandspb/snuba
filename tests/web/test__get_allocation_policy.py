from __future__ import annotations

from datetime import datetime
from typing import Union
from unittest import mock

import pytest

from snuba.attribution.appid import AppID
from snuba.attribution.attribution_info import AttributionInfo
from snuba.clickhouse.formatter.query import format_query
from snuba.clickhouse.query import Query as ClickhouseQuery
from snuba.datasets.entities.entity_key import EntityKey
from snuba.datasets.entities.factory import get_entity
from snuba.datasets.storages.factory import get_storage
from snuba.datasets.storages.storage_key import StorageKey
from snuba.query import SelectedExpression
from snuba.query.allocation_policies import (
    DEFAULT_PASSTHROUGH_POLICY,
    AllocationPolicy,
    PassthroughPolicy,
)
from snuba.query.composite import CompositeQuery
from snuba.query.conditions import ConditionFunctions, binary_condition
from snuba.query.data_source.join import JoinClause
from snuba.query.data_source.simple import Table
from snuba.query.expressions import Column, FunctionCall, Literal
from snuba.query.query_settings import HTTPQuerySettings
from snuba.utils.metrics.timer import Timer
from snuba.web.db_query_class import DBQuery

events_storage = get_entity(EntityKey.EVENTS).get_writable_storage()
assert events_storage is not None
events_table_name = events_storage.get_table_writer().get_schema().get_table_name()


events_table = Table(
    events_table_name,
    events_storage.get_schema().get_columns(),
    allocation_policies=[PassthroughPolicy(StorageKey("flimflam"), [], {})],
    final=False,
    sampling_rate=None,
    mandatory_conditions=events_storage.get_schema()
    .get_data_source()
    .get_mandatory_conditions(),
)

composite_query = CompositeQuery(
    from_clause=ClickhouseQuery(
        from_clause=events_table,
        selected_columns=[
            SelectedExpression("project_id", Column(None, None, "project_id")),
        ],
        groupby=[Column(None, None, "project_id")],
        condition=binary_condition(
            ConditionFunctions.GTE,
            Column(None, None, "timestamp"),
            Literal(None, datetime(2020, 1, 1, 12, 0)),
        ),
    ),
    selected_columns=[
        SelectedExpression(
            "average",
            FunctionCall("average", "avg", (Column(None, None, "project_id"),)),
        ),
    ],
)


class BadJoinClause(JoinClause[Table]):
    # the join clause functionality is not supported,
    # doesn't matter that the join clause is not valid
    # if we support join clauses + allocation_policies
    # we can remove this
    def __post_init__(self) -> None:
        pass


join_query = CompositeQuery(
    from_clause=BadJoinClause(
        left_node=mock.Mock(),
        right_node=mock.Mock(),
        keys=[mock.Mock()],
        join_type=mock.Mock(),
    ),
    selected_columns=[],
)


@pytest.mark.parametrize(
    "query,expected_allocation_policies",
    [
        pytest.param(
            composite_query,
            [PassthroughPolicy(StorageKey("flimflam"), [], {})],
            id="composite query uses leaf query's allocation policy",
        ),
        pytest.param(
            CompositeQuery(
                from_clause=composite_query,
                selected_columns=[
                    SelectedExpression(
                        "average",
                        FunctionCall(
                            "average", "avg", (Column(None, None, "project_id"),)
                        ),
                    ),
                ],
            ),
            [PassthroughPolicy(StorageKey("flimflam"), [], {})],
            id="double nested composite query uses leaf query's allocation policy",
        ),
        pytest.param(
            join_query,
            [DEFAULT_PASSTHROUGH_POLICY],
            id="Joins just pass through (this is a hack)",
        ),
        pytest.param(
            ClickhouseQuery(
                from_clause=events_table,
                selected_columns=[
                    SelectedExpression("project_id", Column(None, None, "project_id")),
                ],
                groupby=[Column(None, None, "project_id")],
                condition=binary_condition(
                    ConditionFunctions.GTE,
                    Column(None, None, "timestamp"),
                    Literal(None, datetime(2020, 1, 1, 12, 0)),
                ),
            ),
            [PassthroughPolicy(StorageKey("flimflam"), [], {})],
            id="simple query uses table's allocation policy",
        ),
    ],
)
@pytest.mark.clickhouse_db
def test__get_allocation_policies(
    query: Union[ClickhouseQuery, CompositeQuery[Table]],
    expected_allocation_policies: list[AllocationPolicy],
) -> None:
    obj = DBQuery(
        clickhouse_query=query,
        query_settings=HTTPQuerySettings(),
        attribution_info=AttributionInfo(
            app_id=AppID(key="key"),
            tenant_ids={"referrer": "something", "organization_id": 1234},
            referrer="something",
            team=None,
            feature=None,
            parent_api=None,
        ),
        dataset_name="",
        query_metadata_list=[],
        formatted_query=format_query(query),
        reader=get_storage(StorageKey("errors_ro")).get_cluster().get_reader(),
        timer=Timer("foo"),
        stats={},
    )
    obj._load_allocation_policies()
    assert obj.allocation_policies == expected_allocation_policies
