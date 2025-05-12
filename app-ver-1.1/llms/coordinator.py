# db_search_agent.py
import logging
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_openai import ChatOpenAI
from langsmith import traceable

from prompts import get_mongodb_decision_prompt

logger = logging.getLogger(__name__)

class Coordinator:
    def __init__(self, 
                 model_name: str = "gpt-4-0613", 
                 temperature: float = 0.0):
        """
        Khởi tạo Coordinator 
        
        Args:
            model_name: Mô hình LLM sử dụng
            temperature: Nhiệt độ mô hình
        """
        logger.info("Khởi tạo Coordinator với model=%s, temperature=%.1f", model_name, temperature)
        
        # Khởi tạo LLM
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)
        
        # Lấy prompt từ module prompts
        self.tool_decision_prompt = get_mongodb_decision_prompt()
        
        logger.info("Đã khởi tạo Coordinator thành công")

    
    @traceable(run_type="llm")
    async def decide_mongodb_usage(self, query: str) -> str:
        """
        Sử dụng LLM để quyết định xem truy vấn có cần sử dụng MongoDB hay không.
        
        Args:
            query: Câu truy vấn của người dùng
            
        Returns:
            "YES" hoặc "NO"
        """
        user_prompt = f"Câu hỏi: {query}"
        decision_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(self.tool_decision_prompt),
            HumanMessagePromptTemplate.from_template(user_prompt)
        ])
        decision_chain = decision_prompt | self.llm
        decision_response = await decision_chain.ainvoke({"input": query})
        decision = decision_response.content.strip().upper()
        logger.info("Quyết định sử dụng MongoDB cho query '%s': %s", query, decision)
        return decision
    
    