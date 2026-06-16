from chatbot_api.prompting import build_messages


def test_build_messages_wraps_profile_in_public_fact_delimiters():
    messages = build_messages(
        question="Where does Ryan show container orchestration?",
        sanitized_profile="Ryan shows EKS in aws-devops-lab.",
    )

    assert messages[0]["role"] == "user"
    content = messages[0]["content"][0]["text"]
    assert "PUBLIC FACTS START" in content
    assert "PUBLIC FACTS END" in content
    assert "Ryan shows EKS in aws-devops-lab." in content
    assert "Where does Ryan show container orchestration?" in content
