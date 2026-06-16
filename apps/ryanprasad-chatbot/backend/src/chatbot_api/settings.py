from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

DEFAULT_MODEL_ID = "us.amazon.nova-2-lite-v1:0"
DEFAULT_MAX_TOKENS = 768
PROFILE_SOURCE_MAX_CHARS = int(os.getenv("PROFILE_SOURCE_MAX_CHARS", "51200"))
MAX_CLIENT_MESSAGE_CHARS = 2000
MAX_MESSAGES = 8


@dataclass(frozen=True)
class ChatbotSettings:
    model_id: str = os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
    max_tokens: int = int(os.getenv("BEDROCK_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
    profile_source_max_chars: int = PROFILE_SOURCE_MAX_CHARS
    profile_source_path: Path = Path(os.getenv("PROFILE_SOURCE_PATH", "content/profile.md"))
    max_client_message_chars: int = MAX_CLIENT_MESSAGE_CHARS
    max_messages: int = MAX_MESSAGES
