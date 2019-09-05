from batching_kafka_consumer import BatchingKafkaConsumer
from typing import Optional, Sequence

from snuba.consumers.consumer_builder import ConsumerBuilder
from snuba.stateful_consumer import ConsumerStateData, ConsumerStateCompletionEvent
from snuba.utils.state_machine import State, StateType, StateMachine
from snuba.stateful_consumer.states.bootstrap import BootstrapState
from snuba.stateful_consumer.states.consuming import ConsumingState
from snuba.stateful_consumer.states.paused import PausedState
from snuba.stateful_consumer.states.catching_up import CatchingUpState


class ConsumerStateMachine(StateMachine[ConsumerStateCompletionEvent, Optional[ConsumerStateData]]):
    """
    Context class for the stateful consumer. The states defined here
    regulate when the consumer is consuming from the main topic and when
    it is consuming from the control topic.
    """

    def __init__(
        self,
        consumer_builder: ConsumerBuilder,
        topic: str,
        bootstrap_servers: Sequence[str],
        group_id: str,
    ) -> None:
        self.__consumer_builder = consumer_builder
        self.__topic = topic
        self.__bootstrap_servers = bootstrap_servers
        self.__group_id = group_id

        super(ConsumerStateMachine, self).__init__(
            definition={
                BootstrapState: {
                    ConsumerStateCompletionEvent.NO_SNAPSHOT: ConsumingState,
                    ConsumerStateCompletionEvent.SNAPSHOT_INIT_RECEIVED: PausedState,
                    ConsumerStateCompletionEvent.SNAPSHOT_READY_RECEIVED: CatchingUpState,
                },
                ConsumingState: {
                    ConsumerStateCompletionEvent.CONSUMPTION_COMPLETED: None,
                    ConsumerStateCompletionEvent.SNAPSHOT_INIT_RECEIVED: PausedState,
                },
                PausedState: {
                    ConsumerStateCompletionEvent.CONSUMPTION_COMPLETED: None,
                    ConsumerStateCompletionEvent.SNAPSHOT_READY_RECEIVED: CatchingUpState,
                },
                CatchingUpState: {
                    ConsumerStateCompletionEvent.CONSUMPTION_COMPLETED: None,
                    ConsumerStateCompletionEvent.SNAPSHOT_CATCHUP_COMPLETED: ConsumingState,
                },
            },
            start_state=BootstrapState,
        )

    def _build_state(
        self,
        state_class: StateType,
    ) -> State[ConsumerStateCompletionEvent, ConsumerStateData]:
        if state_class == ConsumingState:
            return ConsumingState(
                self.__consumer_builder,
            )
        elif state_class == BootstrapState:
            return BootstrapState(
                topic=self.__topic,
                bootstrap_servers=self.__bootstrap_servers,
                group_id=self.__group_id,
            )
        elif state_class == CatchingUpState:
            return CatchingUpState(
                self.__consumer_builder,
            )
        else:
            return state_class()
