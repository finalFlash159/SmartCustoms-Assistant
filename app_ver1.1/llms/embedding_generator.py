from langchain_openai import OpenAIEmbeddings
from typing import List
from config import Config

config = Config()

class EmbeddingGenerator:
    """
    Lớp này chịu trách nhiệm gọi OpenAI Embeddings để chuyển văn bản thành vector.
    Nó cũng xử lý các vấn đề liên quan như:
      - Chia batch (chunk) nếu danh sách văn bản quá lớn (để tiết kiệm số lần gọi API).
      - Retry (thử lại) nếu gọi API thất bại (do lỗi mạng, rate limit...).
      - Cho phép cấu hình model, API key, số lần retry, kích thước batch...
    """

    def __init__(
        self,
        model_name: str = config.EMBEDDING_MODEL_NAME,
        api_key: str = None,
        chunk_size: int = config.CHUNK_SIZE,
        max_retries: int = config.MAX_RETRIES,
    ):
        """
        Khởi tạo EmbeddingGenerator.

        Args:
            model_name (str): Tên mô hình OpenAI Embedding, ví dụ "text-embedding-ada-002".
            api_key (str, optional): API key của OpenAI.
            chunk_size (int): Số lượng text tối đa trong mỗi batch (mặc định 1000).
            max_retries (int): Số lần thử lại nếu gọi API gặp lỗi (mặc định 5).
        """
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.embedding_model = OpenAIEmbeddings(model=model_name, openai_api_key=api_key)

    def embed_query(self, text: str) -> List[float]:
        """
        Gọi API OpenAI để embedding 1 đoạn text (chuỗi).
        Trả về list float (vector embedding).

        Args:
            text (str): Đoạn văn bản cần chuyển thành vector.

        Returns:
            List[float]: Vector embedding, độ dài phụ thuộc model.
        """
        for attempt in range(self.max_retries):
            try:
                return self.embedding_model.embed_query(text)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
        return []

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed nhiều text cùng lúc. Ta chia text thành từng batch (chunk) để tối ưu gọi API.

        Args:
            texts (List[str]): Danh sách các chuỗi.

        Returns:
            List[List[float]]: Mảng 2 chiều, mỗi phần tử là 1 vector cho 1 chuỗi.
        """
        all_vectors = []
        for i in range(0, len(texts), self.chunk_size):
            batch = texts[i : i + self.chunk_size]
            vectors = self._embed_batch(batch)
            all_vectors.extend(vectors)
        return all_vectors

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Hàm private để embedding 1 batch text bằng 1 lần gọi API duy nhất.

        Args:
            texts (List[str]): Danh sách chuỗi (batch) cần embedding.

        Returns:
            List[List[float]]: Mỗi chuỗi 1 vector.
        """
        for attempt in range(self.max_retries):
            try:
                return self.embedding_model.embed_documents(texts)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
        return []
