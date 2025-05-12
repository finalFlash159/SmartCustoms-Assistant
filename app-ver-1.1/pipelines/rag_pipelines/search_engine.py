from .vector_store import VectorStoreManager
from typing import List
from langchain_core.documents import Document

class SearchEngine:
    def __init__(self, vector_store: VectorStoreManager, threshold: float = 0.4):
        """
        HybridRetriever sử dụng vector search để lấy candidate documents ban đầu,
        sau đó dùng BM25 để re-rank theo truy vấn dựa trên token matching.
        """
        self.vector_store = vector_store
        self.threshold = threshold

    async def retrieve(self, query: str, top_k: int = 20) -> List[Document]:
        """
        Lấy danh sách tài liệu ban đầu từ vector_store rồi lọc lại theo threshold.

        Args:
            query (str): Truy vấn tìm kiếm.
            top_k (int): Số lượng tài liệu cần trả về.

        Returns:
            List[Document]: Danh sách tài liệu đã được lọc theo threshold.
        """
        # Lấy candidate documents từ vector store.
        candidates_with_scores = await self.vector_store.get_relevant_documents_with_scores(query, top_k)
        
        # Lọc doc có score >= threshold
        filtered_docs = []
        for doc, score in candidates_with_scores:
            if score >= self.threshold:
                filtered_docs.append(doc)

        # Nếu sau khi lọc không còn doc => trả về rỗng => fallback
        if not filtered_docs:
            return []

        # Trả về top_k doc
        return filtered_docs[:top_k]
