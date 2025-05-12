from typing import List
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langchain.schema import Document
from langsmith import traceable
from dotenv import load_dotenv, find_dotenv
from config import Config 
from prompts.response_prompts import (
    get_fallback_system_prompt,
    get_fallback_user_prompt,
    get_rag_system_prompt,
    get_rag_user_prompt
)

import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv(find_dotenv())

config = Config()

class ResponseGenerator:
    def __init__(
        self,
        openai_api_key: str,
        model_name: str = config.GENERATE_MODEL_NAME,
        temperature: float = config.TEMPERATURE
    ):
        self.llm = ChatOpenAI(
        openai_api_key=openai_api_key,
        model_name=model_name,
        temperature=temperature,
        )

        # self.memory = ConversationBufferMemory(return_messages=True)

    @traceable(run_type="retriever")
    async def generate_response(self, query: str, docs: List[Document] = None) -> str:
        """
        Sinh câu trả lời dựa trên query và tài liệu (docs) nếu có.
        - Nếu docs rỗng: fallback -> mô hình trả lời theo kiến thức chung.
        - Nếu có docs: mô hình trả lời theo RAG, với cấu trúc đặc biệt cho file PDF.
        """
        # Thoát các ký tự đặc biệt trong query để tránh lỗi ChatPromptTemplate
        escaped_query = query.replace("{", "{{").replace("}", "}}")

        if not docs:
            # Fallback: không có docs
            system_prompt = get_fallback_system_prompt()
            user_prompt = get_fallback_user_prompt(escaped_query)

        else:
            # Có docs => RAG logic
            system_prompt = get_rag_system_prompt()
            # Xây dựng chuỗi tài liệu với metadata
            docs_with_metadata = []
            for doc in docs:
                meta = doc.metadata if hasattr(doc, "metadata") else {}
                file_name = meta.get("file_name", "Unknown")
                file_type = meta.get("file_type", "").lower()
                download_url = meta.get("download_url", "")
                source = f"{file_name}{file_type}".strip()
                content = doc.page_content.replace("{", "{{").replace("}", "}}")

                            # Xây dựng chuỗi tài liệu có cả metadata và download_url
                doc_str = f"**Tên file**: {source}\n**Loại file**: {file_type}\n**Nội dung**:\n{content}"
                
                # Thêm URL tải xuống nếu có
                if download_url:
                    doc_str += f"\n**Download URL**: {download_url}"
                
                docs_with_metadata.append(doc_str)

            docs_str = "\n\n".join(docs_with_metadata)

            user_prompt = get_rag_user_prompt(escaped_query, docs_str)

        try:
            system_message_template = SystemMessagePromptTemplate.from_template(system_prompt)
            user_message_template = HumanMessagePromptTemplate.from_template(user_prompt)
            chat_prompt = ChatPromptTemplate.from_messages([
                system_message_template,
                user_message_template
            ])
            chain = chat_prompt | self.llm
            response = await chain.ainvoke(
                {"input": escaped_query}, 
            )
            
            # Lưu lịch sử hội thoại
            answer_text = response.content
            return answer_text.strip()

        except Exception as e:
            logging.error(f"Lỗi khi sinh câu trả lời: {e}")
            return "Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu của bạn."
