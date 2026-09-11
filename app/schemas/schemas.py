from datetime import datetime
from pydantic import BaseModel

class FileResponse(BaseModel):
    id:int
    filename:str
    content_type:str | None
    size:int
    created_at:datetime

    class Config:
        from_attriubtes = True