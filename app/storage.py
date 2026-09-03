"""AWS S3 storage for project-scoped podcast audio files."""

from __future__ import annotations

import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME", "rankify-image-generator")
PRESIGNED_URL_EXPIRY = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))
S3_USE_PUBLIC_URLS = os.getenv("S3_USE_PUBLIC_URLS", "false").lower() in ("1", "true", "yes")
VOICE_S3_PREFIX = os.getenv("VOICE_S3_PREFIX", "voices")

s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID or None,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY or None,
)


def podcast_s3_key(project_id: str, podcast_id: str) -> str:
    return f"projects/{project_id}/podcasts/{podcast_id}.wav"


def voice_s3_key(voice_id: str) -> str:
    return f"{VOICE_S3_PREFIX}/{voice_id.lower()}.wav"


def public_s3_url(s3_key: str) -> str:
    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"


def audio_url(s3_key: str, expiry: int = PRESIGNED_URL_EXPIRY) -> str:
    if S3_USE_PUBLIC_URLS:
        return public_s3_url(s3_key)
    return presigned_url(s3_key, expiry=expiry)


def upload_podcast(local_path: str, project_id: str, podcast_id: str) -> str:
    key = podcast_s3_key(project_id, podcast_id)
    s3_client.upload_file(
        Filename=local_path,
        Bucket=S3_BUCKET_NAME,
        Key=key,
        ExtraArgs={"ContentType": "audio/wav"},
    )
    return key


def upload_voice_sample(local_path: str, voice_id: str) -> str:
    key = voice_s3_key(voice_id)
    s3_client.upload_file(
        Filename=local_path,
        Bucket=S3_BUCKET_NAME,
        Key=key,
        ExtraArgs={"ContentType": "audio/wav"},
    )
    return key


def presigned_url(s3_key: str, expiry: int = PRESIGNED_URL_EXPIRY) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expiry,
    )


def head_object(s3_key: str) -> dict:
    return s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)


def delete_object(s3_key: str) -> None:
    s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)


def delete_project_podcasts(project_id: str) -> int:
    prefix = f"projects/{project_id}/"
    deleted = 0
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []):
            s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=obj["Key"])
            deleted += 1
    return deleted


def object_exists(s3_key: str) -> bool:
    try:
        head_object(s3_key)
        return True
    except ClientError:
        return False
