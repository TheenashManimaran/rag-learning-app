import os
import litellm
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from backend.app.core.config import settings


class ConfigurationError(Exception):
    """Exception raised for missing or invalid configuration."""
    pass


class LLMGateway:
    """
    Multi-Model Mesh Gateway for routing requests to specialized models.
    """
    def __init__(self):
        self.models = {
            "LIBRARIAN": settings.librarian_model,
            "ORCHESTRATOR": settings.orchestrator_model,
            "JUDGE": settings.judge_model
        }
        self._check_api_keys()

    def _check_api_keys(self):
        missing_keys = []
        if not settings.groq_api_key: missing_keys.append("GROQ_API_KEY")
        if not settings.gemini_api_key: missing_keys.append("GEMINI_API_KEY")
        if not settings.mistral_api_key: missing_keys.append("MISTRAL_API_KEY")
        if not settings.xai_api_key: missing_keys.append("XAI_API_KEY")
        
        if missing_keys:
            raise ConfigurationError(f"Missing required API keys: {', '.join(missing_keys)}")

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((
            litellm.exceptions.ServiceUnavailableError, 
            litellm.exceptions.RateLimitError
        ))
    )
    async def _execute_acompletion(self, model_name: str, messages: list[dict], tools: list = None):
        return await litellm.acompletion(
            model=model_name,
            messages=messages,
            tools=tools
        )

    async def get_response(self, role: str, messages: list[dict], tools: list = None):
        """
        Get an async response from the specified model role.
        """
        if role not in self.models:
            raise ValueError(f"Unknown role: {role}. Available roles: {list(self.models.keys())}")
        
        model_name = self.models[role]
        
        try:
            response = await self._execute_acompletion(model_name, messages, tools)
            return response
        except Exception as e:
            if role == "LIBRARIAN":
                fallback_model = self.models["ORCHESTRATOR"]
                # Attempt to fall back to the ORCHESTRATOR
                return await self._execute_acompletion(fallback_model, messages, tools)
            raise e
