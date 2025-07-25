from fastapi import APIRouter, Depends, HTTPException
from app.services.neo4j_service import Neo4jService
from app.services.prompt_service import PromptService
# from app.models.schemas import OntologyNode
from app.dependencies.dependencies import get_neo4j_service  # 从 dependencies.py 导入

router = APIRouter()


# @router.get("/list", response_model=list[OntologyNode])
# async def get_ontologies(neo4j_service: Neo4jService = Depends(get_neo4j_service)):
#     """获取所有Ontology节点"""
#     query = "MATCH (n:Ontology) RETURN n.name AS name, n.description AS description, id(n) AS id"
#     return await neo4j_service.run_query(query)


@router.get("/prompt/{ontology_id}")
async def get_prompt(ontology_id: str, neo4j_service: Neo4jService = Depends(get_neo4j_service)):
    """根据本体ID生成初始提示词"""
    prompt_service = PromptService(neo4j_service=neo4j_service)
    extraction_prompt = await prompt_service.build_prompt(ontology_id)

    if "error" in extraction_prompt:
        raise HTTPException(status_code=404, detail=extraction_prompt["error"])

    # prompt = f"请基于以下本体构建知识图谱，确保符合{ontology_id}号本体的分类体系..."
    return {"prompt": extraction_prompt}

