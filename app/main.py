import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio

from config import Config
from pipelines.rag_pipelines.crossencoder_reranker import CrossReranker
from pipelines.rag_pipelines.vector_store import VectorStoreManager
from pipelines.rag_pipelines.search_engine import SearchEngine
from pipelines.rag_pipelines.cohere_reranker import AsyncCohereReranker

# Agent
from pipelines.llm_pipelines.agent_decision import ToolAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === VectorStoreManager Pool ===
    num_vector_stores = config.NUM_VECTOR_STORES
    app.state.vector_store_pool = [
        VectorStoreManager(
            collection_name=config.QDRANT_COLLECTION_NAME,
            openai_api_key=config.OPENAI_API_KEY,
            qdrant_api_key=config.QDRANT_API_KEY,
            qdrant_url=config.QDRANT_URL,
            prefer_grpc=True,
        )
        for _ in range(num_vector_stores)
    ]
    for vs in app.state.vector_store_pool:
        await vs.init_collection()
    app.state.vector_store_queue = asyncio.Queue()
    for vs in app.state.vector_store_pool:
        await app.state.vector_store_queue.put(vs)
    logger.info(f"Khởi tạo queue cho {num_vector_stores} VectorStoreManager.")

    # === SearchEngine Pool & Queue ===
    app.state.search_engine_pool = [
        SearchEngine(vector_store=app.state.vector_store_pool[i])
        for i in range(num_vector_stores)
    ]
    app.state.search_engine_queue = asyncio.Queue()
    for se in app.state.search_engine_pool:
        await app.state.search_engine_queue.put(se)
    logger.info(f"Khởi tạo pool với {num_vector_stores} SearchEngine.")

    # === AsyncCohereReranker Pool & Queue === 
    num_rerankers = config.NUM_RERANKERS
    reranker_list = [AsyncCohereReranker(api_key=config.COHERE_API_KEY) for _ in range(num_rerankers)]
    app.state.async_cohere_reranker_queue = asyncio.Queue()
    for r in reranker_list:
        await app.state.async_cohere_reranker_queue.put(r)
    logger.info(f"Khởi tạo pool với {num_rerankers} AsyncCohereReranker.")

    # === Khởi tạo ToolAgent ===
    db_config ={
        "host": config.backend_host,
        "user": config.backend_user,
        "password": config.backend_password,
        "database": config.backend_databasse,
        "use_pure": config.backend_user_pure,  
        "port": config.backend_port  
    }
        
    num_agents = config.NUM_AGENTS
    tool_agent_pool = []
    for i in range(num_agents):
        agent = ToolAgent(
            model_name=config.AGENT_MODEL_NAME,
            temperature=config.AGENT_TEMPERATURE,
            db_config=db_config
        )
        tool_agent_pool.append(agent)

    # Tạo queue
    app.state.tool_agent_queue = asyncio.Queue()
    for ag in tool_agent_pool:
        await app.state.tool_agent_queue.put(ag)
    logger.info(f"Khởi tạo pool với {num_agents} ToolAgent.")
    
    # Lưu config để dùng chung
    app.state.config = config
    app.state.db_config = db_config
    
    yield  # Chuyển giao quyền điều khiển cho ứng dụng
    
    print("Shutdown")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.request_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import router từ các endpoint
from api.chat_endpoint import router as chat_router
from api.pdf_endpoint import router as pdf_router
from api.xlsx_endpoint import router as xlsx_router
from api.doc_endpoint import router as doc_router
from api.delete_endpoint import router as delete_router
from api.xlsx_delete import router as xlsx_delete_router

app.include_router(chat_router, prefix="/api", tags=["CHAT"])
app.include_router(pdf_router, prefix="/pdf", tags=["PDF"])
app.include_router(xlsx_router, prefix="/xlsx", tags=["XLSX"])
app.include_router(doc_router, prefix="/doc", tags=["DOC"])
app.include_router(delete_router, prefix="/delete", tags=["DELETE"])
app.include_router(xlsx_delete_router, prefix="/delete", tags=["DELETE"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
