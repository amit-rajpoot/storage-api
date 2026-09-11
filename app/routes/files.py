from fastapi import (
    APIRouter,
    UploadFile,
    File as FastAPIFile,
    Depends,
    HTTPException,
    Query,
    Form,
    BackgroundTasks
)

from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session

import os
import shutil
import uuid

from app.db.database import get_db

from app.model.models import (
    File as FileModel,
    UploadSession
)

from app.schemas.schemas import FileResponse

from app.services.storage import (
    upload_file as upload_to_minio,
    get_file as get_file_from_minio,
    delete_file as delete_from_minio
)


router = APIRouter(
    prefix="/files",
    tags=["Files"]
)


# =========================================================
# CONFIG
# =========================================================

UPLOAD_DIR = "storage"

CHUNK_DIR = os.path.join(
    UPLOAD_DIR,
    "chunks"
)


os.makedirs(
    CHUNK_DIR,
    exist_ok=True
)


# =========================================================
# VALIDATION
# =========================================================

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
    "text/plain"
}


MAX_FILE_SIZE = 10 * 1024 * 1024


# =========================================================
# CLEANUP TEMP FILES
# =========================================================

def cleanup_temp_files(
    chunk_dir: str,
    file_path: str
):

    if os.path.exists(
        chunk_dir
    ):

        shutil.rmtree(
            chunk_dir
        )

    if os.path.exists(
        file_path
    ):

        os.remove(
            file_path
        )


# =========================================================
# NORMAL FILE UPLOAD
# =========================================================

@router.post("/upload")
def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Validate content type
    # -----------------------------------------------------

    if file.content_type not in ALLOWED_CONTENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail="File type not allowed"
        )

    # -----------------------------------------------------
    # Get extension
    # -----------------------------------------------------

    extension = ""

    if "." in file.filename:

        extension = os.path.splitext(
            file.filename
        )[1]

    # -----------------------------------------------------
    # Generate unique storage filename
    # -----------------------------------------------------

    storage_filename = (
        f"{uuid.uuid4()}{extension}"
    )

    # -----------------------------------------------------
    # Temporary file path
    # -----------------------------------------------------

    file_path = os.path.join(
        UPLOAD_DIR,
        storage_filename
    )

    # -----------------------------------------------------
    # Save temporary file
    # -----------------------------------------------------

    try:

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Failed to save file"
        )

    # -----------------------------------------------------
    # Get file size
    # -----------------------------------------------------

    file_size = os.path.getsize(
        file_path
    )

    # -----------------------------------------------------
    # Validate file size
    # -----------------------------------------------------

    if file_size > MAX_FILE_SIZE:

        os.remove(
            file_path
        )

        raise HTTPException(
            status_code=400,
            detail="File size must be less than 10 MB"
        )

    # -----------------------------------------------------
    # Upload to MinIO
    # -----------------------------------------------------

    try:

        upload_to_minio(
            file_path=file_path,
            object_name=storage_filename,
            content_type=file.content_type
        )

    except Exception:

        if os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )

        raise HTTPException(
            status_code=500,
            detail="Failed to upload file to object storage"
        )

    # -----------------------------------------------------
    # Delete temporary local file
    # -----------------------------------------------------

    if os.path.exists(
        file_path
    ):

        os.remove(
            file_path
        )

    # -----------------------------------------------------
    # Save metadata in database
    # -----------------------------------------------------

    new_file = FileModel(
        filename=file.filename,
        storage_filename=storage_filename,
        content_type=file.content_type,
        size=file_size
    )

    db.add(
        new_file
    )

    db.commit()

    db.refresh(
        new_file
    )

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "message": "File uploaded successfully",
        "file_id": new_file.id,
        "filename": new_file.filename,
        "size": new_file.size
    }


# =========================================================
# INIT MULTIPART UPLOAD
# =========================================================

