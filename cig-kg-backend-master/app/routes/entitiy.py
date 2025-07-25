from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.entity_service import *
from app.services.pdf_service import PDFService
from app.services.kg_build_service import KGBuildService
from app.dependencies.dependencies import get_neo4j_service  # 从 dependencies.py 导入
import shutil
import os
import json
from typing import Optional
from datetime import datetime


router = APIRouter()

@router.post("/list", response_model=EntityListResponse)
async def get_entities(
        file: UploadFile = File(..., description="上传的PDF文件")
):
    """
    获取实体列表，从文件夹下所有JSON文件中读取nodes数据
    """
    try:
        # 1. 验证文件类型
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="仅支持PDF文件")

        # 根据文件名创建子文件夹
        file_name_without_extension = os.path.splitext(file.filename)[0]

        # 创建 json 文件夹，包含了模型抽取节点与关系的结果
        kg_output_dir = "kg_output"

        # 根据文件名创建子文件夹
        JSON_DATA_DIR = os.path.join(kg_output_dir, file_name_without_extension)

        # 读取所有JSON文件
        json_files_data = read_all_json_files(JSON_DATA_DIR)

        if not json_files_data:
            raise HTTPException(status_code=404, detail="未找到任何JSON文件")

        # 提取所有文件中的nodes数据并转换为Entity格式
        entities = []

        for file_data in json_files_data:
            nodes = file_data.get("nodes", [])
            source_file = file_data.get("source_file", "unknown")

            for node in nodes:
                # 在属性中添加来源文件信息
                if node.get("properties") != None:
                    properties = node.get("properties", {})

                properties["source_file"] = source_file
                print(node)
                entity = Entity(
                    id=node.get("id", ""),
                    name=node.get("name", ""),
                    type=node.get("type", ""),
                    properties=properties
                )

                entities.append(entity)

        # 根据ID去重（如果多个文件中有相同ID的实体，保留第一个）
        unique_entities = {}
        for entity in entities:
            if entity.id not in unique_entities:
                unique_entities[entity.id] = entity

        return EntityListResponse(entities=list(unique_entities.values()))

    except HTTPException:
        raise
    except Exception as e:
        print("-------------------")
        print(e)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")