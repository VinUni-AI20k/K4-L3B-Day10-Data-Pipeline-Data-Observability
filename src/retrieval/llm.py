from __future__ import annotations

import re
from typing import Any, Sequence

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from core.config import Settings, normalized_provider, require_llm_credentials
from core.utils import first_sentence


class _MockPaperChatModel(FakeListChatModel):
    """Exercise the local paper tools deterministically without a remote model."""

    tool_names: tuple[str, ...] = ()

    def bind_tools(self, tools: Sequence[Any], *, tool_choice=None, **kwargs):
        names = tuple(convert_to_openai_tool(tool)["function"]["name"] for tool in tools)
        if set(names) - {"semantic_search_papers", "lookup_paper"}:
            # Structured judging remains the evaluator's explicit heuristic fallback.
            raise NotImplementedError("The offline mock supports only the local paper tools.")
        return self.model_copy(update={"tool_names": names})

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        if not self.tool_names:
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

        latest_user = next(
            (index for index in range(len(messages) - 1, -1, -1)
             if isinstance(messages[index], HumanMessage)),
            None,
        )
        question = str(messages[latest_user].content) if latest_user is not None else ""
        turn = messages[latest_user + 1:] if latest_user is not None else messages
        results = [message for message in turn if isinstance(message, ToolMessage)]

        def tool_call(name, arguments):
            message = AIMessage(content="", tool_calls=[{
                "name": name, "args": arguments, "id": f"mock_{len(messages)}",
            }])
            return ChatResult(generations=[ChatGeneration(message=message)])

        if not results:
            quoted = re.search(r"'([^']+)'", question)
            if quoted and "lookup_paper" in self.tool_names:
                return tool_call("lookup_paper", {"paper_id_or_title": quoted.group(1)})
            if "semantic_search_papers" in self.tool_names:
                return tool_call("semantic_search_papers", {"query": question, "top_k": 4})
            return tool_call("lookup_paper", {"paper_id_or_title": question})

        latest = results[-1]
        content = str(latest.content)
        if (latest.name == "lookup_paper" and content == "No exact paper match found."
                and "semantic_search_papers" in self.tool_names):
            return tool_call("semantic_search_papers", {"query": question, "top_k": 4})

        # Only the first retrieved paper supplies an answer, matching baseline QA.
        fields = {}
        for line in content.split("\npaper_id:", 1)[0].splitlines():
            key, separator, value = line.partition(": ")
            if separator:
                fields[key.lower()] = value
        lowered = question.lower()
        if "who authored" in lowered or "list the authors" in lowered:
            answer = fields.get("authors", "")
        elif any(phrase in lowered for phrase in ("when was", "publication date", "published on")):
            answer = fields.get("published", "")
        elif "what categories" in lowered:
            answer = fields.get("categories", "")
        else:
            answer = first_sentence(fields.get("summary", ""))
        message = AIMessage(content=answer or "I don't know from the indexed corpus.")
        return ChatResult(generations=[ChatGeneration(message=message)])


def build_llm(settings: Settings, temperature: float = 0.0):
    provider = normalized_provider(settings)
    require_llm_credentials(settings)

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=settings.model_name,
            google_api_key=settings.google_api_key,
            temperature=temperature,
        )
    if provider == "openai":
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
            temperature=temperature,
        )
    if provider == "anthropic":
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
        return _MockPaperChatModel(responses=["This is a mock response from the scholarly corpus."])
    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
