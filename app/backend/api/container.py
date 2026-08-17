"""Composition root: builds every client/service once from a ``Settings``.

Routes/blueprints depend on this ``Container`` (an explicit collection of
already-wired collaborators), not on module-level globals created at import
time. Tests can build a ``Container`` with fakes/mocks directly, or patch
individual attributes on an existing instance — this is the Dependency
Inversion move referenced throughout the refactor plan.
"""

from __future__ import annotations

from typing import Optional

from clients.general_simulation_client import GeneralSimulationClient
from clients.llama_stack_client import LlamaStackClient
from clients.news_client import NewsClient
from clients.vector_store_client import VectorStoreClient
from logging_config import getLogger
from repositories.knowledge_base_repository import KnowledgeBaseRepository
from services.agent_service import AgentService
from services.chat_service import ChatService
from services.general_simulation_service import GeneralSimulationService
from services.news_service import NewsService
from services.news_vector_store_service import NewsVectorStoreService
from services.readiness_service import ReadinessService
from services.scenario_create_service import ScenarioCreateService
from settings import Settings

logger = getLogger(__name__)

_FALLBACK_OPENAI_MODEL = "gpt-4o-mini"


def _resolve_openai_model(settings: Settings) -> str:
    if settings.llama_stack_openai_model:
        return settings.llama_stack_openai_model
    logger.error(
        "LLAMA_STACK_OPENAI_MODEL is not set. Set it to the model ID for the "
        "OpenAI-compatible endpoint."
    )
    return _FALLBACK_OPENAI_MODEL


def _build_primary_llama_client(settings: Settings, openai_model: str) -> LlamaStackClient:
    stack_url = (settings.llama_stack_url or "").rstrip("/")
    # Local OpenAI-only setups often point LLAMA_STACK_URL at api.openai.com. The
    # default Llama Stack model ID is invalid there, so use the OpenAI model for
    # the primary client.
    if "api.openai.com" in stack_url:
        logger.warning(
            "LLAMA_STACK_URL points at OpenAI (%s); using model %s for the primary "
            "chat client instead of LLAMA_STACK_MODEL.",
            stack_url,
            openai_model,
        )
        model = openai_model
    else:
        model = settings.llama_stack_model
    return LlamaStackClient(
        timeout_seconds=settings.llama_stack_timeout_seconds,
        base_url=settings.llama_stack_url,
        model=model,
        label="vllm",
        api_key=settings.openai_api_key,
        vector_store_provider=settings.vector_store_provider,
    )


def _build_vector_store_client(settings: Settings) -> Optional[VectorStoreClient]:
    try:
        client = VectorStoreClient(
            host=settings.pg_host,
            port=settings.pg_port,
            user=settings.pg_user,
            password=settings.pg_password,
            database=settings.pg_database,
            llama_stack_url=settings.llama_stack_url,
            embed_model=settings.embed_model,
            embed_base_url=settings.embed_base_url,
            embed_api_key=settings.embed_api_key,
        )
        logger.info("VectorStoreClient initialized successfully.")
        return client
    # Broad catch: best-effort init; external libs may raise varied errors, proceed without RAG context.
    except Exception as exc:
        logger.warning(
            "VectorStoreClient could not be initialized (%s). Chat will proceed without RAG context.",
            exc,
        )
        return None


class Container:
    """Holds every constructed client/service for the API process."""

    def __init__(self, settings: Settings):
        self.settings = settings

        self.news_client = NewsClient(
            feed_urls_raw=settings.news_feed_urls_raw,
            user_agent=settings.news_user_agent,
        )
        self.news_service = NewsService(client=self.news_client)

        self.general_simulation_client = GeneralSimulationClient(
            base_url=settings.general_simulation_base_url,
            timeout=settings.general_simulation_timeout_seconds,
        )
        self.general_simulation_service = GeneralSimulationService(
            client=self.general_simulation_client
        )

        self.vector_store_client = _build_vector_store_client(settings)

        openai_model = _resolve_openai_model(settings)
        self.primary_llama_client = _build_primary_llama_client(settings, openai_model)
        self.openai_llama_client = LlamaStackClient(
            timeout_seconds=settings.llama_stack_timeout_seconds,
            base_url=settings.llama_stack_url,
            model=openai_model,
            label="openai",
            api_key=settings.openai_api_key,
            vector_store_provider=settings.vector_store_provider,
        )

        self.news_vector_store_service = NewsVectorStoreService(
            llama_client=self.primary_llama_client,
        )

        self.agent_service = AgentService(
            self.primary_llama_client,
            general_simulation_client=self.general_simulation_client,
            news_client=self.news_client,
            news_vector_store=self.news_vector_store_service,
        )
        self.chat_service = ChatService(
            self.primary_llama_client,
            vector_store_client=self.vector_store_client,
            openai_client=self.openai_llama_client,
            agent_service=self.agent_service,
            news_vector_store=self.news_vector_store_service,
        )
        self.scenario_create_service = ScenarioCreateService(
            llama_stack_client=self.primary_llama_client,
            general_simulation_client=self.general_simulation_client,
        )

        self.knowledge_base_repository = KnowledgeBaseRepository(settings.knowledge_bases_store_path)

        self.readiness_service = ReadinessService(
            self.primary_llama_client,
            self.general_simulation_client,
            self.vector_store_client,
        )
