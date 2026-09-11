from sqlalchemy import Column , Integer , String , BigInteger , DateTime
from datetime import datetime
from app.db.database import Base

class File(Base):
    __tablename__ = "files"

    id = Column(Integer , primary_key=True , index=True)
    filename = Column(String , nullable=False)
    storage_filename = Column(String , nullable=False , unique=True)
    content_type = Column(String , nullable=True)
    size = Column(BigInteger , nullable=False)
    created_at = Column(DateTime , default=datetime.utcnow)

class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id = Column(Integer, primary_key=True , index=True)
    upload_id = Column(
        String, unique=True , nullable=False , index=True
    )
    filename = Column(String , nullable=False)
    content_type = Column(String , nullable=True)
    total_size = Column(BigInteger , nullable=True)
    total_chunks = Column(Integer , nullable=False)
    created_at = Column(DateTime , default=datetime.utcnow)