from __future__ import annotations

from typing import Sequence

from snuba.datasets.entities.entity_key import EntityKey
from snuba.datasets.entities.factory import get_entity
from snuba.datasets.entity import Entity


class Dataset:
    """
    A dataset represents a data model we can run a Snuba Query on.
    A data model provides a logical schema of a graph of entities (today it is
    just a single entity, but it will soon be multiple entities).

    The class is a facade to access the components used to write on the
    data model and to query the entities.

    When processing a query, there are three main steps:
    - dataset query processing. A series of QueryProcessors are applied to the
      query before deciding which Storage to use. These processors are defined
      by the entity.
    - the Storage to run the query onto is selected and the query is transformed
      into a Clickhouse Query. This is done by a ClickhouseQueryPlanBuilder. This object
      produces a plan that includes the Query contextualized on the storage/s, the
      list of processors to apply and the strategy to run the query (in case of
      any strategy more complex than a single DB query like a split).
    - storage query processing. A second series of QueryProcessors are applied
      to the query. These are defined by the storage.

    The architecture of the Dataset is divided in two layers. The highest layer
    provides the logic we use to deal with the data model. (writers, query processors,
    query planners, etc.). The lowest layer incldues simple objects that define
    the query itself (Query, Schema, RelationalSource). The lop layer object access and
    manipulate the lower layer objects.
    """

    def __init__(self, *, all_entities: Sequence[EntityKey]) -> None:
        self.__all_entities = all_entities

    def get_all_entities(self) -> Sequence[Entity]:
        return [get_entity(entity_key) for entity_key in self.__all_entities]

    def __repr__(self) -> str:
        from snuba.datasets.factory import get_dataset_name

        return f"get_dataset({repr(get_dataset_name(self))})"
