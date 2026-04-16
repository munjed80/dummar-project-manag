"""Shared utilities for file field serialization/deserialization in schemas."""

import json
from typing import Optional, List


def parse_file_list(v: object) -> Optional[List[str]]:
    """Parse a DB text value (JSON array or comma-separated) into a list.

    Used as a Pydantic field_validator for file reference fields stored as
    Text columns in the database.  Canonical storage format is JSON array;
    comma-separated is accepted for backward compatibility.
    """
    if v is None:
        return None
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except (json.JSONDecodeError, ValueError):
            pass
        return [x.strip() for x in v.split(",") if x.strip()]
    return None


def serialize_file_list(file_list: Optional[List[str]]) -> Optional[str]:
    """Serialize a list of file paths to a JSON string for DB storage."""
    if file_list is None:
        return None
    return json.dumps(file_list)
