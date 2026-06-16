from chatbot_api.rate_limit import build_rate_limit_key


def test_build_rate_limit_key_hashes_identity_and_buckets_time():
    key = build_rate_limit_key("203.0.113.10", "session-1", salt="public-test-salt", now_epoch=3601)

    assert key["pk"].startswith("identity#")
    assert "203.0.113.10" not in key["pk"]
    assert "session-1" not in key["pk"]
    assert key["sk"] == "window#hour#1"
    assert key["ttl"] > 3601
