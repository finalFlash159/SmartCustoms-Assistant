import uuid
import logging
import sys

from fastapi import APIRouter, HTTPException, Request, Response, Cookie
from pydantic import BaseModel
sys.path.append('../') 
from llms.response_generator import ResponseGenerator
from utils.query_processor import process_query

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary lưu các instance của ResponseGenerator theo session_id
conversation_instances = {}

class ChatRequest(BaseModel):
    prompt: str
    num_results: int

@router.post("/chat")
async def chat(
    request: Request,
    response: Response,
    chat_request: ChatRequest,
    session_id: str = Cookie(default=None),
):
    """
    Endpoint chat duy trì cuộc hội thoại theo phiên.
    - Nếu không có session_id, tạo mới và gán qua cookie.
    - Nếu có, sử dụng instance đã lưu để duy trì history cho đến khi phiên kết thúc.
    - Dựa vào quyết định của ToolAgent (YES/NO), nếu cần tool thì gọi agent chain, ngược lại fallback sang RAG.
    """
    prompt = chat_request.prompt


    try:
        # 1) Tạo/Gán session
        if not session_id:
            session_id = str(uuid.uuid4())
            response.set_cookie(key="session_id", value=session_id)
            logger.info(f"New session created: {session_id}")
        
        # 2) Lấy hoặc tạo instance LangChainGenerator cho session
        if session_id not in conversation_instances:
            conversation_instances[session_id] = ResponseGenerator(
                openai_api_key=request.app.state.config.OPENAI_API_KEY
            )
            logger.info(f"New ResponseGenerator instance created for session: {session_id}")
        generator = conversation_instances[session_id]

        # 3) Lấy Coordinator từ queue
        coordinator_queue = getattr(request.app.state, "coordinator_queue", None)
        if not coordinator_queue:
            logger.error("No coordinator_queue found in app.state.")
            raise HTTPException(status_code=500, detail="Coordinator queue not initialized.")

        coordinator = await coordinator_queue.get()  # Lấy 1 Coordinator từ pool

         # Cập nhật package từ request
        # coordinator.set_package(package)
        # logger.info("Đã cập nhật package của Coordinator thành: %s", coordinator.package)

        try:
            # Dùng Coordinator để quyết định có dùng tool hay không
            use_mongodb = await coordinator.decide_mongodb_usage(prompt)
            logger.info(f"MongoDB usage decision for query '{prompt}': {use_mongodb}")

            if use_mongodb == "YES":
                # Nếu dùng MongoDB, thực hiện truy vấn MongoDB
                mongodb_search = await request.app.state.mongodb_search_queue.get()
                try:
                    retrieved_docs = await mongodb_search.handle_query(prompt)
                    logger.info(f"Retrieved {len(retrieved_docs)} documents for query: {prompt}")
                    return {"response": retrieved_docs}
                finally:
                    await request.app.state.mongodb_search_queue.put(mongodb_search) 
            else:
                # Nếu không dùng MongoDB, thực hiện truy vấn RAG
                search_engine = await request.app.state.search_engine_queue.get()
                try:
                    processed_prompt = process_query(prompt)
                    retrieved_docs = await search_engine.retrieve(processed_prompt, top_k=10)
                    logger.info(f"Retrieved {len(retrieved_docs)} documents for query: {processed_prompt}")
                finally:
                    await request.app.state.search_engine_queue.put(search_engine)

                top_docs = []
                if retrieved_docs:
                    page_contents = [
                        doc.page_content for doc in retrieved_docs
                        if doc.page_content and doc.page_content.strip()
                    ]
                    if page_contents:
                        reranker = await request.app.state.async_cohere_reranker_queue.get()
                        try:
                            reranked_response = await reranker.rerank(
                                query=processed_prompt,
                                documents=page_contents,
                                top_n=5
                            )
                            top_docs = [
                                retrieved_docs[result.index]
                                for result in reranked_response.results
                                if 0 <= result.index < len(retrieved_docs)
                            ]
                        finally:
                            await request.app.state.async_cohere_reranker_queue.put(reranker)
                    else:
                        logger.warning("No valid page_content after filtering.")
                else:
                    logger.warning("No documents retrieved from search engine.")

                # Gọi LLM tạo phản hồi dựa trên query và top_docs
                answer_text = await generator.generate_response(query=prompt, docs=top_docs)
                logger.info(f"Response generated for session {session_id}")
                logger.info(f"LLM response: {answer_text}")
                return {"response": answer_text}

        finally:
            # Trả Coordinator về queue
            await coordinator_queue.put(coordinator)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi hệ thống. Vui lòng thử lại sau.")
