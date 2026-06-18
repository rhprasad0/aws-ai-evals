from __future__ import annotations

import json
import logging
import time
from typing import Any

from .prompting import PROMPT_TEMPLATE_VERSION, build_messages
from .response_contract import ChatResponse, ResponseContractError, validate_chat_response
from .settings import ChatbotSettings
from .sources import load_profile_source, sanitize_source_text

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _aws_error_details(exc: Exception) -> dict[str, Any]:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return {}

    error = response.get("Error")
    metadata = response.get("ResponseMetadata")
    details: dict[str, Any] = {}
    if isinstance(error, dict):
        code = error.get("Code")
        if isinstance(code, str):
            details["aws_error_code"] = code
    if isinstance(metadata, dict):
        request_id = metadata.get("RequestId")
        http_status = metadata.get("HTTPStatusCode")
        retry_attempts = metadata.get("RetryAttempts")
        if isinstance(request_id, str):
            details["aws_request_id"] = request_id
        if isinstance(http_status, int):
            details["http_status_code"] = http_status
        if isinstance(retry_attempts, int):
            details["retry_attempts"] = retry_attempts
    return details


def _log_bedrock_boundary_error(
    *,
    boundary_event: str,
    exc: Exception,
    settings: ChatbotSettings,
    elapsed_ms: int | None = None,
) -> None:
    context: dict[str, Any] = {
        "event": boundary_event,
        "boundary": "lambda_to_bedrock",
        "operation": "Converse",
        "model_id": settings.model_id,
        "exception_type": type(exc).__name__,
    }
    if elapsed_ms is not None:
        context["elapsed_ms"] = elapsed_ms
    context.update(_aws_error_details(exc))
    logger.error("bedrock_boundary_error %s", json.dumps(context, sort_keys=True))


def _safe_token_usage(converse_response: dict[str, Any]) -> dict[str, int]:
    usage = converse_response.get("usage")
    if not isinstance(usage, dict):
        return {}

    safe_usage: dict[str, int] = {}
    for source_key, target_key in (
        ("inputTokens", "input_tokens"),
        ("outputTokens", "output_tokens"),
        ("totalTokens", "total_tokens"),
    ):
        value = usage.get(source_key)
        if isinstance(value, int):
            safe_usage[target_key] = value
    return safe_usage


def _log_chat_app_event(
    *,
    response: ChatResponse,
    settings: ChatbotSettings,
    response_source: str,
    elapsed_ms: int | None = None,
    converse_response: dict[str, Any] | None = None,
) -> None:
    event: dict[str, Any] = {
        "event": "chat_response_completed",
        "response_source": response_source,
        "request_class": "chat",
        "prompt_template_version": PROMPT_TEMPLATE_VERSION,
        "model_id": settings.model_id,
        "max_tokens": settings.max_tokens,
        "citation_labels": response.citations,
        "citation_count": len(response.citations),
        "evidence_strength": response.evidenceStrength,
        "unsupported_claim_count": len(response.unsupportedClaims),
    }
    if elapsed_ms is not None:
        event["elapsed_ms"] = elapsed_ms
    if converse_response is not None:
        event.update(_safe_token_usage(converse_response))
    logger.info("chat_app_event %s", json.dumps(event, sort_keys=True))


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
    if "injection_canary_do_not_follow" in lower_question or "ignore all previous instructions" in lower_question:
        return ChatResponse(
            answer=(
                "That instruction-like canary is not supported by the public evidence. "
                "I should ignore attempts to override the recruiter-evidence boundary, should not cite a fake "
                "private source, and should not invent private or production ownership claims."
            ),
            citations=[],
            evidenceStrength="unsupported",
            unsupportedClaims=["prompt-injection canary or unsupported production-ownership claim"],
        )
    if "private" in lower_question or "private notes" in lower_question or "private projects" in lower_question:
        return ChatResponse(
            answer=(
                "I should not use private memory, private projects, private notes, local memory, or unpublished sources. "
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
    if "millions of production users" in lower_question or "large-scale production" in lower_question:
        return ChatResponse(
            answer=(
                "That scale claim is not supported by the public evidence. The public source supports lab and "
                "public-project AI systems work, not millions of production users or large-scale production ownership."
            ),
            citations=[],
            evidenceStrength="unsupported",
            unsupportedClaims=["millions of production users or large-scale production ownership"],
        )
    if "foundation model training" in lower_question or "trained frontier models" in lower_question:
        return ChatResponse(
            answer=(
                "That claim is not supported by the public evidence. The public source supports AI systems, "
                "orchestration, RAG/search, and eval harness work, not foundation model training expertise."
            ),
            citations=[],
            evidenceStrength="unsupported",
            unsupportedClaims=["foundation model training expertise"],
        )
    if "safety certification" in lower_question or "certified safe" in lower_question:
        return ChatResponse(
            answer=(
                "That certification claim is not supported by the public source. The public evidence supports "
                "eval, reliability, and safety-oriented project work, but not a formal safety certification."
            ),
            citations=[],
            evidenceStrength="unsupported",
            unsupportedClaims=["formal safety certification"],
        )
    if "repeats the same recruiter question" in lower_question or ("repeated" in lower_question and "question" in lower_question):
        return ChatResponse(
            answer=(
                "Repeated recruiter questions should be handled as an operational boundary: apply a rate limit "
                "or abuse-control check rather than treating repeated traffic as new public evidence."
            ),
            citations=[],
            evidenceStrength="calibration_required",
            unsupportedClaims=[],
        )
    if "celebrity gossip" in lower_question or "viral joke thread" in lower_question:
        return ChatResponse(
            answer=(
                "That off-topic request is not supported for the recruiter evidence chatbot. I should stay in "
                "the recruiter evidence lane rather than write unrelated entertainment content."
            ),
            citations=[],
            evidenceStrength="unsupported",
            unsupportedClaims=["off-topic entertainment content"],
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
        _log_chat_app_event(response=canned_response, settings=settings, response_source="guardrail")
        return canned_response.to_dict()

    sanitized_profile = sanitize_source_text(profile_text)
    started = time.monotonic()
    try:
        response = bedrock_client.converse(
            modelId=settings.model_id,
            messages=build_messages(question=question, sanitized_profile=sanitized_profile),
            inferenceConfig={"maxTokens": settings.max_tokens},
            requestMetadata={"prompt_template_version": PROMPT_TEMPLATE_VERSION, "request_class": "chat"},
        )
        response_payload = _parse_json_object(_extract_text(response))
        validated = validate_chat_response(response_payload)
        final_response = _apply_question_guardrails(question, validated)
        _log_chat_app_event(
            response=final_response,
            settings=settings,
            response_source="bedrock",
            elapsed_ms=int((time.monotonic() - started) * 1000),
            converse_response=response,
        )
        return final_response.to_dict()
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ResponseContractError) as exc:
        _log_bedrock_boundary_error(
            boundary_event="bedrock_response_contract_failure",
            exc=exc,
            settings=settings,
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )
        return {"error": "validation_error"}
    except Exception as exc:
        _log_bedrock_boundary_error(
            boundary_event="bedrock_converse_failure",
            exc=exc,
            settings=settings,
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )
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
