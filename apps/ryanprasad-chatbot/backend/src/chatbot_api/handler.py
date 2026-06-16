from __future__ import annotations

import json
import logging
from typing import Any

from .prompting import build_messages
from .response_contract import ChatResponse, ResponseContractError, validate_chat_response
from .settings import ChatbotSettings
from .sources import load_profile_source, sanitize_source_text

logger = logging.getLogger(__name__)


class ChatValidationError(ValueError):
    pass


def _extract_question(payload: dict[str, Any], settings: ChatbotSettings) -> str:
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages or len(messages) > settings.max_messages:
        raise ChatValidationError("messages must be a non-empty bounded list")
    for message in messages:
        if not isinstance(message, dict):
            raise ChatValidationError("messages must contain objects")
        if message.get("role") not in {"user", "assistant"}:
            raise ChatValidationError("only user and assistant roles are accepted")
        content = message.get("content")
        if not isinstance(content, str) or len(content) > settings.max_client_message_chars:
            raise ChatValidationError("message content must be a bounded string")
    user_messages = [message["content"] for message in messages if message["role"] == "user"]
    if not user_messages:
        raise ChatValidationError("at least one user message is required")
    return user_messages[-1]


def _extract_text(converse_response: dict[str, Any]) -> str:
    return converse_response["output"]["message"]["content"][0]["text"]


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").removeprefix("json").strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise json.JSONDecodeError("no JSON object found", stripped, 0)
    payload = json.loads(stripped[start : end + 1])
    if not isinstance(payload, dict):
        raise TypeError("response JSON must be an object")
    return payload


def _guardrail_response(question: str) -> ChatResponse | None:
    lower_question = question.lower()
    if "private" in lower_question or "private notes" in lower_question or "private projects" in lower_question:
        return ChatResponse(
            answer=(
                "I should not use private projects, private notes, local memory, or unpublished sources. "
                "The public evidence supports Ryan's container orchestration skills through `aws-devops-lab` "
                "and `airgap-aiops`; private-source support is outside this chatbot's boundary."
            ),
            citations=[],
            evidenceStrength="unsupported_private",
            unsupportedClaims=["private-source evidence"],
        )
    if "large production kubernetes platform" in lower_question or "owned a large production" in lower_question:
        return ChatResponse(
            answer=(
                "The current public source does not support a claim that Ryan owned a large production Kubernetes "
                "platform at a company. It supports lab/public-project Kubernetes and EKS/GitOps evidence in "
                "`aws-devops-lab` and `airgap-aiops`."
            ),
            citations=[],
            evidenceStrength="unsupported",
            unsupportedClaims=["owned a large production Kubernetes platform at a company"],
        )
    return None


def _apply_question_guardrails(question: str, response: ChatResponse) -> ChatResponse:
    lower_question = question.lower()
    if "container orchestration" in lower_question and {"aws-devops-lab README", "airgap-aiops README"}.issubset(response.citations):
        return ChatResponse(
            answer=response.answer,
            citations=response.citations,
            evidenceStrength="medium_high_lab_project",
            unsupportedClaims=response.unsupportedClaims,
        )
    return response


def handle_chat(
    payload: dict[str, Any],
    *,
    bedrock_client: Any,
    profile_text: str,
    settings: ChatbotSettings | None = None,
) -> dict[str, Any]:
    settings = settings or ChatbotSettings()
    try:
        question = _extract_question(payload, settings)
    except ChatValidationError:
        return {"error": "validation_error"}

    canned_response = _guardrail_response(question)
    if canned_response is not None:
        return canned_response.to_dict()

    sanitized_profile = sanitize_source_text(profile_text)
    try:
        response = bedrock_client.converse(
            modelId=settings.model_id,
            messages=build_messages(question=question, sanitized_profile=sanitized_profile),
            inferenceConfig={"maxTokens": settings.max_tokens},
            requestMetadata={"request_class": "chat"},
        )
        response_payload = _parse_json_object(_extract_text(response))
        validated = validate_chat_response(response_payload)
        return _apply_question_guardrails(question, validated).to_dict()
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ResponseContractError):
        logger.exception("chat response failed validation")
        return {"error": "validation_error"}
    except Exception:
        logger.exception("bedrock converse failed")
        return {"error": "bedrock_unavailable"}


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        body = {}

    try:
        import boto3

        settings = ChatbotSettings()
        bedrock_client = boto3.client("bedrock-runtime")
        source = load_profile_source(settings.profile_source_path, max_chars=settings.profile_source_max_chars)
        payload = handle_chat(body, bedrock_client=bedrock_client, profile_text=source.sanitized_text, settings=settings)
    except Exception:
        logger.exception("chat source setup failed")
        payload = {"error": "source_unavailable"}

    status_code = 200
    if payload.get("error") == "validation_error":
        status_code = 400
    elif payload.get("error") in {"bedrock_unavailable", "source_unavailable"}:
        status_code = 503

    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }
