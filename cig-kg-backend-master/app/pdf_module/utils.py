import os
from fastapi import UploadFile

UPLOAD_DIR = "uploads/pdf_files"

def ensure_upload_dir():
    """确保上传目录存在"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_file(file: UploadFile, filename: str) -> str:
    """保存上传的文件并返回保存路径"""
    file_path = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    return file_path
