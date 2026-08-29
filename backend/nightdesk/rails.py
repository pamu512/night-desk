from __future__ import annotations

from nightdesk import config
from nightdesk.models import Rails


def assess_rails(*, pubsub_up: bool, gemini_up: bool | None = None) -> Rails:
    vertex_on = config.use_vertex()
    live = config.has_gemini() if gemini_up is None else gemini_up
    return Rails(
        gemini=live and not vertex_on,
        vertex=live and vertex_on,
        pubsub=pubsub_up,
        use_vertex=vertex_on,
    )
