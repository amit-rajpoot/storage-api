from fastapi import FastAPI

from dotenv import load_dotenv


# Load .env
load_dotenv()


from app.db.database import (
    Base,
    engine
)

from app.model import models

from app.routes.files import (
    router as file_router
)

from app.services.storage import (
    create_bucket
)


# =========================================================
# DATABASE
# =========================================================

Base.metadata.create_all(
    bind=engine
)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="File Storage API",
    description="File storage API using FastAPI, SQLite and MinIO",
    version="1.0.0"
)


# =========================================================
# MINIO
# =========================================================

create_bucket()


# =========================================================
# ROUTES
# =========================================================

app.include_router(
    file_router
)


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message": "File Storage API is running"
    }