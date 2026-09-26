from __future__ import annotations

from core.config import Settings, normalized_provider, require_llm_credentials


def build_llm(settings: Settings, temperature: float = 0.0):
    provider = normalized_provider(settings)
    require_llm_credentials(settings)

    # Load only the selected provider; Mock works without optional provider SDKs.
    if provider in {"groq", "openai", "openrouter", "custom"}:
        from langchain_openai import ChatOpenAI

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.model_name,
            google_api_key=settings.google_api_key,
            temperature=temperature,
        )
    if provider == "groq":
        import os

        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.groq_api_key or os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
            temperature=temperature,
        )
    if provider == "openai":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
            temperature=temperature,
        )
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.model_name,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
        )
    if provider == "openrouter":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=temperature,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.model_name,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )
    if provider == "custom":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.custom_llm_api_key or "unused",
            base_url=settings.custom_llm_base_url,
            temperature=temperature,
        )
    if provider == "mock":
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        return FakeListChatModel(responses=["This is a mock response from the scholarly corpus."])
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
