import os
import uuid
from contextlib import asynccontextmanager

from aioboto3.session import Session
from fastapi import UploadFile


class S3Client:
    def __init__(self):
        self.session = Session()
        self.bucket: str = "clay-shop-bucket"
        self.endpoint: str = "https://s3.cloud.ru"
        self.access_key: str = (
            f"{os.getenv("S3_TENANT_ID", "")}:{os.getenv("S3_KEY_ID", "")}"
        )
        self.secret_key: str = os.getenv("S3_KEY_SECRET", "")
        self.region = "ru-central-1"

    @asynccontextmanager
    async def get_client(self):
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        ) as client:
            yield client

    async def get_file(self, s3_key: str) -> bytes:
        async with self.get_client() as s3:
            response = await s3.get_object(Bucket=self.bucket, Key=s3_key)
            return await response["Body"].read()

    async def list_files(self, prefix: str = "") -> list:
        async with self.get_client() as s3:
            response = await s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]

    # Для Ws Friendly чата
    async def upload_file(self, file: UploadFile):
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        mime_type = file.content_type
        if mime_type.startswith("image/"):
            s3_key = f"media/images/{unique_filename}"
        elif mime_type.startswith("video/"):
            s3_key = f"media/videos/{unique_filename}"
        else:
            s3_key = f"media/files/{unique_filename}"

        content = await file.read()
        async with self.get_client() as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=content,
                ContentType=mime_type,
            )
        file_url = f"https://clay-shop.s3.cloud.ru/{s3_key}"
        return {
            "file_url": file_url,
            "mime_type": mime_type.split("/")[0] if "/" in mime_type else "file",
        }

    # Для аватарок
    async def upload_avatar(self, file: UploadFile):
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        mime_type = file.content_type
        s3_key = f"media/users/photos/{unique_filename}"
        content = await file.read()
        async with self.get_client() as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=content,
                ContentType=mime_type,
            )
        file_url = f"https://clay-shop.s3.cloud.ru/{s3_key}"
        return {
            "file_url": file_url,
            "mime_type": mime_type.split("/")[0] if "/" in mime_type else "file",
        }


s3_client = S3Client()
