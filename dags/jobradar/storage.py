"""Raw layer on S3-compatible storage (SeaweedFS locally, any S3 later).

Layout:  s3://<bucket>/source=<source>/snapshot_date=<YYYY-MM-DD>/<fetched_at>.json.gz
Each object is an envelope with metadata + the untouched source records.
Objects are never modified - re-processing always starts from here.
"""
from __future__ import annotations

import gzip
import json
import os
from datetime import datetime

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


def _client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
    )


def bucket_name() -> str:
    return os.environ.get("S3_RAW_BUCKET", "jobradar-raw")


def ensure_bucket() -> None:
    s3, bucket = _client(), bucket_name()
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError:
        s3.create_bucket(Bucket=bucket)


def raw_key(source: str, fetched_at: datetime) -> str:
    return (
        f"source={source}/snapshot_date={fetched_at:%Y-%m-%d}/"
        f"{fetched_at:%Y%m%dT%H%M%SZ}.json.gz"
    )


def put_envelope(key: str, envelope: dict) -> None:
    body = gzip.compress(json.dumps(envelope, ensure_ascii=False).encode("utf-8"))
    _client().put_object(
        Bucket=bucket_name(), Key=key, Body=body,
        ContentType="application/json", ContentEncoding="gzip",
    )


def get_envelope(key: str) -> dict:
    obj = _client().get_object(Bucket=bucket_name(), Key=key)
    return json.loads(gzip.decompress(obj["Body"].read()).decode("utf-8"))
