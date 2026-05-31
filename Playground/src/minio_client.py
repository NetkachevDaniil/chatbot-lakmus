from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from .config import Settings


def build_minio_client(settings: Settings) -> Minio:
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_and_get_link(
    client: Minio,
    bucket: str,
    object_name: str,
    data,
    content_type: str,
    ttl_hours: int,
) -> str:
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=data,
        length=-1,
        part_size=10 * 1024 * 1024,
        content_type=content_type or "application/octet-stream",
    )
    return client.presigned_get_object(
        bucket_name=bucket,
        object_name=object_name,
        expires=timedelta(hours=ttl_hours),
    )


__all__ = ["S3Error", "build_minio_client", "ensure_bucket", "upload_and_get_link"]
