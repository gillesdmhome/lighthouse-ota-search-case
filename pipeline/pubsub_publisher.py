"""Optional Pub/Sub publisher with local fallback."""

from __future__ import annotations

import json
import logging

from pipeline.config import settings

logger = logging.getLogger(__name__)


def publish_event(payload: dict, attributes: dict[str, str]) -> str | None:
    """Publish to Pub/Sub if configured; otherwise no-op (bronze_store handles local)."""
    if not settings.pubsub_topic or not settings.gcp_project_id:
        return None

    try:
        from google.cloud import pubsub_v1

        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(settings.gcp_project_id, settings.pubsub_topic)
        future = publisher.publish(
            topic_path,
            json.dumps(payload).encode("utf-8"),
            **attributes,
        )
        message_id = future.result(timeout=10)
        logger.info("Published to Pub/Sub: %s", message_id)
        return message_id
    except Exception as exc:
        logger.warning("Pub/Sub publish failed (local bronze still written): %s", exc)
        return None
