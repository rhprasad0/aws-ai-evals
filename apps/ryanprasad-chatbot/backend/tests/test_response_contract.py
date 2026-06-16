import pytest

from chatbot_api.response_contract import (
    ALLOWED_EVIDENCE_STRENGTHS,
    ALLOWED_SOURCE_LABELS,
    ResponseContractError,
    validate_chat_response,
)


def test_validate_chat_response_accepts_grounded_response():
    response = validate_chat_response(
        {
            "answer": "Ryan shows Kubernetes work in aws-devops-lab and airgap-aiops.",
            "citations": ["aws-devops-lab README", "airgap-aiops README"],
            "evidenceStrength": "medium_high_lab_project",
            "unsupportedClaims": [],
        }
    )

    assert response.citations == ["aws-devops-lab README", "airgap-aiops README"]
    assert "medium_high_lab_project" in ALLOWED_EVIDENCE_STRENGTHS
    assert "GitHub Profile README" in ALLOWED_SOURCE_LABELS


def test_validate_chat_response_normalizes_known_github_urls():
    response = validate_chat_response(
        {
            "answer": "Ryan shows Kubernetes work in aws-devops-lab and airgap-aiops.",
            "citations": ["https://github.com/rhprasad0/aws-devops-lab", "https://github.com/rhprasad0/airgap-aiops"],
            "evidenceStrength": "medium_high_lab_project",
            "unsupportedClaims": [],
        }
    )

    assert response.citations == ["aws-devops-lab README", "airgap-aiops README"]


def test_validate_chat_response_rejects_unknown_citation():
    with pytest.raises(ResponseContractError, match="citations"):
        validate_chat_response(
            {
                "answer": "Unsupported citation.",
                "citations": ["private notes"],
                "evidenceStrength": "medium_high_lab_project",
                "unsupportedClaims": [],
            }
        )


def test_validate_chat_response_rejects_unknown_evidence_strength():
    with pytest.raises(ResponseContractError, match="evidenceStrength"):
        validate_chat_response(
            {
                "answer": "Bad strength.",
                "citations": [],
                "evidenceStrength": "production_owned",
                "unsupportedClaims": [],
            }
        )
