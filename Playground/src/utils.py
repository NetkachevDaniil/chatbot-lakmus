import os
import re


def sanitize_bucket_name(value: str) -> str:
    cleaned = value.lower()
    cleaned = re.sub(r"[^a-z0-9-]", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    if len(cleaned) < 3:
        cleaned = f"usr-{cleaned or 'bucket'}"
    if len(cleaned) > 63:
        cleaned = cleaned[:63].rstrip("-")
    return cleaned


def detect_file_format(filename: str) -> str:
    _, ext = os.path.splitext(filename or "")
    return (ext.lstrip(".") or "unknown").lower()


__all__ = ["sanitize_bucket_name", "detect_file_format"]
