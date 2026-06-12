import boto3
from botocore.client import Config
from src.config import MinioConfig


def get_minio_client():
    """
    Retourne un client boto3 configuré pour MinIO.
    Compatible S3 — fonctionne avec tout bucket MinIO local.
    """
    return boto3.client(
        "s3",
        endpoint_url=f"http://{MinioConfig.ENDPOINT}",
        aws_access_key_id=MinioConfig.ACCESS_KEY,
        aws_secret_access_key=MinioConfig.SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket_exists(client, bucket_name: str) -> None:
    """
    Crée le bucket s'il n'existe pas déjà.
    Appelé au démarrage de chaque layer.
    """
    existing = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
    if bucket_name not in existing:
        client.create_bucket(Bucket=bucket_name)