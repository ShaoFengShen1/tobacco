from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from ..config.database import Base
import uuid

class PDFFile(Base):
    __tablename__ = "pdf_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    upload_time = Column(DateTime, server_default=func.now())
    es_code = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<PDFFile(id={self.id}, file_name={self.file_name})>"
