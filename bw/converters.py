import datetime
from typing import Any


def make_json_safe(json: dict[str, Any]):
    json_safe: dict[str, Any] = {}
    for key, value in json.items():
        safe_value = value
        if isinstance(value, dict):
            safe_value = make_json_safe(value)
        elif isinstance(value, datetime.datetime):
            safe_value = value.isoformat()

        json_safe[key] = safe_value
    return json_safe
