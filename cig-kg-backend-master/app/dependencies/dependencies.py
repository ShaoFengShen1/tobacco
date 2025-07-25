from app.services.neo4j_service import Neo4jService

# 全局 Neo4j 服务实例
neo4j_service = Neo4jService()


async def get_neo4j_service():
    return neo4j_service
