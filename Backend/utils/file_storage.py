"""
File Storage — supports Local disk and S3-compatible (AWS S3, Cloudflare R2, MinIO).
Set STORAGE_BACKEND=s3 in .env to enable S3.
"""
import hashlib
import uuid
import io
import logging
from pathlib import Path
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png"}


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(
    file_bytes: bytes,
    original_name: str,
    org_id: int,
    mime_type: str = "application/pdf",
) -> tuple[str, str, str]:
    """
    Save file to configured backend (local or S3).
    Returns (file_path_or_s3_key, file_name, sha256_hash).
    """
    ext = ALLOWED_TYPES.get(mime_type, Path(original_name).suffix or ".pdf")
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    backend = getattr(settings, "STORAGE_BACKEND", "local").lower()

    if backend == "s3":
        key = _save_to_s3(file_bytes, unique_name, org_id, mime_type)
        return key, unique_name, file_hash
    else:
        path = _save_local(file_bytes, unique_name, org_id)
        return path, unique_name, file_hash


def _save_local(file_bytes: bytes, unique_name: str, org_id: int) -> str:
    upload_dir = Path(settings.UPLOAD_DIR) / str(org_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / unique_name
    dest.write_bytes(file_bytes)
    return str(dest)


def _save_to_s3(file_bytes: bytes, unique_name: str, org_id: int, mime_type: str) -> str:
    """Upload to S3-compatible storage. Returns S3 key."""
    try:
        import boto3
        from botocore.exceptions import ClientError

        s3_key = f"cvs/{org_id}/{unique_name}"
        bucket = getattr(settings, "S3_BUCKET", "talentai-cvs")
        region = getattr(settings, "AWS_REGION", "us-east-1")
        endpoint = getattr(settings, "S3_ENDPOINT_URL", None)  # for R2/MinIO

        s3 = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint,
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", ""),
        )
        s3.upload_fileobj(
            io.BytesIO(file_bytes),
            bucket,
            s3_key,
            ExtraArgs={"ContentType": mime_type},
        )
        logger.info(f"Uploaded to S3: {s3_key}")
        return s3_key
    except Exception as e:
        logger.error(f"S3 upload failed, falling back to local: {e}")
        return _save_local(file_bytes, unique_name, org_id)


def read_file(file_path: str) -> bytes:
    """Read file from local or S3."""
    backend = getattr(settings, "STORAGE_BACKEND", "local").lower()
    if backend == "s3" and not file_path.startswith("/"):
        return _read_from_s3(file_path)
    return Path(file_path).read_bytes()


def _read_from_s3(s3_key: str) -> bytes:
    import boto3
    bucket = getattr(settings, "S3_BUCKET", "talentai-cvs")
    endpoint = getattr(settings, "S3_ENDPOINT_URL", None)
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", ""),
    )
    buf = io.BytesIO()
    s3.download_fileobj(bucket, s3_key, buf)
    buf.seek(0)
    return buf.read()


def get_file_url(file_path: str, expiry: int = 3600) -> str:
    """Get URL — presigned URL for S3, or local path for local."""
    backend = getattr(settings, "STORAGE_BACKEND", "local").lower()
    if backend == "s3" and not file_path.startswith("/"):
        return _presigned_url(file_path, expiry)
    return f"{settings.BASE_URL}/api/v1/candidates/file/{Path(file_path).name}"


def _presigned_url(s3_key: str, expiry: int) -> str:
    try:
        import boto3
        bucket = getattr(settings, "S3_BUCKET", "talentai-cvs")
        endpoint = getattr(settings, "S3_ENDPOINT_URL", None)
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", ""),
        )
        return s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": s3_key}, ExpiresIn=expiry
        )
    except Exception as e:
        logger.error(f"Presigned URL failed: {e}")
        return ""


def generate_qr_base64(url: str) -> str:
    try:
        import qrcode
        import base64
        qr = qrcode.QRCode(version=1, box_size=6, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except ImportError:
        return ""
