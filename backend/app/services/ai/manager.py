import logging
from typing import Dict, Optional, Type, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.entities import ProviderConfig, SecretRef, AppSetting
from app.core.secrets_manager import secrets_manager
from app.services.ai.base import BaseAIProvider
from app.services.ai.adapters.ollama import OllamaAdapter
from app.services.ai.adapters.openai_provider import OpenAIAdapter
from app.services.ai.adapters.gemini import GeminiAdapter
from app.services.ai.adapters.claude import ClaudeAdapter
from app.services.ai.adapters.openrouter import OpenRouterAdapter
from app.services.ai.adapters.generic_openai import GenericOpenAIAdapter

logger = logging.getLogger("ruby.ai.manager")

ADAPTER_MAP: Dict[str, Type[BaseAIProvider]] = {
    "ollama": OllamaAdapter,
    "openai": OpenAIAdapter,
    "gemini": GeminiAdapter,
    "anthropic": ClaudeAdapter,
    "openrouter": OpenRouterAdapter,
    "generic": GenericOpenAIAdapter,
}


class ProviderManager:
    """Manages AI provider instances, authentication, and task routing."""

    @staticmethod
    def get_adapter_class(provider_type: str) -> Type[BaseAIProvider]:
        adapter_cls = ADAPTER_MAP.get(provider_type.lower())
        if not adapter_cls:
            raise ValueError(f"Unsupported provider type '{provider_type}'. Supported: {list(ADAPTER_MAP.keys())}")
        return adapter_cls

    @classmethod
    async def get_provider_instance(
        cls, session: AsyncSession, provider_id: str
    ) -> BaseAIProvider:
        """Instantiate an adapter with decrypted secrets."""
        stmt = select(ProviderConfig).where(ProviderConfig.id == provider_id)
        res = await session.execute(stmt)
        config = res.scalars().first()
        if not config:
            raise ValueError(f"Provider configuration with ID '{provider_id}' not found.")

        # Retrieve secret if referenced
        api_key = None
        secret_stmt = select(SecretRef).where(SecretRef.provider_id == provider_id)
        sec_res = await session.execute(secret_stmt)
        sec_ref = sec_res.scalars().first()
        if sec_ref:
            api_key = secrets_manager.get_secret(sec_ref.key_name)

        adapter_cls = cls.get_adapter_class(config.provider_type)
        return adapter_cls(
            name=config.name,
            provider_type=config.provider_type,
            base_url=config.base_url,
            api_key=api_key,
            default_model=config.model_name,
            timeout_seconds=config.timeout_seconds,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            extra_params=config.extra_params,
        )

    @classmethod
    async def get_default_provider(cls, session: AsyncSession) -> BaseAIProvider:
        """Retrieve default enabled provider (preferring local Ollama)."""
        stmt = select(ProviderConfig).where(
            ProviderConfig.is_enabled == True,
            ProviderConfig.is_default == True,
        )
        res = await session.execute(stmt)
        default_config = res.scalars().first()

        if not default_config:
            # Fallback to any enabled provider
            stmt_any = select(ProviderConfig).where(ProviderConfig.is_enabled == True)
            res_any = await session.execute(stmt_any)
            default_config = res_any.scalars().first()

        if not default_config:
            # Temporary in-memory fallback to local Ollama
            return OllamaAdapter(
                name="Default Ollama",
                provider_type="ollama",
                base_url="http://127.0.0.1:11434",
                default_model="llama3.2:latest",
            )

        return await cls.get_provider_instance(session, default_config.id)

    @classmethod
    async def resolve_provider_for_task(
        cls, session: AsyncSession, task: str = "chat", requested_provider_id: Optional[str] = None
    ) -> BaseAIProvider:
        """
        Route request to the appropriate provider.
        Enforces strict local-first policy: never fall back to cloud unless explicitly chosen.
        """
        if requested_provider_id:
            return await cls.get_provider_instance(session, requested_provider_id)

        # Check for task routing in app settings (e.g. 'route_reasoning_provider')
        setting_key = f"route_{task}_provider"
        stmt = select(AppSetting).where(AppSetting.key == setting_key)
        res = await session.execute(stmt)
        setting = res.scalars().first()
        if setting and setting.value:
            return await cls.get_provider_instance(session, setting.value)

        return await cls.get_default_provider(session)

    @classmethod
    async def get_active_adapter(
        cls, session: AsyncSession, provider_id: Optional[str] = None
    ) -> BaseAIProvider:
        """Alias for resolving the active chat adapter."""
        return await cls.resolve_provider_for_task(
            session=session, task="chat", requested_provider_id=provider_id
        )

    @classmethod
    async def ensure_default_ollama_provider(cls, session: AsyncSession) -> None:
        """Seed default local Ollama provider if none exist."""
        stmt = select(ProviderConfig).limit(1)
        res = await session.execute(stmt)
        if res.scalars().first() is None:
            default_ollama = ProviderConfig(
                name="Ollama (Local)",
                provider_type="ollama",
                base_url="http://127.0.0.1:11434",
                model_name="llama3.2:latest",
                is_enabled=True,
                is_default=True,
                timeout_seconds=60,
                temperature=0.7,
            )
            session.add(default_ollama)
            await session.commit()
            logger.info("Created default local Ollama provider record.")


provider_manager = ProviderManager()
