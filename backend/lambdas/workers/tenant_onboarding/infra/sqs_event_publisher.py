from __future__ import annotations

"""Adapter: bridges EventPublisher (shared) → EventPublisherPort (tenant_onboarding domain)."""

from lambdas.workers.tenant_onboarding.ports import EventPublisherPort
from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.publisher import DirectPublishReason, EventPublisher


class SQSEventPublisher(EventPublisherPort):
    """
    Adapts shared.EventPublisher to the tenant_onboarding EventPublisherPort ABC.
    Keeps the handler decoupled from the concrete SQS implementation.
    """

    def __init__(self, queue_url: str) -> None:
        self._publisher = EventPublisher(
            queue_url=queue_url,
            reason=DirectPublishReason.POST_COMMIT_WORKER_SIDE_EFFECT,
        )

    def publish(self, event: DomainEvent) -> None:
        self._publisher.publish(event)
