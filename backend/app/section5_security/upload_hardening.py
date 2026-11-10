import os
from fastapi import UploadFile, HTTPException

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB

async def validate_upload_size(file: UploadFile):
    """Infrastructure-level file size validation."""
    content = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    await file.seek(0)
