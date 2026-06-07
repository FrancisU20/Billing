"""Implementación SQS del puerto EventPublisherPort."""
from __future__ import annotations

from lambdas.workers.tenant_onboarding.ports import EventPublisherPort
from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.publisher import EventPublisher


class SQSEventPublisher(EventPublisherPort):
    def __init__(self, queue_url: str) -> None:
        self._publisher = EventPublisher(queue_url=queue_url)

    def publish(self, event: DomainEvent) -> None:
        self._publisher.publish(event)
