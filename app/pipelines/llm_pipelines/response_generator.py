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
from app.config import Config 

import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv(find_dotenv())

config = Config()



class LangChainGenerator:
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
            system_prompt = (
                "Bạn là một trợ lý ảo thân thiện và đáng tin cậy được công ty của chúng tôi giao nhiệm vụ giả làm AI để giúp người dùng với các câu hỏi về hàng hóa, hải quan, và xuất nhập cảnh.\n"
                "Nhưng đây là trường hợp không tìm được tài liệu liên quan đến câu hỏi của người dùng, nên bạn có kiến thức chung về mọi lĩnh vực.\n"
                "Hãy trả lời trực tiếp câu hỏi của người dùng, chỉ đưa ra kết quả chính xác.\n"
                "Trả lời dưới dạng Markdown, không cần mở đầu như 'Dựa trên...' hay 'Theo tài liệu...'.\n"
                "Nếu câu trả lời có code, đặt trong khối triple backticks.\n"
                "Không tiết lộ phác thảo nội bộ (chain-of-draft).\n"
                "\n"
            )

            user_prompt = (
                f"**Người dùng hỏi**: {escaped_query}\n\n"
                "Hãy tuân thủ các yêu cầu ở trên, trả lời súc tích và đúng trọng tâm, sử dụng Markdown.\n"
                "Hãy tuân thủ yêu cầu trên: mở đầu gọn, nội dung chính, kết luận với câu hỏi thân thiện."
            )

        else:
            # Có docs => RAG logic
            system_prompt = (
                "Bạn là một trợ lý ảo đáng tin cậy, chuyên về hàng hóa, hải quan, và xuất nhập cảnh.\n"
                "Nhiệm vụ của bạn là hỗ trợ người dùng với các câu hỏi chuyên sâu trong lĩnh vực này.\n"
                "Trả lời dựa trên tài liệu cung cấp, trình bày bằng Markdown.\n"
                "Không tiết lộ phác thảo nội bộ (chain-of-draft).\n"
                "Không bịa thông tin.\n"
            )

            # Xây dựng chuỗi tài liệu với metadata
            docs_with_metadata = []
            for doc in docs:
                meta = doc.metadata if hasattr(doc, "metadata") else {}
                file_name = meta.get("file_name", "Unknown")
                file_type = meta.get("file_type", "").lower()
                source = f"{file_name}{file_type}".strip()
                content = doc.page_content.replace("{", "{{").replace("}", "}}")
                docs_with_metadata.append(
                    f"**Tên file**: {source}\n**Loại file**: {file_type}\n**Nội dung**:\n{content}"
                )
            docs_str = "\n\n".join(docs_with_metadata)

            user_prompt = (
                f"**Tài liệu (sắp xếp theo thứ tự liên quan giảm dần)**:\n{docs_str}\n\n"
                "### Nhiệm vụ\n"
                f"- Người dùng hỏi: {escaped_query}\n"
                "Hãy trả lời trực tiếp nội dung, không cần viết 'Dựa trên tài liệu...' hay 'Theo tài liệu...'.\n"
                "Nếu tài liệu là PDF (file_type = 'pdf'), hãy trình bày câu trả lời theo cấu trúc:\n"
                "\n"
                "kết quả phân tích phân loại {{tên file pdf}} nội dung là:\n"
                "{{nội dung response từ top docs}}\n"
                "Trình bày đủ 5 mục về kết quả phân loại hàng hóa như trong docs:\n"
                "\n"
                "Nếu có nhiều file PDF, lặp lại cấu trúc này cho từng file.\n"
                "Hãy tuân thủ yêu cầu trên: mở đầu gọn, nội dung chính, kết luận với câu hỏi thân thiện."
            )

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