@router.post("/multipart/init")
def init_multipart_upload(
    filename: str = Form(...),
    total_chunks: int = Form(...),
    total_size: int = Form(...),
    content_type: str = Form(...),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Validate content type
    # -----------------------------------------------------

    if content_type not in ALLOWED_CONTENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail="File type not allowed"
        )

    # -----------------------------------------------------
    # Validate size
    # -----------------------------------------------------

    if total_size <= 0:

        raise HTTPException(
            status_code=400,
            detail="total_size must be greater than 0"
        )

    if total_size > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=400,
            detail="File size must be less than 10 MB"
        )

    # -----------------------------------------------------
    # Validate chunks
    # -----------------------------------------------------

    if total_chunks <= 0:

        raise HTTPException(
            status_code=400,
            detail="total_chunks must be greater than 0"
        )

    # -----------------------------------------------------
    # Generate upload ID
    # -----------------------------------------------------

    upload_id = str(
        uuid.uuid4()
    )

    # -----------------------------------------------------
    # Create upload session
    # -----------------------------------------------------

    upload = UploadSession(
        upload_id=upload_id,
        filename=filename,
        content_type=content_type,
        total_size=total_size,
        total_chunks=total_chunks
    )

    db.add(
        upload
    )

    db.commit()

    # -----------------------------------------------------
    # Create chunk directory
    # -----------------------------------------------------

    chunk_dir = os.path.join(
        CHUNK_DIR,
        upload_id
    )

    os.makedirs(
        chunk_dir,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "message": "Multipart upload initialized",
        "upload_id": upload_id,
        "total_chunks": total_chunks
    }


# =========================================================
# UPLOAD CHUNK
# =========================================================

@router.post(
    "/multipart/{upload_id}/chunk"
)
def upload_chunk(
    upload_id: str,
    chunk_number: int = Form(...),
    chunk: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Find upload session
    # -----------------------------------------------------

    upload = (
        db.query(UploadSession)
        .filter(
            UploadSession.upload_id == upload_id
        )
        .first()
    )

    if not upload:

        raise HTTPException(
            status_code=404,
            detail="Upload session not found"
        )

    # -----------------------------------------------------
    # Validate chunk number
    # -----------------------------------------------------

    if (
        chunk_number < 1
        or chunk_number > upload.total_chunks
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid chunk number"
        )

    # -----------------------------------------------------
    # Chunk directory
    # -----------------------------------------------------

    chunk_dir = os.path.join(
        CHUNK_DIR,
        upload_id
    )

    os.makedirs(
        chunk_dir,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Chunk path
    # -----------------------------------------------------

    chunk_path = os.path.join(
        chunk_dir,
        f"{chunk_number}.part"
    )

    # -----------------------------------------------------
    # Save chunk
    # -----------------------------------------------------

    try:

        with open(
            chunk_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                chunk.file,
                buffer
            )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Failed to save chunk"
        )

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "message": "Chunk uploaded successfully",
        "upload_id": upload_id,
        "chunk_number": chunk_number
    }


# =========================================================
# COMPLETE MULTIPART UPLOAD
# =========================================================

@router.post(
    "/multipart/{upload_id}/complete"
)
def complete_multipart_upload(
    upload_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Find upload session
    # -----------------------------------------------------

    upload = (
        db.query(UploadSession)
        .filter(
            UploadSession.upload_id == upload_id
        )
        .first()
    )

    if not upload:

        raise HTTPException(
            status_code=404,
            detail="Upload session not found"
        )

    # -----------------------------------------------------
    # Chunk directory
    # -----------------------------------------------------

    chunk_dir = os.path.join(
        CHUNK_DIR,
        upload_id
    )

    if not os.path.exists(
        chunk_dir
    ):

        raise HTTPException(
            status_code=400,
            detail="No chunks found"
        )

    # -----------------------------------------------------
    # Check all chunks
    # -----------------------------------------------------

    for i in range(
        1,
        upload.total_chunks + 1
    ):

        chunk_path = os.path.join(
            chunk_dir,
            f"{i}.part"
        )

        if not os.path.exists(
            chunk_path
        ):

            raise HTTPException(
                status_code=400,
                detail=f"Chunk {i} is missing"
            )

    # -----------------------------------------------------
    # Get extension
    # -----------------------------------------------------

    extension = ""

    if "." in upload.filename:

        extension = os.path.splitext(
            upload.filename
        )[1]

    # -----------------------------------------------------
    # Generate unique filename
    # -----------------------------------------------------

    storage_filename = (
        f"{uuid.uuid4()}{extension}"
    )

    # -----------------------------------------------------
    # Temporary merged file
    # -----------------------------------------------------

    file_path = os.path.join(
        UPLOAD_DIR,
        storage_filename
    )

    # -----------------------------------------------------
    # Merge chunks
    # -----------------------------------------------------

    try:

        with open(
            file_path,
            "wb"
        ) as final_file:

            for i in range(
                1,
                upload.total_chunks + 1
            ):

                chunk_path = os.path.join(
                    chunk_dir,
                    f"{i}.part"
                )

                with open(
                    chunk_path,
                    "rb"
                ) as chunk_file:

                    shutil.copyfileobj(
                        chunk_file,
                        final_file
                    )

    except Exception:

        cleanup_temp_files(
            chunk_dir,
            file_path
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to merge chunks"
        )

    # -----------------------------------------------------
    # Final size
    # -----------------------------------------------------

    file_size = os.path.getsize(
        file_path
    )

    # -----------------------------------------------------
    # Validate final size
    # -----------------------------------------------------

    if file_size > MAX_FILE_SIZE:

        cleanup_temp_files(
            chunk_dir,
            file_path
        )

        raise HTTPException(
            status_code=400,
            detail="File size must be less than 10 MB"
        )

    # -----------------------------------------------------
    # Validate expected size
    # -----------------------------------------------------

    if (
        upload.total_size
        and file_size != upload.total_size
    ):

        cleanup_temp_files(
            chunk_dir,
            file_path
        )

        raise HTTPException(
            status_code=400,
            detail="Uploaded file size does not match total_size"
        )

    # -----------------------------------------------------
    # Upload to MinIO
    # -----------------------------------------------------

    try:

        upload_to_minio(
            file_path=file_path,
            object_name=storage_filename,
            content_type=upload.content_type
        )

    except Exception:

        cleanup_temp_files(
            chunk_dir,
            file_path
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to upload file to object storage"
        )

    # -----------------------------------------------------
    # Save metadata
    # -----------------------------------------------------

    new_file = FileModel(
        filename=upload.filename,
        storage_filename=storage_filename,
        content_type=upload.content_type,
        size=file_size
    )

    db.add(
        new_file
    )

    # -----------------------------------------------------
    # Delete upload session
    # -----------------------------------------------------

    db.delete(
        upload
    )

    db.commit()

    db.refresh(
        new_file
    )

    # -----------------------------------------------------
    # Background cleanup
    # -----------------------------------------------------

    background_tasks.add_task(
        cleanup_temp_files,
        chunk_dir,
        file_path
    )

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "message": "Multipart upload completed successfully",
        "file_id": new_file.id,
        "filename": new_file.filename,
        "size": new_file.size
    }


