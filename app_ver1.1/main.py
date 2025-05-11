import os
import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from pipelines.rag_pipelines.vector_store import VectorStoreManager
from pipelines.rag_pipelines.search_engine import SearchEngine
from pipelines.rag_pipelines.cohere_reranker import AsyncCohereReranker
from mongodb.mongodb_manager import MongoDBManager
from mongodb.mongodb_search import MongoDBSearch
from llms.aggregate_pipeline_generator import AggregatePipelineGenerator
from llms.coordinator import Coordinator

# Routers
from api.chat_endpoint import router as chat_router
from api.pdf_endpoint import router as pdf_router
from api.xlsx_endpoint import router as xlsx_router
from api.doc_endpoint import router as doc_router
from api.delete_endpoint import router as delete_router
from api.xlsx_delete import router as xlsx_delete_router

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

config = Config()

async def init_queue_from_pool(pool, queue: asyncio.Queue):
    """Khởi tạo queue từ pool các đối tượng"""
    for item in pool:
        await queue.put(item)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ==== Validate ENV ====
    required_envs = [config.OPENAI_API_KEY, config.MONGODB_URI, config.COHERE_API_KEY]
    if not all(required_envs):
        raise RuntimeError("Thiếu ENV quan trọng: OPENAI_API_KEY / MONGODB_URI / COHERE_API_KEY")

    # ==== Init VectorStoreManager ====
    vector_store_pool = [
        VectorStoreManager(
            collection_name=config.QDRANT_COLLECTION_NAME,
            openai_api_key=config.OPENAI_API_KEY,
            qdrant_api_key=config.QDRANT_API_KEY,
            qdrant_url=config.QDRANT_URL,
            prefer_grpc=True,
        )
        for _ in range(config.NUM_VECTOR_STORES)
    ]
    for vs in vector_store_pool:
        try:
            await vs.init_collection()
        except Exception as e:
            logger.error(f"[VectorStore] Lỗi khi init collection: {e}")
    vector_store_queue = asyncio.Queue()
    await init_queue_from_pool(vector_store_pool, vector_store_queue)
    logger.info(f"Khởi tạo queue với {config.NUM_VECTOR_STORES} VectorStoreManager.")

    # ==== Init SearchEngine ====
    search_engine_pool = [
        SearchEngine(vector_store=vector_store_pool[i])
        for i in range(config.NUM_VECTOR_STORES)
    ]
    search_engine_queue = asyncio.Queue()
    await init_queue_from_pool(search_engine_pool, search_engine_queue)
    logger.info(f"Khởi tạo queue với {config.NUM_VECTOR_STORES} SearchEngine.")

    # ==== Init Cohere Reranker ====
    cohere_reranker_pool = [AsyncCohereReranker(api_key=config.COHERE_API_KEY) for _ in range(config.NUM_RERANKERS)]
    cohere_reranker_queue = asyncio.Queue()
    await init_queue_from_pool(cohere_reranker_pool, cohere_reranker_queue)
    logger.info(f"Khởi tạo queue với {config.NUM_RERANKERS} AsyncCohereReranker.")

    # ==== Init MongoDB ====
    mongo_db_pool = [
        MongoDBManager(
            mongodb_uri=config.MONGODB_URI,
            database_name=config.MONGODB_DATABASE,
            collection_name=config.MONGODB_COLLECTION,
            pool_config=config.MONGODB_CONNECTION_POOL_CONFIG
        )
        for _ in range(config.NUM_MONGO_DBS)
    ]
    mongo_db_queue = asyncio.Queue()
    await init_queue_from_pool(mongo_db_pool, mongo_db_queue)
    logger.info(f"Khởi tạo queue với {config.NUM_MONGO_DBS} MongoDB.")

    # ==== Init AggregatePipelineGenerator ====
    pipeline_generator_pool = [
        AggregatePipelineGenerator(
            api_key=config.OPENAI_API_KEY,
            config=config.AGGREGATE_PIPELINE_GENERATOR_CONFIG
        )
        for _ in range(config.NUM_MONGO_DBS)
    ]
    pipeline_generator_queue = asyncio.Queue()
    await init_queue_from_pool(pipeline_generator_pool, pipeline_generator_queue)
    logger.info(f"Khởi tạo queue với {config.NUM_MONGO_DBS} AggregatePipelineGenerator.")

    # ==== Init MongoDBSearch ====
    mongodb_search_pool = [
        MongoDBSearch(
            db_manager=mongo_db_pool[i],
            pipeline_generator=pipeline_generator_pool[i]
        )
        for i in range(config.NUM_MONGO_DBS)
    ]
    mongodb_search_queue = asyncio.Queue()
    await init_queue_from_pool(mongodb_search_pool, mongodb_search_queue)
    logger.info(f"Khởi tạo queue với {config.NUM_MONGO_DBS} MongoDBSearch.")

    # ==== Init Coordinator ====
    coordinator_pool = [
        Coordinator(
            model_name=config.COORDINATOR_MODEL_NAME,
            temperature=config.COORDINATOR_TEMPERATURE
        )
        for _ in range(config.NUM_COORDINATORS)
    ]
    coordinator_queue = asyncio.Queue()
    await init_queue_from_pool(coordinator_pool, coordinator_queue)
    logger.info(f"Khởi tạo queue với {config.NUM_COORDINATORS} Coordinator.")

    # ==== Gắn vào app.state ====
    app.state.config = config
    app.state.vector_store_pool = vector_store_pool
    app.state.vector_store_queue = vector_store_queue
    app.state.search_engine_pool = search_engine_pool
    app.state.search_engine_queue = search_engine_queue
    app.state.async_cohere_reranker_queue = cohere_reranker_queue
    app.state.mongo_db_pool = mongo_db_pool
    app.state.mongo_db_queue = mongo_db_queue
    app.state.aggregate_pipeline_generator_pool = pipeline_generator_pool
    app.state.aggregate_pipeline_generator_queue = pipeline_generator_queue
    app.state.mongodb_search_queue = mongodb_search_queue
    app.state.coordinator_queue = coordinator_queue

    logger.info("✅ Hệ thống đã khởi tạo xong.")
    yield
    
    # ==== Dọn dẹp tài nguyên ====
    logger.info("🧹 Đang shutdown app...")
    for mongo_db in mongo_db_pool:
        mongo_db.close_connections()
    logger.info("🔒 Đã đóng tất cả kết nối MongoDB")

# ==== App ====
app = FastAPI(
    title="LogiTuning API",
    description="API cho ứng dụng LogiTuning",
    version="1.2.0",
    lifespan=lifespan
)

# ==== Middleware ====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== Routers ====
app.include_router(chat_router, prefix="/api", tags=["CHAT"])
app.include_router(pdf_router, prefix="/pdf", tags=["PDF"])
app.include_router(xlsx_router, prefix="/xlsx", tags=["XLSX"])
app.include_router(doc_router, prefix="/doc", tags=["DOC"])
app.include_router(delete_router, prefix="/delete", tags=["DELETE"])
app.include_router(xlsx_delete_router, prefix="/delete", tags=["DELETE"])

# ==== Main entry ====
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)