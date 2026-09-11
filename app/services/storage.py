import os

from minio import Minio


# =========================================================
# MINIO CONFIG
# =========================================================

MINIO_ENDPOINT = os.getenv(
    "MINIO_ENDPOINT",
    "localhost:9000"
)

MINIO_ACCESS_KEY = os.getenv(
    "MINIO_ACCESS_KEY",
    "admin"
)

MINIO_SECRET_KEY = os.getenv(
    "MINIO_SECRET_KEY",
    "admin12345"
)

BUCKET_NAME = os.getenv(
    "MINIO_BUCKET_NAME",
    "files"
)


# =========================================================
# MINIO CLIENT
# =========================================================

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)


# =========================================================
# CREATE BUCKET
# =========================================================

def create_bucket():

    if not client.bucket_exists(
        BUCKET_NAME
    ):

        client.make_bucket(
            BUCKET_NAME
        )


# =========================================================
# UPLOAD FILE
# =========================================================

def upload_file(
    file_path: str,
    object_name: str,
    content_type: str
):

    client.fput_object(
        bucket_name=BUCKET_NAME,
        object_name=object_name,
        file_path=file_path,
        content_type=content_type
    )


# =========================================================
# DELETE FILE
# =========================================================

def delete_file(
    object_name: str
):

    client.remove_object(
        BUCKET_NAME,
        object_name
    )


# =========================================================
# GET FILE
# =========================================================

def get_file(
    object_name: str
):

    return client.get_object(
        BUCKET_NAME,
        object_name
    )