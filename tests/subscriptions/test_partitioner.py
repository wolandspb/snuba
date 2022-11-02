import pytest

from snuba import settings
from snuba.datasets.table_storage import KafkaTopicSpec
from snuba.subscriptions.data import SubscriptionData
from snuba.subscriptions.partitioner import TopicSubscriptionDataPartitioner
from snuba.utils.streams.topics import Topic
from tests.subscriptions import BaseSubscriptionTest
from tests.subscriptions.subscriptions_utils import create_entity_subscription

TESTS = [
    pytest.param(
        SubscriptionData(
            project_id=123,
            org_id=None,
            query="MATCH (events) SELECT count() AS count WHERE platform IN tuple('a')",
            time_window_sec=10 * 60,
            resolution_sec=60,
            entity_subscription=create_entity_subscription(),
        ),
        id="Legacy subscription",
    ),
    pytest.param(
        SubscriptionData(
            project_id=123,
            org_id=None,
            query=(
                "MATCH (events) "
                "SELECT count() AS count BY time "
                "WHERE "
                "platform IN tuple('a') "
            ),
            time_window_sec=10 * 60,
            resolution_sec=60,
            entity_subscription=create_entity_subscription(),
        ),
        id="SnQL subscription",
    ),
]


class TestBuildRequest(BaseSubscriptionTest):
    @pytest.mark.parametrize("subscription", TESTS)
    def test(self, subscription: SubscriptionData) -> None:
        settings.TOPIC_PARTITION_COUNTS = {"events": 64}
        partitioner = TopicSubscriptionDataPartitioner(KafkaTopicSpec(Topic.EVENTS))

        assert partitioner.build_partition_id(subscription) == 18
