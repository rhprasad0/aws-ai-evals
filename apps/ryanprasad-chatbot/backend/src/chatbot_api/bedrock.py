from __future__ import annotations

from typing import Any

from .settings import ChatbotSettings


def converse(client: Any, *, model_id: str, messages: list[dict[str, object]], max_tokens: int) -> dict[str, Any]:
    return client.converse(
        modelId=model_id,
        messages=messages,
        inferenceConfig={"maxTokens": max_tokens},
        requestMetadata={"request_class": "chat"},
    )


def default_converse_kwargs(settings: ChatbotSettings | None = None) -> dict[str, Any]:
    settings = settings or ChatbotSettings()
    return {
        "modelId": settings.model_id,
        "inferenceConfig": {"maxTokens": settings.max_tokens},
        "requestMetadata": {"request_class": "chat"},
    }
