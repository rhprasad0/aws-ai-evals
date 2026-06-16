from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_SOURCE_LABELS = frozenset(
    {
        "content/profile.md",
        "GitHub Profile README",
        "aws-devops-lab README",
        "airgap-aiops README",
        "agent2agent-guestbook README",
        "closed-loop-ai-podcast README",
        "aws-ai-evals README",
        "ai-tamperguard README",
        "policy-bonfire-2 README",
    }
)

CITATION_ALIASES = {
    "https://github.com/rhprasad0/rhprasad0": "GitHub Profile README",
    "https://github.com/rhprasad0/aws-devops-lab": "aws-devops-lab README",
    "https://github.com/rhprasad0/airgap-aiops": "airgap-aiops README",
    "https://github.com/rhprasad0/agent2agent-guestbook": "agent2agent-guestbook README",
    "https://github.com/rhprasad0/closed-loop-ai-podcast": "closed-loop-ai-podcast README",
    "https://github.com/rhprasad0/aws-ai-evals": "aws-ai-evals README",
    "https://github.com/rhprasad0/ai-tamperguard": "ai-tamperguard README",
    "https://github.com/rhprasad0/policy-bonfire-2": "policy-bonfire-2 README",
    "rhprasad0/rhprasad0": "GitHub Profile README",
    "aws-devops-lab": "aws-devops-lab README",
    "airgap-aiops": "airgap-aiops README",
    "agent2agent-guestbook": "agent2agent-guestbook README",
    "closed-loop-ai-podcast": "closed-loop-ai-podcast README",
    "aws-ai-evals": "aws-ai-evals README",
    "ai-tamperguard": "ai-tamperguard README",
    "policy-bonfire-2": "policy-bonfire-2 README",
}

ALLOWED_EVIDENCE_STRENGTHS = frozenset(
    {
        "high_public_project",
        "medium_high_public_project",
        "medium_high_lab_project",
        "calibration_required",
        "weak_support",
        "unsupported",
        "unsupported_private",
    }
)


class ResponseContractError(ValueError):
    """Raised when a chatbot response violates the public response contract."""


@dataclass(frozen=True)
class ChatResponse:
    answer: str
    citations: list[str]
    evidenceStrength: str
    unsupportedClaims: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "citations": self.citations,
            "evidenceStrength": self.evidenceStrength,
            "unsupportedClaims": self.unsupportedClaims,
        }


def _normalize_citation(citation: str) -> str:
    stripped = citation.strip().strip("`").rstrip("/")
    return CITATION_ALIASES.get(stripped, stripped)


def validate_chat_response(payload: dict[str, Any]) -> ChatResponse:
    answer = payload.get("answer")
    citations = payload.get("citations")
    evidence_strength = payload.get("evidenceStrength")
    unsupported_claims = payload.get("unsupportedClaims")

    if not isinstance(answer, str) or not answer.strip():
        raise ResponseContractError("answer must be a non-empty string")
    if not isinstance(citations, list) or not all(isinstance(item, str) for item in citations):
        raise ResponseContractError("citations must be a list of strings")
    normalized_citations = [_normalize_citation(item) for item in citations]
    unknown_citations = sorted(set(normalized_citations) - ALLOWED_SOURCE_LABELS)
    if unknown_citations:
        raise ResponseContractError(f"citations contain unknown labels: {unknown_citations}")
    if evidence_strength not in ALLOWED_EVIDENCE_STRENGTHS:
        raise ResponseContractError(f"evidenceStrength is not allowed: {evidence_strength}")
    if not isinstance(unsupported_claims, list) or not all(isinstance(item, str) for item in unsupported_claims):
        raise ResponseContractError("unsupportedClaims must be a list of strings")

    return ChatResponse(
        answer=answer.strip(),
        citations=normalized_citations,
        evidenceStrength=evidence_strength,
        unsupportedClaims=unsupported_claims,
    )
