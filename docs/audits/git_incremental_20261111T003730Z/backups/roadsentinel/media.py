"""Where keyframes and clips live: the local data/media folder, or an S3-compatible bucket in production.

Events store a media *key* like "demo-highway/event_000_very_high_speed.mp4"; the API serves it at /media/<key>.
The bucket is used when S3_BUCKET is set (plus S3_ENDPOINT, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_REGION).
"""
import mimetypes
import os
import shutil
from functools import lru_cache
from pathlib import Path

LOCAL_ROOT = Path(os.environ.get("RS_PIPELINE_WORK_DIR", ".")) / "data/media"


def bucket():
    return os.environ.get("S3_BUCKET")


@lru_cache
def _s3():
    import boto3

    return boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT"),
                        aws_access_key_id=os.environ.get("S3_ACCESS_KEY_ID"),
                        aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY"),
                        region_name=os.environ.get("S3_REGION", "auto"))


def key_for(path):
    """Media key for a file under data/media/."""
    return Path(path).resolve().relative_to(LOCAL_ROOT.resolve()).as_posix()


def local_path(key):
    """Path for a media key; refuses anything that would land outside data/media."""
    root = LOCAL_ROOT.resolve()
    p = (root / key).resolve()
    if not p.is_relative_to(root) or p == root:
        raise ValueError(f"invalid media key: {key}")
    return p


def save(key, fileobj):
    """Stream a file object into storage without loading it into memory."""
    if bucket():
        _s3().upload_fileobj(fileobj, bucket(), key,
                             ExtraArgs={"ContentType": mimetypes.guess_type(key)[0] or "application/octet-stream"})
    else:
        p = local_path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as out:
            shutil.copyfileobj(fileobj, out)


def presigned_url(key, seconds=3600):
    return _s3().generate_presigned_url("get_object", Params={"Bucket": bucket(), "Key": key}, ExpiresIn=seconds)


def delete_prefix(prefix):
    if bucket():
        s3 = _s3()
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket(), Prefix=prefix):
            objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objs:
                s3.delete_objects(Bucket=bucket(), Delete={"Objects": objs})
    else:
        for f in (LOCAL_ROOT / prefix).glob("*"):
            f.unlink()


def exists(key):
    if bucket():
        from botocore.exceptions import ClientError

        try:
            _s3().head_object(Bucket=bucket(), Key=key)
            return True
        except ClientError:
            return False
    try:
        return local_path(key).is_file()
    except ValueError:
        return False
