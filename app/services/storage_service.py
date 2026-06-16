import uuid
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

_s3 = None

def _get_client():
    global _s3
    if _s3 is None:
        _s3 = boto3.client(
            "s3",
            endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
    return _s3


def _ensure_bucket() -> None:
    client = _get_client()
    bucket = settings.MINIO_BUCKET
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)
        client.put_bucket_policy(
            Bucket=bucket,
            Policy=f'{{"Version":"2012-10-17","Statement":[{{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::{bucket}/*"}}]}}',
        )
        logger.info("minio_bucket_created", bucket=bucket)


async def upload_file(file: UploadFile, folder: str = "spaces") -> str:
    import asyncio

    _ensure_bucket()
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() or "jpg"
    key = f"{folder}/{uuid.uuid4()}.{ext}"
    content = await file.read()

    def _put():
        _get_client().put_object(
            Bucket=settings.MINIO_BUCKET,
            Key=key,
            Body=content,
            ContentType=file.content_type or "image/jpeg",
        )

    await asyncio.to_thread(_put)
    return f"/storage/{key}"


def delete_file(key: str) -> None:
    try:
        _get_client().delete_object(Bucket=settings.MINIO_BUCKET, Key=key)
    except Exception as e:
        logger.warning("minio_delete_error", key=key, error=str(e))
