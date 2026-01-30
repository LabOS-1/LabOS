"""
LLM Factory Module

Provides unified factory for creating LangChain Chat Model instances
from LLMConfig objects.
"""

from typing import Any
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from .config import LLMConfig


class LLMFactory:
    """
    Factory for creating LangChain Chat Model instances

    Supports:
    - Google Gemini (via langchain_google_genai)
    - Anthropic Claude (via langchain_anthropic)
    - OpenAI GPT (via langchain_openai)
    - OpenRouter (any model via ChatOpenAI with custom base URL)
    """

    @staticmethod
    def create(config: LLMConfig) -> Any:
        """
        Create LangChain Chat Model from configuration

        Args:
            config: LLMConfig instance with provider, model, and parameters

        Returns:
            LangChain Chat Model instance (ChatGoogleGenerativeAI, ChatAnthropic, etc.)

        Raises:
            ValueError: If provider is unknown or API key is missing

        Example:
            >>> config = LLMConfig(provider="anthropic", model="claude-sonnet-4")
            >>> model = LLMFactory.create(config)
            >>> isinstance(model, ChatAnthropic)
            True
        """
        provider = config.provider.lower()

        if provider == "gemini":
            return LLMFactory._create_gemini(config)
        elif provider == "anthropic":
            return LLMFactory._create_anthropic(config)
        elif provider == "openai":
            return LLMFactory._create_openai(config)
        elif provider == "openrouter":
            return LLMFactory._create_openrouter(config)
        else:
            raise ValueError(
                f"Unknown LLM provider: {provider}. "
                f"Supported: gemini, anthropic, openai, openrouter"
            )

    @staticmethod
    def _create_gemini(config: LLMConfig) -> ChatGoogleGenerativeAI:
        """Create Google Gemini model with optional Google Search grounding"""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        # Prepare parameters
        params = config.extra_params.copy()

        # Note: google_search is now handled in LangChainAgent.bind_tools()
        # to avoid being overwritten when agent binds its own tools
        params.pop("google_search", None)  # Remove if present

        # Create base model
        llm = ChatGoogleGenerativeAI(
            model=config.model,
            google_api_key=api_key,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
            **params
        )

        return llm

    @staticmethod
    def _create_anthropic(config: LLMConfig) -> ChatAnthropic:
        """Create Anthropic Claude model"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        return ChatAnthropic(
            model=config.model,
            anthropic_api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            **config.extra_params
        )

    @staticmethod
    def _create_openai(config: LLMConfig) -> ChatOpenAI:
        """Create OpenAI GPT model"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        return ChatOpenAI(
            model=config.model,
            openai_api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            **config.extra_params
        )

    @staticmethod
    def _create_openrouter(config: LLMConfig) -> ChatOpenAI:
        """
        Create model via OpenRouter API

        OpenRouter provides unified access to 100+ LLMs through OpenAI-compatible API.
        Model names should be in format: "provider/model" (e.g., "anthropic/claude-sonnet-4")

        Requires: OPENROUTER_API_KEY environment variable
        """
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY_STRING")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY or OPENROUTER_API_KEY_STRING not found in environment variables"
            )

        return ChatOpenAI(
            model=config.model,  # e.g., "anthropic/claude-sonnet-4"
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            **config.extra_params
        )
