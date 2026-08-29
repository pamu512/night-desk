from __future__ import annotations

import uvicorn

from nightdesk import config

if __name__ == "__main__":
    uvicorn.run(
        "nightdesk.api:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
    )
