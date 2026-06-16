#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any


def _status(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"check": name, "ok": ok, "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run opt-in Bedrock preflight checks for the candidate chatbot.")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--model-id", default="us.amazon.nova-2-lite-v1:0")
    parser.add_argument("--max-tokens", type=int, default=768)
    parser.add_argument("--skip-smoke", action="store_true", help="Skip the live Converse smoke call.")
    args = parser.parse_args()

    try:
        import boto3
    except ImportError:
        print(json.dumps({"ok": False, "error": "boto3 is required for live Bedrock preflight"}, indent=2))
        return 2

    bedrock = boto3.client("bedrock", region_name=args.region)
    runtime = boto3.client("bedrock-runtime", region_name=args.region)

    checks = []
    try:
        models = bedrock.list_foundation_models(byProvider="Amazon", byOutputModality="TEXT")
        model_ids = [model.get("modelId", "") for model in models.get("modelSummaries", [])]
        checks.append(_status("ListFoundationModels", True, f"amazon_text_models={len(model_ids)}"))
    except Exception as exc:
        checks.append(_status("ListFoundationModels", False, type(exc).__name__))

    try:
        profiles = bedrock.list_inference_profiles(typeEquals="SYSTEM_DEFINED")
        profile_ids = [profile.get("inferenceProfileId", "") for profile in profiles.get("inferenceProfileSummaries", [])]
        checks.append(_status("ListInferenceProfiles", args.model_id in profile_ids, f"profiles={len(profile_ids)}"))
    except Exception as exc:
        checks.append(_status("ListInferenceProfiles", False, type(exc).__name__))

    try:
        profile = bedrock.get_inference_profile(inferenceProfileIdentifier=args.model_id)
        checks.append(_status("GetInferenceProfile", profile.get("status") == "ACTIVE", profile.get("status", "unknown")))
    except Exception as exc:
        checks.append(_status("GetInferenceProfile", False, type(exc).__name__))

    if not args.skip_smoke:
        try:
            runtime.converse(
                modelId=args.model_id,
                messages=[{"role": "user", "content": [{"text": "Reply with ok."}]}],
                inferenceConfig={"maxTokens": min(args.max_tokens, 16)},
                requestMetadata={"request_class": "preflight"},
            )
            checks.append(_status("ConverseSmoke", True, "ok"))
        except Exception as exc:
            checks.append(_status("ConverseSmoke", False, type(exc).__name__))

    ok = all(check["ok"] for check in checks)
    print(json.dumps({"ok": ok, "region": args.region, "model_id": args.model_id, "checks": checks}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
