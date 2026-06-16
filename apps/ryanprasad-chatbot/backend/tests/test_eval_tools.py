import json
from pathlib import Path

from chatbot_api.eval_tools import deterministic_score, to_bedrock_byoi_row, validate_recruiter_dataset


def test_validate_recruiter_dataset_accepts_existing_fixture():
    rows = validate_recruiter_dataset(Path("../../../datasets/synthetic/recruiter-evidence-qa.jsonl"))

    assert len(rows) == 8
    assert all(row.referenceResponse for row in rows)


def test_deterministic_score_catches_missing_required_citation():
    row = validate_recruiter_dataset(Path("../../../datasets/synthetic/recruiter-evidence-qa.jsonl"))[0]
    result = deterministic_score(
        row,
        {
            "answer": "Ryan shows EKS work.",
            "citations": ["aws-devops-lab README"],
            "evidenceStrength": "medium_high_lab_project",
            "unsupportedClaims": [],
        },
    )

    assert not result.passed
    assert any("missing expected source" in issue for issue in result.issues)


def test_deterministic_score_allows_negated_forbidden_claims():
    row = validate_recruiter_dataset(Path("../../../datasets/synthetic/recruiter-evidence-qa.jsonl"))[6]
    result = deterministic_score(
        row,
        {
            "answer": "The public source does not support that Ryan owned a large production Kubernetes platform.",
            "citations": [],
            "evidenceStrength": "unsupported",
            "unsupportedClaims": [],
        },
    )

    assert result.passed, result.issues


def test_to_bedrock_byoi_row_uses_single_model_response_shape():
    row = validate_recruiter_dataset(Path("../../../datasets/synthetic/recruiter-evidence-qa.jsonl"))[0]
    byoi = to_bedrock_byoi_row(
        row,
        response="Ryan shows orchestration in aws-devops-lab and airgap-aiops.",
        model_identifier="ryanprasad-ai-chatbot-v1",
    )

    assert set(byoi) == {"prompt", "referenceResponse", "category", "modelResponses"}
    assert byoi["modelResponses"] == [
        {
            "response": "Ryan shows orchestration in aws-devops-lab and airgap-aiops.",
            "modelIdentifier": "ryanprasad-ai-chatbot-v1",
        }
    ]
    json.dumps(byoi)
