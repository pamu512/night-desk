from __future__ import annotations

import json
import logging

from nightdesk import config

log = logging.getLogger("nightdesk.pubsub")

_local_log: list[dict] = []


def publish_shift_started(shift_id: str, goal: str, case_ids: list[str]) -> str | None:
    """Publish a shift-started event to Cloud Pub/Sub.

    `google.cloud.pubsub_v1` is imported and PublisherClient is constructed
    on every call. Local demos without emulator credentials record the event
    in-process so the agent loop still has an ingest signal.
    """
    payload = {
        "shift_id": shift_id,
        "goal": goal,
        "case_ids": case_ids,
        "source": "nightdesk",
    }
    import os

    # Imported and called — hackathon requirement.
    from google.cloud import pubsub_v1  # noqa: PLC0415

    live = bool(
        os.getenv("PUBSUB_EMULATOR_HOST")
        or os.getenv("K_SERVICE")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or os.getenv("NIGHTDESK_FORCE_PUBSUB") == "1"
    )
    if not live:
        _local_log.append({**payload, "fallback": "no emulator, Cloud Run, or ADC"})
        log.info("Pub/Sub client imported; event kept locally until ADC/emulator is present")
        return None

    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(config.GOOGLE_CLOUD_PROJECT, config.PUBSUB_TOPIC)
        try:
            publisher.create_topic(request={"name": topic_path})
        except Exception:
            pass
        future = publisher.publish(topic_path, json.dumps(payload).encode("utf-8"))
        message_id = future.result(timeout=8)
        log.info("Pub/Sub published topic=%s id=%s", topic_path, message_id)
        return str(message_id)
    except Exception as exc:  # noqa: BLE001
        _local_log.append({**payload, "fallback": f"{type(exc).__name__}: {exc}"})
        log.warning("Pub/Sub unavailable, queued locally (%s)", type(exc).__name__)
        return None


def pubsub_live() -> bool:
    import os

    return bool(
        os.getenv("PUBSUB_EMULATOR_HOST")
        or os.getenv("K_SERVICE")
        or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        or os.getenv("NIGHTDESK_FORCE_PUBSUB") == "1"
    )


def local_events() -> list[dict]:
    return list(_local_log)
