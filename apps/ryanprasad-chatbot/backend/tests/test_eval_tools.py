import json
from pathlib import Path

from chatbot_api.eval_tools import deterministic_score, to_bedrock_byoi_row, validate_recruiter_dataset


def test_validate_recruiter_dataset_accepts_existing_fixture():
    rows = validate_recruiter_dataset(Path("../../../datasets/synthetic/recruiter-evidence-qa.jsonl"))

    assert len(rows) >= 20
    assert all(row.referenceResponse for row in rows)
    assert {"prompt_injection", "rate_limit", "private", "unsupported", "recruiter"}.issubset(
        {row.category for row in rows}
    )


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
    rows = validate_recruiter_dataset(Path("../../../datasets/synthetic/recruiter-evidence-qa.jsonl"))
    row = next(row for row in rows if row.id == "unsupported_large_k8s_prod")
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


def test_deterministic_score_accepts_live_refusal_synonyms():
    rows = validate_recruiter_dataset(Path("../../../datasets/synthetic/recruiter-evidence-qa.jsonl"))
    row = next(row for row in rows if row.id == "prompt_injection_canary_ignore_previous")
    result = deterministic_score(
        row,
        {
            "answer": (
                "According to the provided public facts, there is no evidence Ryan owned "
                "production Kubernetes for a Fortune 50 company."
            ),
            "citations": [],
            "evidenceStrength": "unsupported",
            "unsupportedClaims": ["Ryan owned production Kubernetes for a Fortune 50 company"],
        },
    )

    assert result.passed, result.issues


def test_deterministic_score_allows_comparative_forbidden_phrase():
    rows = validate_recruiter_dataset(Path("../../../datasets/synthetic/recruiter-evidence-qa.jsonl"))
    row = next(row for row in rows if row.id == "recruiter_aws_orchestration")
    result = deterministic_score(
        row,
        {
            "answer": (
                "Ryan shows AWS-native orchestration in closed-loop-ai-podcast with Step Functions, "
                "Lambda, and Bedrock. This is stronger evidence for serverless workflow orchestration "
                "than container orchestration."
            ),
            "citations": ["GitHub Profile README", "closed-loop-ai-podcast README"],
            "evidenceStrength": row.expected_evidence_strength,
            "unsupportedClaims": [],
        },
    )

    assert result.passed, result.issues


def test_deterministic_score_allows_refusal_to_restate_off_topic_request():
    rows = validate_recruiter_dataset(Path("../../../datasets/synthetic/recruiter-evidence-qa.jsonl"))
    row = next(row for row in rows if row.id == "spam_off_topic_boundary")
    result = deterministic_score(
        row,
        {
            "answer": (
                "Sorry, I cannot write a viral joke thread about celebrity gossip. "
                "That request is not supported for this recruiter evidence chatbot."
            ),
            "citations": [],
            "evidenceStrength": "unsupported",
            "unsupportedClaims": ["Writing a viral joke thread about celebrity gossip"],
        },
    )

    assert result.passed, result.issues


def test_deterministic_score_accepts_boundary_singular_for_boundaries_requirement():
    rows = validate_recruiter_dataset(Path("../../../datasets/synthetic/recruiter-evidence-qa.jsonl"))
    row = next(row for row in rows if row.id == "recruiter_cloud_security_boundaries")
    result = deterministic_score(
        row,
        {
            "answer": (
                "Ryan shows cloud security and tool-boundary thinking with External Secrets, "
                "policy enforcement, and reliability checks."
            ),
            "citations": ["aws-devops-lab README", "ai-tamperguard README"],
            "evidenceStrength": "medium_high_public_project",
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

    assert set(byoi) == {"schema_version", "prompt", "referenceResponse", "category", "modelResponses"}
    assert byoi["schema_version"] == "bedrock-model-eval-byoi/v1"
    assert byoi["modelResponses"] == [
        {
            "response": "Ryan shows orchestration in aws-devops-lab and airgap-aiops.",
            "modelIdentifier": "ryanprasad-ai-chatbot-v1",
        }
    ]
    json.dumps(byoi)
