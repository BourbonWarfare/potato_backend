import datetime
import uuid
import dataclasses
import hashlib
from typing import Any
from pathlib import Path


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
    sha2 = hashlib.sha256()
    while True:
        with open(file_path, 'rb') as f:
            data = f.read(buffer_size)
            if not data:
                break
            sha2.update(data)
    return sha2.hexdigest()
