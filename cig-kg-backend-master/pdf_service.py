import os
import uuid
import math
from datetime import datetime
from typing import List

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, String, DateTime, or_
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel

# --- Pydantic 模型定义 ---
class FileUpdatePayload(BaseModel):
    es_code: str | None = None

class BatchDeletePayload(BaseModel):
    file_ids: List[str]

# --- FastAPI 应用实例 ---
app = FastAPI(title="PDF文件管理服务")


# ==============================================================================
#  ★★★★★ 最终修改部分 ★★★★★
#  修正了CORS配置，以同时允许来自 'localhost' 和 '127.0.0.1' 的请求。
# ==============================================================================
origins = [
    "http://localhost:5173",    # 前端开发服务器地址 (来自浏览器请求头)
    "http://127.0.0.1:5173",  # 也包含 127.0.0.1 以增加兼容性
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # 使用上面定义的来源列表
    allow_credentials=True,      # 允许携带 cookies
    allow_methods=["*"],         # 允许所有 HTTP 方法 (GET, POST, etc.)
    allow_headers=["*"],         # 允许所有请求头
)
# ==============================================================================


# --- 数据库配置 ---
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:root@localhost/file_management"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- 数据库模型: PDFFile ---
class PDFFile(Base):
    __tablename__ = "pdf_files"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    es_code = Column(String(255), nullable=True)

# 创建数据库表 (如果不存在)
Base.metadata.create_all(bind=engine)


# --- 文件上传目录 ---
UPLOAD_DIR = "pdf_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --- 依赖项: 数据库会话 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API 路由 ---

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """处理单个PDF文件的上传"""
    # if not file.filename.lower().endswith('.pdf'):
    #     raise HTTPException(status_code=400, detail={"status": "error", "message": "只接受PDF文件"})
    try:
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        db_file = PDFFile(file_name=file.filename, file_path=file_path)
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        return {"status": "success", "message": "文件上传成功", "filename": file.filename, "id": db_file.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": f"上传失败: {str(e)}"})

@app.post("/upload/batch")
async def upload_batch_pdf(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """处理批量PDF文件的上传"""
    success_count, failure_count = 0, 0
    new_db_files = []
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            failure_count += 1
            continue
        try:
            unique_filename = f"{uuid.uuid4()}_{file.filename}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            new_db_files.append(PDFFile(file_name=file.filename, file_path=file_path))
            success_count += 1
        except Exception as e:
            print(f"处理文件 {file.filename} 时出错: {e}")
            failure_count += 1
    if new_db_files:
        db.add_all(new_db_files)
        db.commit()
    return {"status": "success", "message": f"批量上传完成。成功 {success_count} 个，失败 {failure_count} 个。"}

@app.get("/files")
def get_pdf_files(db: Session = Depends(get_db), page: int = Query(1, ge=1), per_page: int = Query(10, ge=1, le=100), search: str = Query(None)):
    """获取PDF文件列表，支持分页和搜索"""
    query = db.query(PDFFile)
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(PDFFile.file_name.ilike(search_term), PDFFile.es_code.ilike(search_term)))
    total = query.count()
    offset = (page - 1) * per_page
    total_pages = math.ceil(total / per_page)
    files_query = query.order_by(PDFFile.upload_time.desc()).offset(offset).limit(per_page).all()
    files_data = []
    for file in files_query:
        file_size_mb = round(os.path.getsize(file.file_path) / (1024 * 1024), 2) if os.path.exists(file.file_path) else 0
        files_data.append({
            "id": file.id, "file_name": file.file_name, "upload_time": file.upload_time,
            "es_code": file.es_code, "file_size_mb": file_size_mb
        })
    return {"status": "success", "data": {"files": files_data, "pagination": {"total": total, "page": page, "per_page": per_page, "total_pages": total_pages}}}

@app.put("/files/{file_id}")
def update_file(file_id: str, payload: FileUpdatePayload, db: Session = Depends(get_db)):
    """更新文件的元数据 (例如 es_code)"""
    db_file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    if not db_file: raise HTTPException(status_code=404, detail="文件不存在")
    db_file.es_code = payload.es_code
    db.commit()
    db.refresh(db_file)
    return {"status": "success", "message": "更新成功"}

@app.get("/files/{file_id}/preview")
def preview_pdf_file(file_id: str, db: Session = Depends(get_db)):
    """在浏览器中预览PDF文件"""
    file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    if not file: raise HTTPException(status_code=404, detail="文件记录不存在")
    if not os.path.exists(file.file_path): raise HTTPException(status_code=404, detail="物理文件不存在")
    return FileResponse(file.file_path, media_type='application/pdf')

@app.get("/files/{file_id}/download")
def download_pdf_file(file_id: str, db: Session = Depends(get_db)):
    """下载PDF文件"""
    file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    if not file: raise HTTPException(status_code=404, detail="文件记录不存在")
    if not os.path.exists(file.file_path): raise HTTPException(status_code=404, detail="物理文件不存在")
    return FileResponse(path=file.file_path, filename=file.file_name, media_type='application/octet-stream')

@app.delete("/files/{file_id}")
def delete_pdf_file(file_id: str, db: Session = Depends(get_db)):
    """删除单个PDF文件"""
    file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    if not file: raise HTTPException(status_code=404, detail="文件不存在")
    try:
        if os.path.exists(file.file_path): os.remove(file.file_path)
    except Exception as e: print(f"警告: 删除物理文件 {file.file_path} 时出错: {e}")
    db.delete(file)
    db.commit()
    return {"status": "success", "message": "文件已成功删除"}

@app.post("/files/batch-delete")
def batch_delete_files(payload: BatchDeletePayload, db: Session = Depends(get_db)):
    """批量删除多个PDF文件"""
    if not payload.file_ids: raise HTTPException(status_code=400, detail="文件ID列表不能为空")
    files_to_delete = db.query(PDFFile).filter(PDFFile.id.in_(payload.file_ids)).all()
    if not files_to_delete: raise HTTPException(status_code=404, detail="未找到任何有效文件")
    for file in files_to_delete:
        if os.path.exists(file.file_path):
            try: os.remove(file.file_path)
            except Exception as e: print(f"警告: 删除物理文件 {file.file_path} 时出错: {e}")
    db.query(PDFFile).filter(PDFFile.id.in_(payload.file_ids)).delete(synchronize_session=False)
    db.commit()
    return {"status": "success", "message": f"成功删除 {len(files_to_delete)} 个文件"}

# --- 启动命令 (用于开发环境) ---
if __name__ == "__main__":
    import uvicorn
    # 推荐使用命令行启动以获得热重载功能:
    # uvicorn your_filename:app --host 0.0.0.0 --port 8001 --reload
    uvicorn.run(app, host="0.0.0.0", port=8001)