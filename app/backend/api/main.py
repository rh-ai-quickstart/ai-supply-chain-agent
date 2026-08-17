"""Process entry point: load Settings, build the app via the composition root, run it.

All routing/business logic lives in ``routes/*`` (blueprints), ``container.py``
(composition root), and ``services``/``clients``. See ``app_factory.py``.
"""

from logging_config import setup_logging

setup_logging()

from app_factory import create_app
from settings import Settings

settings = Settings.from_env()
app = create_app(settings)
container = app.container

if __name__ == "__main__":
    # Ensure the news vector store exists before the first chat turn happens; the
    # news KB is always-on context for every conversation (best-effort create).
    container.news_vector_store_service.ensure_created()
    app.run(host="0.0.0.0", port=5001, debug=settings.flask_debug, threaded=True)
