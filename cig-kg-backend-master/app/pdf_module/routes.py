from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import os
from datetime import datetime
import uuid
from typing import List

from app.config.database import get_db
from .models import PDFFile
from .utils import ensure_upload_dir, save_file

router = APIRouter(prefix="/pdf")

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith('.pdf'):
        return {
            "filename": file.filename,
            "status": "error",
            "message": "只接受PDF文件"
        }
        
    try:
        ensure_upload_dir()
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = await save_file(file, unique_filename)
        
        # 创建数据库记录
        db_file = PDFFile(
            file_name=file.filename,
            file_path=file_path
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        return {
            "filename": file.filename,
            "status": "success",
            "id": db_file.id,
            "message": "文件上传成功"
        }
        
    except Exception as e:
        return {
            "filename": file.filename,
            "status": "error",
            "message": str(e)
        }

@router.get("/files")
def list_files(db: Session = Depends(get_db)):
    """获取所有上传的PDF文件列表"""
    files = db.query(PDFFile).all()
    return [file.to_dict() for file in files]

@router.delete("/files/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db)):
    """删除指定的PDF文件"""
    file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")
    
    db.delete(file)
    db.commit()
    
    return {"status": "success", "message": "文件已成功删除"}
