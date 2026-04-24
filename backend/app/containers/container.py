"""
DSA AutoGrader - Dependency Injection Container (Enhanced).

Features:
- Graceful degradation for failed dependencies
- Health checks for all components
- Lazy initialization
- Resource cleanup
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.core.config import AI_MODEL_NAME, DB_FILE, GEMINI_API_KEY, REDIS_URL, SQL_SERVER_URL

logger = logging.getLogger("dsa.container")


@dataclass
class ComponentHealth:
    """Health status of a component."""
    name: str
    healthy: bool
    message: str = ""
    error: Optional[str] = None


@dataclass
class ContainerHealth:
    """Overall container health status."""
    healthy: bool
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: __import__('time').time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "healthy": self.healthy,
            "components": {
                name: {
                    "healthy": comp.healthy,
                    "message": comp.message,
                    "error": comp.error,
                }
                for name, comp in self.components.items()
            },
            "timestamp": self.timestamp,
        }


class Container:
    """
    Dependency Injection Container with graceful degradation.

    Features:
    - Singleton pattern
    - Graceful degradation (Redis fail → In-Memory)
    - Health checks for all components
    - Lazy initialization
    - Proper resource cleanup

    Usage::
        container = Container()
        container.initialize()

        grading_service = container.get_grading_service()
        health = container.get_health()
    """

    _instance: Optional["Container"] = None

    def __init__(self) -> None:
        # Infrastructure
        self._repository = None
        self._job_store = None
        self._cache = None
        self._event_bus = None

        # AI
        self._ai_provider = None

        # Services
        self._ai_grading_service = None
        self._ast_grading_service = None
        self._plagiarism_service = None
        self._grading_service = None

        # Health tracking
        self._health_status: Dict[str, ComponentHealth] = {}

        # Configuration snapshot
        self._config = {
            "ai_provider": "gemini",
            "gemini_api_key": GEMINI_API_KEY,
            "ai_model_name": AI_MODEL_NAME,
            "sql_server_url": SQL_SERVER_URL,
            "db_file": DB_FILE,
            "redis_url": REDIS_URL,
        }

        # Test overrides
        self._overrides: dict = {}

    # ==================== SINGLETON ====================

    @classmethod
    def get_instance(cls) -> "Container":
        """Return the singleton container instance."""
        if cls._instance is None:
            cls._instance = Container()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (testing only)."""
        cls._instance = None

    # ==================== INITIALISATION ====================

    def initialize(self) -> None:
        """
        Initialise all dependencies with graceful degradation.
        Call once at startup.
        """
        logger.info("Initializing container components...")

        # Initialize in order of dependency
        self._init_infrastructure()
        self._init_ai_providers()
        self._init_services()

        # Log final health status
        health = self.get_health()
        logger.info(
            "Container initialized: %s healthy, %s unhealthy",
            sum(1 for c in health.components.values() if c.healthy),
            sum(1 for c in health.components.values() if not c.healthy),
        )

    def _init_infrastructure(self) -> None:
        """Set up repository, job store, and cache with graceful degradation."""
        # 1. Repository (Database) - Required
        try:
            from app.services.repository import GradingRepository

            self._repository = GradingRepository(
                sql_server_url=self._config["sql_server_url"],
                sqlite_file=self._config["db_file"],
            )
            self._repository.initialize()
            self._health_status["repository"] = ComponentHealth(
                name="repository",
                healthy=True,
                message="Database initialized successfully",
            )
            logger.info("Repository initialized: %s", 
                       "SQL Server" if self._config["sql_server_url"] else "SQLite")
        except Exception as exc:
            logger.error("Repository initialization failed: %s", exc)
            self._health_status["repository"] = ComponentHealth(
                name="repository",
                healthy=False,
                message="Database initialization failed",
                error=str(exc),
            )
            raise RuntimeError(f"Critical: Database initialization failed: {exc}")

        # 2. Job Store - Graceful degradation (Redis → In-Memory)
        try:
            from app.services.job_store import get_job_store

            self._job_store = get_job_store()
            redis_available = self._job_store._use_redis if hasattr(self._job_store, '_use_redis') else False
            self._health_status["job_store"] = ComponentHealth(
                name="job_store",
                healthy=True,
                message=f"Job store initialized ({'Redis' if redis_available else 'In-Memory'})",
            )
            logger.info("Job store initialized: %s", "Redis" if redis_available else "In-Memory")
        except Exception as exc:
            logger.error("Job store initialization failed: %s", exc)
            self._health_status["job_store"] = ComponentHealth(
                name="job_store",
                healthy=False,
                message="Job store initialization failed",
                error=str(exc),
            )
            raise

        # 3. Cache - Graceful degradation (Redis → In-Memory)
        try:
            if self._config["redis_url"]:
                try:
                    from app.cache.redis_cache import RedisCache

                    self._cache = RedisCache(self._config["redis_url"])
                    self._health_status["cache"] = ComponentHealth(
                        name="cache",
                        healthy=True,
                        message="Redis cache initialized",
                    )
                    logger.info("Cache initialized: Redis")
                except Exception as redis_exc:
                    logger.warning("Redis cache failed (%s), falling back to in-memory.", redis_exc)
                    from app.cache.in_memory_cache import InMemoryCache

                    self._cache = InMemoryCache()
                    self._health_status["cache"] = ComponentHealth(
                        name="cache",
                        healthy=True,
                        message="In-Memory cache initialized (Redis failed)",
                    )
            else:
                from app.cache.in_memory_cache import InMemoryCache

                self._cache = InMemoryCache()
                self._health_status["cache"] = ComponentHealth(
                    name="cache",
                    healthy=True,
                    message="In-Memory cache initialized (no Redis URL)",
                )
                logger.info("Cache initialized: In-Memory (no Redis URL)")
        except Exception as exc:
            logger.error("Cache initialization failed: %s", exc)
            self._health_status["cache"] = ComponentHealth(
                name="cache",
                healthy=False,
                message="Cache initialization failed",
                error=str(exc),
            )
            # Cache is not critical - continue without it

        # 4. Event Bus - Always in-memory for now
        try:
            self._init_event_bus()
        except Exception as exc:
            logger.error("Event bus initialization failed: %s", exc)
            self._health_status["event_bus"] = ComponentHealth(
                name="event_bus",
                healthy=False,
                message="Event bus initialization failed",
                error=str(exc),
            )

    def _init_event_bus(self) -> None:
        """Set up the event bus."""
        try:
            from app.events.in_memory_event_bus import InMemoryEventBus

            self._event_bus = InMemoryEventBus()
            self._health_status["event_bus"] = ComponentHealth(
                name="event_bus",
                healthy=True,
                message="In-memory event bus initialized",
            )
            logger.info("Event bus initialized.")
        except Exception as exc:
            logger.error("Event bus initialization failed: %s", exc)
            raise

    def _init_ai_providers(self) -> None:
        """Set up the configured Gemini AI provider."""
        try:
            def _resolve_model() -> str:
                model_name = (self._config.get("ai_model_name") or "").strip()
                lower = model_name.lower()
                if not model_name or lower.startswith(("llama", "mixtral", "qwen", "gemma")):
                    return "gemini-2.0-flash"
                return model_name

            if self._config.get("gemini_api_key"):
                from app.services.ai_providers.gemini_provider import GeminiProvider

                model_name = _resolve_model()
                self._ai_provider = GeminiProvider(
                    api_key=self._config["gemini_api_key"],
                    model_name=model_name,
                )
                self._health_status["ai_provider"] = ComponentHealth(
                    name="ai_provider",
                    healthy=True,
                    message=f"Gemini AI initialized ({model_name})",
                )
                logger.info("AI provider initialized: Gemini (%s)", model_name)
                return

            self._health_status["ai_provider"] = ComponentHealth(
                name="ai_provider",
                healthy=False,
                message="No AI provider configured (set GEMINI_API_KEY)",
            )
            logger.info("AI provider: Not configured (AI-only grading unavailable until GEMINI_API_KEY is set)")
        except Exception as exc:
            logger.error("AI provider initialization failed: %s", exc)
            self._health_status["ai_provider"] = ComponentHealth(
                name="ai_provider",
                healthy=False,
                message=f"AI provider failed to start: {exc}",
                error=str(exc),
            )
            self._ai_provider = None  # Ensure it is set to None on failure

    def _init_services(self) -> None:
        """Set up business-logic services."""
        # 1. AST Grading Service - Optional support service (not used for AI-only scoring)
        try:
            from app.services.ast_grader import DSALightningGrader

            self._ast_grading_service = DSALightningGrader()
            self._health_status["ast_grading"] = ComponentHealth(
                name="ast_grading",
                healthy=True,
                message="AST grading service initialized",
            )
            logger.info("AST grading service initialized.")
        except Exception as exc:
            logger.error("AST grading service initialization failed: %s", exc)
            self._health_status["ast_grading"] = ComponentHealth(
                name="ast_grading",
                healthy=False,
                message="AST grading service initialization failed",
                error=str(exc),
            )
            raise RuntimeError(f"Critical: AST grading service failed: {exc}")

        # 2. AI Grading Service - Required for AI-only grading
        try:
            from app.services.ai_grading_service import AIGradingService

            self._ai_grading_service = AIGradingService(
                ai_provider=self._ai_provider,
                repository=self._repository,
            )
            ai_available = self._ai_provider is not None
            self._health_status["ai_grading"] = ComponentHealth(
                name="ai_grading",
                healthy=True,
                message=f"AI grading service initialized ({'AI enabled' if ai_available else 'Unavailable until AI provider is configured'})",
            )
            logger.info("AI grading service initialized: %s", 
                       "AI enabled" if ai_available else "Unavailable")
        except Exception as exc:
            logger.error("AI grading service initialization failed: %s", exc)
            self._health_status["ai_grading"] = ComponentHealth(
                name="ai_grading",
                healthy=False,
                message="AI grading service initialization failed",
                error=str(exc),
            )
            # AI grading is optional - create with None provider
            self._ai_grading_service = None

        # 3. Plagiarism Service - Required
        try:
            from app.services.plagiarism_service import PlagiarismService

            self._plagiarism_service = PlagiarismService(
                repository=self._repository,
                ai_provider=self._ai_provider,
            )
            self._health_status["plagiarism"] = ComponentHealth(
                name="plagiarism",
                healthy=True,
                message="Plagiarism service initialized",
            )
            logger.info("Plagiarism service initialized.")
        except Exception as exc:
            logger.error("Plagiarism service initialization failed: %s", exc)
            self._health_status["plagiarism"] = ComponentHealth(
                name="plagiarism",
                healthy=False,
                message="Plagiarism service initialization failed",
                error=str(exc),
            )
            raise RuntimeError(f"Critical: Plagiarism service failed: {exc}")

        # 4. Grading Service (Orchestrator) - Required
        try:
            from app.services.grading_service import GradingService

            self._grading_service = GradingService(
                ast_service=self._ast_grading_service,
                ai_service=self._ai_grading_service,
                plagiarism_service=self._plagiarism_service,
                repository=self._repository,
                job_store=self._job_store,
                event_bus=self._event_bus,
            )
            self._health_status["grading"] = ComponentHealth(
                name="grading",
                healthy=True,
                message="Grading orchestrator service initialized",
            )
            logger.info("Grading service initialized.")
        except Exception as exc:
            logger.error("Grading service initialization failed: %s", exc)
            self._health_status["grading"] = ComponentHealth(
                name="grading",
                healthy=False,
                message="Grading service initialization failed",
                error=str(exc),
            )
            raise RuntimeError(f"Critical: Grading service failed: {exc}")

    # ==================== RESOLVERS ====================

    def get_repository(self):
        """Return the grading repository."""
        return self._repository

    def get_job_store(self):
        """Return the job store."""
        return self._job_store

    def get_cache(self):
        """Return the cache layer."""
        return self._cache

    def get_event_bus(self):
        """Return the event bus."""
        return self._event_bus

    def get_ai_provider(self):
        """Return the AI provider (may be None)."""
        return self._ai_provider

    def get_ai_grading_service(self):
        """Return the AI grading service (may be None)."""
        return self._ai_grading_service

    def get_ast_grading_service(self):
        """Return the AST grading service."""
        return self._ast_grading_service

    def get_plagiarism_service(self):
        """Return the plagiarism detection service."""
        return self._plagiarism_service

    def get_grading_service(self):
        """Return the main grading orchestrator service."""
        return self._grading_service

    # ==================== HEALTH CHECKS ====================

    def get_health(self) -> ContainerHealth:
        """Get overall container health status."""
        health = ContainerHealth(
            healthy=True,
            components=dict(self._health_status),
        )

        # Check if any critical component is unhealthy
        critical_components = ["repository", "ai_provider", "ai_grading", "plagiarism", "grading"]
        for name in critical_components:
            if name in health.components and not health.components[name].healthy:
                health.healthy = False
                break

        return health

    def get_health_dict(self) -> Dict[str, Any]:
        """Get health status as dictionary."""
        return self.get_health().to_dict()

    # ==================== TESTING OVERRIDES ====================

    def override(self, name: str, instance) -> None:
        """Replace a dependency with a test double."""
        self._overrides[name] = instance
        setattr(self, f"_{name}", instance)
        logger.info("Overrode dependency: %s", name)

    def reset_overrides(self) -> None:
        """Remove all test overrides."""
        self._overrides.clear()
        logger.info("Reset dependency overrides.")

    # ==================== SHUTDOWN ====================

    def shutdown(self) -> None:
        """Release all resources. Call at application shutdown."""
        logger.info("Shutting down container...")

        # Close database connection
        if self._repository:
            try:
                self._repository.close()
                logger.info("Repository closed.")
            except Exception as exc:
                logger.error("Repository shutdown error: %s", exc)

        # Close cache connection
        if self._cache:
            try:
                if hasattr(self._cache, 'close'):
                    self._cache.close()
                logger.info("Cache closed.")
            except Exception as exc:
                logger.error("Cache shutdown error: %s", exc)

        # Close event bus
        if self._event_bus:
            try:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    # Loop is running — fire-and-forget
                    loop.create_task(self._event_bus.disconnect())
                except RuntimeError:
                    # No running loop — create one for shutdown
                    asyncio.run(self._event_bus.disconnect())
                logger.info("Event bus disconnected.")
            except Exception as exc:
                logger.error("Event bus shutdown error: %s", exc)

        # Close job store
        if self._job_store:
            try:
                if hasattr(self._job_store, 'close'):
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._job_store.close())
                    except RuntimeError:
                        asyncio.run(self._job_store.close())
                logger.info("Job store closed.")
            except Exception as exc:
                logger.error("Job store shutdown error: %s", exc)

        logger.info("Container shutdown complete.")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------
_container: Optional[Container] = None


def get_container() -> Container:
    """Return (or create) the global container singleton."""
    global _container
    if _container is None:
        _container = Container()
        _container.initialize()
    return _container


def reset_container() -> None:
    """Destroy the global container (testing / shutdown)."""
    global _container
    if _container:
        _container.shutdown()
    _container = None


def get_container_health() -> Dict[str, Any]:
    """Get container health status without getting full container."""
    if _container:
        return _container.get_health_dict()
    return {
        "healthy": False,
        "message": "Container not initialized",
        "components": {},
    }


__all__ = [
    "Container",
    "ContainerHealth",
    "ComponentHealth",
    "get_container",
    "reset_container",
    "get_container_health",
]
