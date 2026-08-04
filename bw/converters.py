import dataclasses
import datetime
import hashlib
import re
import string
import uuid
from pathlib import Path
from typing import Any

ALLOWED_PASSWORD_CHARACTERS = set(string.ascii_letters + string.digits + '!@#$%^&*-._~')
SECRET_REGEX_MATCH = re.compile('((?:password|token|secret)[\'"\\s :,]*)([a-zA-Z0-9!@#$%^&*-._~]+)')


def make_json_safe(json: Any):
    from bw.web_event.base import BaseEvent

    if json is None:
        return {}

    if dataclasses.is_dataclass(json):
        json = dataclasses.asdict(json)

    json_safe: dict[str, Any] = {}
    for key, value in json.items():
        safe_value = value
        if isinstance(value, dict):
            safe_value = make_json_safe(value)
        elif isinstance(value, datetime.datetime):
            safe_value = value.isoformat()
        elif isinstance(value, uuid.UUID):
            safe_value = str(value)
        elif isinstance(value, BaseEvent):
            safe_value = value.encoded_string()
        elif dataclasses.is_dataclass(value):
            safe_value = make_json_safe(dataclasses.asdict(value))

        json_safe[key] = safe_value
    return json_safe


def file_sha2(file_path: Path, *, buffer_size=2**20) -> str:
    with open(file_path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def sanitize_string_for_secrets(to_check: str, *, replace_character: str = '#', max_extra: int = 6) -> str:
    def replacer(match: re.Match) -> str:
        # try to hide meta information about the secret by obfuscuating the secret length through this hash algorithm
        secret_start, secret_end = match.span(2)
        secret_length = secret_end - secret_start

        secret_extra = (hash(match.group(2)) % (2 * max_extra)) - max_extra
        return match.group(1) + replace_character * max(1 + secret_length // 2, secret_length + secret_extra)

    return re.sub(SECRET_REGEX_MATCH, replacer, to_check)
