"""
LLM Configuration Module

Provides configuration dataclasses and utilities for managing LLM settings.
Supports loading from environment variables and merging with user overrides.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os
import yaml
from pathlib import Path


@dataclass
class LLMConfig:
    """
    LLM Configuration

    Attributes:
        provider: LLM provider ("gemini", "anthropic", "openai", "openrouter")
        model: Model name (e.g., "claude-sonnet-4", "gemini-2.0-flash-exp")
        temperature: Model temperature (0.0 - 2.0)
        max_tokens: Maximum output tokens
        extra_params: Additional provider-specific parameters
    """
    provider: str
    model: str
    temperature: float = 0.1
    max_tokens: int = 4096
    extra_params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env_var(cls, env_var_name: str) -> "LLMConfig":
        """
        Load LLM config from environment variable

        Expected format: LABOS_MANAGER_MODEL=anthropic/claude-sonnet-4

        Args:
            env_var_name: Environment variable name (e.g., "LABOS_MANAGER_MODEL")

        Returns:
            LLMConfig instance with settings from environment

        Example:
            >>> config = LLMConfig.from_env_var("LABOS_MANAGER_MODEL")
            >>> config.provider
            'anthropic'
            >>> config.model
            'claude-sonnet-4'
        """
        model_string = os.getenv(env_var_name, "gemini/gemini-3-pro-preview")

        # Parse provider/model format
        if "/" in model_string:
            provider, model = model_string.split("/", 1)
        else:
            # Fallback: assume gemini if no provider specified
            provider = "gemini"
            model = model_string

        # Load global temperature and max_tokens
        temperature = float(os.getenv("MODEL_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("MODEL_MAX_TOKENS", "4096"))

        return cls(
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMConfig":
        """
        Create LLMConfig from dictionary (for API input)

        Args:
            data: Dictionary with provider, model, temperature, etc.

        Returns:
            LLMConfig instance

        Example:
            >>> config = LLMConfig.from_dict({
            ...     "provider": "anthropic",
            ...     "model": "claude-sonnet-4",
            ...     "temperature": 0.2
            ... })
        """
        return cls(
            provider=data.get("provider", "gemini"),
            model=data.get("model", "gemini-3-pro-preview"),
            temperature=data.get("temperature", 0.1),
            max_tokens=data.get("max_tokens", 4096),
            extra_params=data.get("extra_params", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "extra_params": self.extra_params
        }


def _load_yaml_config() -> Optional[Dict[str, Any]]:
    """
    Load LLM configuration from config/llm_models.yaml

    Returns:
        Dictionary with agent configurations, or None if file doesn't exist
    """
    config_path = Path(__file__).parent.parent.parent.parent / "config" / "llm_models.yaml"

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Failed to load {config_path}: {e}")
        return None


def get_default_agent_configs() -> Dict[str, LLMConfig]:
    """
    Load default Agent LLM configurations from YAML file or environment variables

    Priority:
    1. config/llm_models.yaml (if exists)
    2. Environment variables (fallback)

    YAML Format:
        agents:
          manager:
            model: anthropic/claude-sonnet-4
            temperature: 0.1
            max_tokens: 4096

    Environment Variables (fallback):
        LABOS_MANAGER_MODEL: Manager agent model (e.g., "anthropic/claude-sonnet-4")
        LABOS_DEV_MODEL: Dev agent model
        LABOS_CRITIC_MODEL: Critic agent model
        LABOS_TOOL_CREATION_MODEL: Tool creation agent model

    Returns:
        Dictionary mapping agent names to LLMConfig instances

    Example:
        >>> configs = get_default_agent_configs()
        >>> configs["manager"].provider
        'anthropic'
        >>> configs["dev_agent"].model
        'gemini-2.0-flash-exp'
    """
    # Try loading from YAML first
    yaml_config = _load_yaml_config()

    if yaml_config and "agents" in yaml_config:
        configs = {}
        agents_config = yaml_config["agents"]

        for agent_name, agent_data in agents_config.items():
            # Parse model format: "provider/model"
            model_string = agent_data.get("model", "gemini/gemini-3-pro-preview")

            if "/" in model_string:
                provider, model = model_string.split("/", 1)
            else:
                provider = "gemini"
                model = model_string

            configs[agent_name] = LLMConfig(
                provider=provider,
                model=model,
                temperature=agent_data.get("temperature", 0.1),
                max_tokens=agent_data.get("max_tokens", 4096),
                extra_params=agent_data.get("extra_params", {})
            )

        return configs

    # Fallback to environment variables
    return {
        "manager": LLMConfig.from_env_var("LABOS_MANAGER_MODEL"),
        "dev_agent": LLMConfig.from_env_var("LABOS_DEV_MODEL"),
        "critic_agent": LLMConfig.from_env_var("LABOS_CRITIC_MODEL"),
        "tool_creation_agent": LLMConfig.from_env_var("LABOS_TOOL_CREATION_MODEL"),
    }


def merge_agent_configs(
    defaults: Dict[str, LLMConfig],
    overrides: Optional[Dict[str, Dict[str, Any]]]
) -> Dict[str, LLMConfig]:
    """
    Merge default Agent configs with user-provided overrides

    This allows users to override specific agent configurations while
    keeping defaults for others.

    Args:
        defaults: Default configurations from environment variables
        overrides: Optional user overrides from API
            Example: {"manager": {"provider": "openai", "model": "gpt-4o"}}

    Returns:
        Merged configuration dictionary

    Example:
        >>> defaults = get_default_agent_configs()
        >>> overrides = {"manager": {"provider": "openai", "model": "gpt-4o"}}
        >>> merged = merge_agent_configs(defaults, overrides)
        >>> merged["manager"].provider  # User override
        'openai'
        >>> merged["dev_agent"].provider  # Default (not overridden)
        'gemini'
    """
    if not overrides:
        return defaults

    merged = defaults.copy()

    for agent_name, override_data in overrides.items():
        if agent_name in merged:
            # User override: create new config from dict
            merged[agent_name] = LLMConfig.from_dict(override_data)
        else:
            # Unknown agent name, but still create config
            merged[agent_name] = LLMConfig.from_dict(override_data)

    return merged
