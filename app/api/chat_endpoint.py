import uuid
from fastapi import APIRouter, HTTPException, Request, Response, Cookie
import logging
from pydantic import BaseModel
import sys

sys.path.append('../') 

from pipelines.llm_pipelines.response_generator import LangChainGenerator

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary lưu các instance của LangChainGenerator theo session_id
conversation_instances = {}

class ChatRequest(BaseModel):
    prompt: str
    package: str

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
    package = chat_request.package

    try:
        # 1) Tạo/Gán session
        if not session_id:
            session_id = str(uuid.uuid4())
            response.set_cookie(key="session_id", value=session_id)
            logger.info(f"New session created: {session_id}")
        
        # 2) Lấy hoặc tạo instance LangChainGenerator cho session
        if session_id not in conversation_instances:
            conversation_instances[session_id] = LangChainGenerator(
                openai_api_key=request.app.state.config.OPENAI_API_KEY
            )
            logger.info(f"New LangChainGenerator instance created for session: {session_id}")
        generator = conversation_instances[session_id]

        # 3) Lấy ToolAgent từ queue
        tool_agent_queue = getattr(request.app.state, "tool_agent_queue", None)
        if not tool_agent_queue:
            logger.error("No tool_agent_queue found in app.state.")
            raise HTTPException(status_code=500, detail="ToolAgent queue not initialized.")

        tool_agent = await tool_agent_queue.get()  # Lấy 1 ToolAgent từ pool

         # Cập nhật package từ request
        tool_agent.set_package(package)
        logger.info("Đã cập nhật package của ToolAgent thành: %s", tool_agent.package)

        try:
            # Dùng ToolAgent để quyết định có dùng tool hay không
            use_tool = await tool_agent.decide_tool_usage(prompt)
            logger.info(f"Tool usage decision for query '{prompt}': {use_tool}")

            if use_tool:
                # Nếu cần tool, sử dụng agent chain của ToolAgent để gọi tool
                agent_result = tool_agent.decide_and_run(prompt)
                logger.info(f"ToolAgent returned: {agent_result}")
                return {"response": agent_result}
            else:
                # Nếu không dùng tool, thực hiện truy vấn RAG
                search_engine = await request.app.state.search_engine_queue.get()
                try:
                    retrieved_docs = await search_engine.retrieve(prompt, top_k=10)
                    logger.info(f"Retrieved {len(retrieved_docs)} documents for query: {prompt}")
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
                                query=prompt,
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
            # Trả ToolAgent về queue
            await tool_agent_queue.put(tool_agent)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi hệ thống. Vui lòng thử lại sau.")
