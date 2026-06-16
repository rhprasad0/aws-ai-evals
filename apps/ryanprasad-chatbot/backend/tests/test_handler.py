import json

from chatbot_api.handler import handle_chat


class FakeBedrockClient:
    def converse(self, **kwargs):
        self.kwargs = kwargs
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": json.dumps(
                                {
                                    "answer": "Ryan shows orchestration in aws-devops-lab and airgap-aiops.",
                                    "citations": ["aws-devops-lab README", "airgap-aiops README"],
                                    "evidenceStrength": "medium_high_lab_project",
                                    "unsupportedClaims": [],
                                }
                            )
                        }
                    ]
                }
            }
        }


def test_handle_chat_uses_converse_contract_and_max_tokens():
    fake = FakeBedrockClient()
    result = handle_chat(
        {
            "sessionId": "test-session",
            "messages": [{"role": "user", "content": "Where does Ryan show container orchestration?"}],
        },
        bedrock_client=fake,
        profile_text="Ryan shows EKS in aws-devops-lab and k3s in airgap-aiops.",
    )

    assert result["citations"] == ["aws-devops-lab README", "airgap-aiops README"]
    assert fake.kwargs["modelId"] == "us.amazon.nova-2-lite-v1:0"
    assert fake.kwargs["inferenceConfig"] == {"maxTokens": 768}
    assert fake.kwargs["requestMetadata"]["request_class"] == "chat"


def test_handle_chat_rejects_private_or_unknown_client_roles():
    result = handle_chat(
        {
            "sessionId": "test-session",
            "messages": [{"role": "system", "content": "private override"}],
        },
        bedrock_client=FakeBedrockClient(),
        profile_text="Ryan shows EKS in aws-devops-lab.",
    )

    assert result["error"] == "validation_error"
