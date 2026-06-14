"""Azure Blob Storage persistence for immutable Bronze responses."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone


def build_blob_path(source_name: str, run_id: str, retrieved_at: datetime) -> str:
    """Build a partitioned Bronze object path."""
    timestamp = retrieved_at.astimezone(timezone.utc)
    return (
        f"{source_name}/year={timestamp:%Y}/month={timestamp:%m}/"
        f"day={timestamp:%d}/{run_id}.json"
    )


def upload_raw_response(
    *,
    connection_string: str,
    container_name: str,
    blob_path: str,
    content: bytes,
) -> str:
    """Upload one immutable raw API response and return its SHA-256 hash."""
    from azure.storage.blob import BlobServiceClient, ContentSettings

    service = BlobServiceClient.from_connection_string(connection_string)
    container = service.get_container_client(container_name)
    blob = container.get_blob_client(blob_path)
    digest = hashlib.sha256(content).hexdigest()
    blob.upload_blob(
        content,
        overwrite=False,
        metadata={"sha256": digest},
        content_settings=ContentSettings(content_type="application/json"),
    )
    return digest
