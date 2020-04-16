from typing import Optional, Sequence

from snuba.datasets.plans.query_plan import (
    QueryPlanExecutionStrategy,
    QueryRunner,
    StorageQueryPlan,
    StorageQueryPlanBuilder,
)
from snuba.datasets.storage import QueryStorageSelector, ReadableStorage
from snuba.datasets.plans.translators import CopyTranslator

# TODO: Importing snuba.web here is just wrong. What's need to be done to avoid this
# dependency is a refactoring of the methods that return RawQueryResult to make them
# depend on Result + some debug data structure instead. Also It requires removing
# extra data from the result of the query.
from snuba.web import RawQueryResult
from snuba.query.physical import PhysicalQuery
from snuba.query.query_processor import PhysicalQueryProcessor
from snuba.request import Request
from snuba.request.request_settings import RequestSettings


class SimpleQueryPlanExecutionStrategy(QueryPlanExecutionStrategy):
    def execute(
        self,
        query: PhysicalQuery,
        request_settings: RequestSettings,
        runner: QueryRunner,
    ) -> RawQueryResult:
        return runner(query, request_settings)


class SingleStorageQueryPlanBuilder(StorageQueryPlanBuilder):
    """
    Builds the Storage Query Execution Plan for a dataset that is based on
    a single storage.
    """

    def __init__(
        self,
        storage: ReadableStorage,
        post_processors: Optional[Sequence[PhysicalQueryProcessor]] = None,
    ) -> None:
        # The storage the query is based on
        self.__storage = storage
        # This is a set of query processors that have to be executed on the
        # query after the storage selection but that are defined by the dataset.
        # Query processors defined by a Storage must be executable independently
        # from the context the Storage is used (whether the storage is used by
        # itself or whether it is joined with another storage).
        # In a joined query we would have processors defined by multiple storages.
        # that would have to be executed only once (like Prewhere). That is a
        # candidate to be added here as post process.
        self.__post_processors = post_processors or []

    def build_plan(self, request: Request) -> StorageQueryPlan:
        # TODO: Clearly the QueryTranslator instance  will be dependent on the storage.
        # Setting the data_source on the query should become part of the translation
        # as well.
        physical_query = CopyTranslator().translate(request.query)
        physical_query.set_data_source(
            self.__storage.get_schemas().get_read_schema().get_data_source()
        )

        return StorageQueryPlan(
            query=physical_query,
            query_processors=[
                *self.__storage.get_query_processors(),
                *self.__post_processors,
            ],
            execution_strategy=SimpleQueryPlanExecutionStrategy(),
        )


class SelectedStorageQueryPlanBuilder(StorageQueryPlanBuilder):
    """
    A query plan builder that selects one of multiple storages in the
    dataset.
    """

    def __init__(
        self,
        selector: QueryStorageSelector,
        post_processors: Optional[Sequence[PhysicalQueryProcessor]] = None,
    ) -> None:
        self.__selector = selector
        self.__post_processors = post_processors or []

    def build_plan(self, request: Request) -> StorageQueryPlan:
        storage = self.__selector.select_storage(request.query, request.settings)
        # TODO: Same as for SingleStorageQueryPlanBuilder. The instance of the translator
        # depends on the storage. This dependency will be added in a followup. Also
        # this code is likely to change with multi-table storages, but it will take a while
        # to get there.
        physical_query = CopyTranslator().translate(request.query)
        physical_query.set_data_source(
            storage.get_schemas().get_read_schema().get_data_source()
        )

        return StorageQueryPlan(
            query=physical_query,
            query_processors=[
                *storage.get_query_processors(),
                *self.__post_processors,
            ],
            execution_strategy=SimpleQueryPlanExecutionStrategy(),
        )