# =========================================================
# LIST FILES
# =========================================================

@router.get(
    "/",
    response_model=list[FileResponse]
)
def list_files(
    skip: int = Query(
        0,
        ge=0
    ),
    limit: int = Query(
        10,
        ge=1,
        le=100
    ),
    db: Session = Depends(get_db)
):

    files = (
        db.query(FileModel)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return files


# =========================================================
# FILE METADATA
# =========================================================

@router.get(
    "/{file_id}/metadata",
    response_model=FileResponse
)
def get_file_metadata(
    file_id: int,
    db: Session = Depends(get_db)
):

    file = (
        db.query(FileModel)
        .filter(
            FileModel.id == file_id
        )
        .first()
    )

    if not file:

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return file


# =========================================================
# DOWNLOAD FILE
# =========================================================

@router.get(
    "/{file_id}"
)
def download_file(
    file_id: int,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Find file in database
    # -----------------------------------------------------

    file = (
        db.query(FileModel)
        .filter(
            FileModel.id == file_id
        )
        .first()
    )

    if not file:

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    # -----------------------------------------------------
    # Get file from MinIO
    # -----------------------------------------------------

    try:

        response = get_file_from_minio(
            file.storage_filename
        )

    except Exception:

        raise HTTPException(
            status_code=404,
            detail="File not found in object storage"
        )

    # -----------------------------------------------------
    # Stream file
    # -----------------------------------------------------

    def file_iterator():

        try:

            while True:

                chunk = response.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                yield chunk

        finally:

            response.close()
            response.release_conn()

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return StreamingResponse(
        file_iterator(),
        media_type=file.content_type
        or "application/octet-stream",
        headers={
            "Content-Disposition":
                f'attachment; filename="{file.filename}"'
        }
    )


# =========================================================
# DELETE FILE
# =========================================================

@router.delete(
    "/{file_id}"
)
def delete_file(
    file_id: int,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Find file
    # -----------------------------------------------------

    file = (
        db.query(FileModel)
        .filter(
            FileModel.id == file_id
        )
        .first()
    )

    if not file:

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    # -----------------------------------------------------
    # Delete from MinIO
    # -----------------------------------------------------

    try:

        delete_from_minio(
            file.storage_filename
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Failed to delete file from object storage"
        )

    # -----------------------------------------------------
    # Delete database record
    # -----------------------------------------------------

    db.delete(
        file
    )

    db.commit()

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "message": "File deleted successfully",
        "file_id": file_id
    }