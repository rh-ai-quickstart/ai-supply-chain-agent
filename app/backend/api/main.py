"""Process entry point: load Settings, build the app via the composition root, run it.

All routing/business logic lives in ``routes/*`` (blueprints), ``container.py``
(composition root), and ``services``/``clients``. See ``app_factory.py``.
"""

import logging

from app_factory import create_app
from settings import Settings

logging.basicConfig(level=logging.INFO)

settings = Settings.from_env()
app = create_app(settings)
container = app.container

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=settings.flask_debug, threaded=True)
