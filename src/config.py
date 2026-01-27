"""
Configuration management for The Planeswalker Agent.

Loads configuration from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI API (including Realtime API)."""
    api_key: Optional[str] = None
    # Realtime API settings (supports both OpenAI and Azure OpenAI)
    realtime_endpoint: Optional[str] = None  # Full WebSocket URL
    realtime_model: str = "gpt-4o-realtime-preview"
    realtime_api_version: str = "2024-10-01-preview"
    # Azure-specific settings
    azure_endpoint: Optional[str] = None  # e.g., https://your-resource.openai.azure.com
    azure_deployment: Optional[str] = None  # Deployment name for Azure
    # Standard API settings (fallback)
    api_endpoint: str = "https://api.openai.com/v1"
    chat_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2048

    @property
    def is_configured(self) -> bool:
        """Check if OpenAI is properly configured."""
        return self.api_key is not None and len(self.api_key) > 0

    @property
    def is_azure(self) -> bool:
        """Check if using Azure OpenAI."""
        return self.azure_endpoint is not None or (
            self.realtime_endpoint and "azure" in self.realtime_endpoint.lower()
        )

    def get_realtime_url(self) -> str:
        """
        Build the full Realtime API WebSocket URL.

        For Azure OpenAI:
            wss://{resource}.openai.azure.com/openai/realtime?api-version=2024-10-01-preview&deployment={deployment}

        For OpenAI:
            wss://api.openai.com/v1/realtime?model={model}
        """
        # If explicit endpoint provided, use it
        if self.realtime_endpoint:
            url = self.realtime_endpoint
            # Add api-version if not present (for Azure)
            if "azure" in url.lower() and "api-version" not in url:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}api-version={self.realtime_api_version}"
            return url

        # Build Azure URL
        if self.azure_endpoint:
            base = self.azure_endpoint.rstrip("/")
            # Convert https to wss
            if base.startswith("https://"):
                base = "wss://" + base[8:]
            elif base.startswith("http://"):
                base = "ws://" + base[7:]
            elif not base.startswith("wss://"):
                base = "wss://" + base

            deployment = self.azure_deployment or self.realtime_model
            return f"{base}/openai/realtime?api-version={self.realtime_api_version}&deployment={deployment}"

        # Default OpenAI URL
        return f"wss://api.openai.com/v1/realtime?model={self.realtime_model}"


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic Claude API."""
    api_key: Optional[str] = None
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 2048

    @property
    def is_configured(self) -> bool:
        """Check if Anthropic is properly configured."""
        return self.api_key is not None and len(self.api_key) > 0


@dataclass
class AgentConfig:
    """Main agent configuration."""
    # LLM provider: "openai", "openai_realtime", "anthropic", or "none"
    llm_provider: str = "none"
    # Enable verbose logging
    verbose: bool = False
    # Cache settings
    cache_enabled: bool = True
    cache_dir: str = "data"


class Config:
    """
    Central configuration class for The Planeswalker Agent.

    Usage:
        from src.config import config

        if config.openai.is_configured:
            # Use OpenAI
            pass
    """

    def __init__(self):
        self.openai = self._load_openai_config()
        self.anthropic = self._load_anthropic_config()
        self.agent = self._load_agent_config()

    def _load_openai_config(self) -> OpenAIConfig:
        """Load OpenAI configuration from environment."""
        return OpenAIConfig(
            api_key=os.getenv("OPENAI_API_KEY"),
            # Realtime settings
            realtime_endpoint=os.getenv("OPENAI_REALTIME_ENDPOINT"),
            realtime_model=os.getenv(
                "OPENAI_REALTIME_MODEL",
                "gpt-4o-realtime-preview"
            ),
            realtime_api_version=os.getenv(
                "OPENAI_REALTIME_API_VERSION",
                "2024-10-01-preview"
            ),
            # Azure-specific settings
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            # Standard API settings
            api_endpoint=os.getenv(
                "OPENAI_API_ENDPOINT",
                "https://api.openai.com/v1"
            ),
            chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2048")),
        )

    def _load_anthropic_config(self) -> AnthropicConfig:
        """Load Anthropic configuration from environment."""
        return AnthropicConfig(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048")),
        )

    def _load_agent_config(self) -> AgentConfig:
        """Load agent configuration from environment."""
        return AgentConfig(
            llm_provider=os.getenv("LLM_PROVIDER", "none"),
            verbose=os.getenv("VERBOSE", "false").lower() == "true",
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            cache_dir=os.getenv("CACHE_DIR", "data"),
        )

    def get_active_llm_provider(self) -> Optional[str]:
        """
        Determine which LLM provider to use based on configuration.

        Returns provider name or None if no LLM is configured.
        """
        provider = self.agent.llm_provider.lower()

        if provider == "openai_realtime" and self.openai.is_configured:
            return "openai_realtime"
        elif provider == "openai" and self.openai.is_configured:
            return "openai"
        elif provider == "anthropic" and self.anthropic.is_configured:
            return "anthropic"
        elif provider == "auto":
            # Auto-detect: prefer OpenAI Realtime > OpenAI > Anthropic
            if self.openai.is_configured:
                return "openai"
            elif self.anthropic.is_configured:
                return "anthropic"

        return None

    def print_status(self):
        """Print configuration status for debugging."""
        print("\n=== Configuration Status ===")
        print(f"LLM Provider Setting: {self.agent.llm_provider}")
        print(f"Active Provider: {self.get_active_llm_provider() or 'None (template-based responses)'}")
        print(f"OpenAI Configured: {self.openai.is_configured}")
        print(f"  - Using Azure: {self.openai.is_azure}")
        print(f"  - Realtime URL: {self.openai.get_realtime_url()}")
        print(f"  - API Version: {self.openai.realtime_api_version}")
        print(f"  - Realtime Model: {self.openai.realtime_model}")
        print(f"  - Chat Model: {self.openai.chat_model}")
        if self.openai.azure_endpoint:
            print(f"  - Azure Endpoint: {self.openai.azure_endpoint}")
            print(f"  - Azure Deployment: {self.openai.azure_deployment}")
        print(f"Anthropic Configured: {self.anthropic.is_configured}")
        print(f"  - Model: {self.anthropic.model}")
        print(f"Verbose: {self.agent.verbose}")
        print(f"Cache Enabled: {self.agent.cache_enabled}")
        print("=" * 28 + "\n")


# Global singleton instance
config = Config()
