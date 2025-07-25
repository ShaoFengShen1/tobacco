from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any
from dotenv import load_dotenv
import os


class Neo4jService:
    def __init__(self):
        load_dotenv()

        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None

    async def initialize(self):
        """异步初始化 Neo4j 驱动程序"""
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

    async def close(self):
        """异步关闭驱动程序"""
        if self.driver:
            await self.driver.close()

    async def get_session(self, database_name: str = None):
        """获取指定数据库的异步会话"""
        if not self.driver:
            raise Exception("Neo4j driver is not initialized. Call initialize() first.")
        return self.driver.session(database=database_name)