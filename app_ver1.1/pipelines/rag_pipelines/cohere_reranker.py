import cohere
import asyncio


class AsyncCohereReranker:
    def __init__(self, api_key: str, model: str = "rerank-v3.5"):
        """
        Khởi tạo AsyncCohereReranker với API key và model rerank.
        """
        self.client = cohere.AsyncClientV2(api_key)
        self.model = model

    async def rerank(self, query: str, documents: list, top_n: int = 10):
        """
        Hàm rerank bất đồng bộ nhận vào:
          - query: truy vấn dạng chuỗi.
          - documents: danh sách các văn bản.
          - top_n: số lượng kết quả cần trả về (mặc định 3).
        Trả về kết quả từ endpoint rerank của Cohere.
        """
        # Nếu không có tài liệu, trả về danh sách rỗng
        if not documents:
            return []

        response = await self.client.rerank(
            model=self.model,
            query=query,
            documents= documents,
            top_n=top_n
        )
        return response