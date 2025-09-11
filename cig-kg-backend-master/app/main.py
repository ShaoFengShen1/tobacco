from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import sys
import pathlib

# 添加项目根目录到Python路径
root_dir = str(pathlib.Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.routes import ontology, build, image, entitiy
from app.dependencies.dependencies import neo4j_service, get_neo4j_service  # 从 dependencies.py 导入
from app.config.database import engine
from app.services import getEntities_service
from app.pdf_module import pdf_module
from app.pdf_module.models import PDFFile  # 导入PDF模型以创建表
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

# 包含PDF模块
from app.pdf_module import pdf_module
app.include_router(pdf_module, prefix="/api", tags=["PDF"])

# 创建数据库表
PDFFile.__table__.create(bind=engine, checkfirst=True)

@app.on_event("startup")
async def startup_event():
    try:
        await neo4j_service.initialize()
    except Exception as e:
        print(f"Neo4j initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时关闭 Neo4j 驱动程序"""
    await neo4j_service.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Knowledge Graph Builder API"}

# 打印所有加载的路由
for route in app.routes:
    print(route.path, route.name)




