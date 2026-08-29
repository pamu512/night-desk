from __future__ import annotations

from nightdesk import config
from nightdesk.models import Rails


def assess_rails(*, pubsub_up: bool, gemini_up: bool | None = None) -> Rails:
    gemini = config.has_gemini() if gemini_up is None else gemini_up
    vertex_up = bool(config.USE_VERTEX and gemini)
    return Rails(
        gemini=gemini and not config.USE_VERTEX,
        vertex=vertex_up,
        pubsub=pubsub_up,
        use_vertex=config.USE_VERTEX,
    )
