from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.pdf_service import PDFService
from app.services.kg_build_service import KGBuildService
from app.dependencies.dependencies import get_neo4j_service  # 从 dependencies.py 导入
import shutil
import os
import json
from typing import Optional
from datetime import datetime


router = APIRouter()
# 测试文件
TEST_FILE = "X6_Electrical-Instruction_Data-Sheet_Manual_CHI.md"


@router.post("/kg_build")
async def build_knowledge_graph(
        file: UploadFile = File(..., description="上传的PDF文件"),
        database_name: str = Form(..., description="目标数据库名称"),
        prompt: str = Form(..., description="构建提示词")
):
    """构建知识图谱接口"""
    try:
        pdf_service = PDFService()
        kg_build_service = KGBuildService()

        # 1. 验证文件类型
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="仅支持PDF文件")

        # 2. 保存上传文件
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. 解析PDF内容并保存预处理结果
        # TODO: 替换为OCR识别接口
        md_text = pdf_service.pdf2md(file_path)

        # 创建预处理文件夹
        preprocess_dir = "doc_preprocessed"
        os.makedirs(preprocess_dir, exist_ok=True)

        # 根据文件名创建子文件夹
        file_name_without_extension = os.path.splitext(file.filename)[0]
        preprocess_file_dir = os.path.join(preprocess_dir, file_name_without_extension)
        os.makedirs(preprocess_file_dir, exist_ok=True)


        # 生成带时间戳的预处理文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        preprocessed_filename = f"{os.path.splitext(file.filename)[0]}_{timestamp}.md"
        preprocessed_path = os.path.join(preprocess_file_dir, preprocessed_filename)

        # TODO: 替换为OCR识别接口后图片的相关处理
        # 保存预处理内容
        with open(preprocessed_path, "w", encoding="utf-8") as f:
            f.write(md_text)

        # 4. 构建知识图谱

        # 创建 json 文件夹，包含了模型抽取节点与关系的结果
        kg_output_dir = "kg_output"
        os.makedirs(kg_output_dir, exist_ok=True)

        # 根据文件名创建子文件夹
        kg_output_file_dir = os.path.join(kg_output_dir, file_name_without_extension)
        os.makedirs(kg_output_file_dir, exist_ok=True)

        result = kg_build_service.build_graph(kg_output_file_dir, preprocessed_path, prompt, database_name)

        # 5. 清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)

        return {
            "success": True,
            "message": "知识图谱构建完成",
            "preprocessed_file": preprocessed_filename,
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        return {
            "success": False,
            "message": f"构建失败: {str(e)}"
        }

@router.get("/kg_extract")
async def kg_extract(
        file: UploadFile = File(..., description="上传的PDF文件"),
        database_name: str = Form(..., description="目标数据库名称"),
        prompt: str = Form(..., description="构建提示词")
):
    """构建知识图谱接口"""
    try:
        all_nodes = []
        # 1. 验证文件类型
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="仅支持PDF文件")


        # 根据文件名创建子文件夹
        file_name_without_extension = os.path.splitext(file.filename)[0]


        # 创建 json 文件夹，包含了模型抽取节点与关系的结果
        kg_output_dir = "kg_output"


        # 根据文件名创建子文件夹
        kg_output_file_dir = os.path.join(kg_output_dir, file_name_without_extension)

        for filename in os.listdir(kg_output_file_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(kg_output_file_dir, filename)
                try:
                    with open(filepath, encoding='utf-8') as f:
                        data = json.load(f)
                        nodes = data.get('nodes', [])
                        print(nodes)
                        all_nodes.extend(nodes)
                except Exception as e:
                    print(f'读取失败 {filename}: {e}')
        return {
            "success": True,
            "message": "知识抽取完成",
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        return {
            "success": False,
            "message": f"抽取失败: {str(e)}"
        }