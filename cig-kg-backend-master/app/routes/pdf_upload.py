from fastapi import FastAPI, APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from typing import List
import os
from datetime import datetime
import sys
import pathlib

# 添加项目根目录到Python路径
root_dir = str(pathlib.Path(__file__).parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.config.database import get_db
from app.models.pdf_file import PDFFile

app = FastAPI()
router = APIRouter()

UPLOAD_DIR = "uploads/pdf_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith('.pdf'):
        return {"filename": file.filename, "status": "error", "message": "不是PDF文件"}
        
    try:
        # 保存文件
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        content = await file.read()
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
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
            "id": db_file.id
        }
        
    except Exception as e:
        return {
            "filename": file.filename,
            "status": "error",
            "message": str(e)
        }

@router.get("/files")
def get_pdf_files(db: Session = Depends(get_db)):
    return db.query(PDFFile).all()

app.include_router(router, prefix="/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
