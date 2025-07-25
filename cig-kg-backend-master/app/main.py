from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routes import ontology, build, image, entitiy
from app.dependencies.dependencies import neo4j_service, get_neo4j_service  # 从 dependencies.py 导入
from app.services import getEntities_service
app = FastAPI(title="Knowledge Graph Builder API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(ontology.router, prefix="/api/ontology", tags=["Ontology"])
app.include_router(build.router, prefix="/api/build", tags=["Build"])
app.include_router(image.router, prefix="/api/image", tags=["Image"])
app.include_router(entitiy.router, prefix="/api/entities", tags=["entities"])
# app.include_router(getEntities_service.router, prefix="/api/entities", tags=["entities"])


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化 Neo4j 驱动程序"""
    await neo4j_service.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时关闭 Neo4j 驱动程序"""
    await neo4j_service.close()




