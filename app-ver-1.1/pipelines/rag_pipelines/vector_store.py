import os
import asyncio
from typing import List, Dict, Tuple, Any
from datetime import datetime
import uuid

from qdrant_client.async_qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    CollectionStatus,
    Filter,
    FieldCondition,
    MatchValue,
    ScoredPoint
)
from qdrant_client.models import VectorParams, Distance, PointStruct
from langchain_core.documents import Document

from llms.embedding_generator import EmbeddingGenerator


class VectorStoreManager:
    def __init__(
        self,
        collection_name: str = "chatbot_embeddings",
        host: str = "localhost",
        port: int = 6333,
        openai_api_key: str = None,
        qdrant_api_key: str = None,
        qdrant_url: str = None,
        prefer_grpc: bool = True,
    ):
        """
        Quản lý lưu trữ embedding trong Qdrant, sử dụng AsyncQdrantClient gốc (không dùng langchain_qdrant).
        
        Args:
            collection_name (str): Tên collection trong Qdrant.
            host (str): Host Qdrant, mặc định "localhost".
            port (int): Port Qdrant, mặc định 6333.
            openai_api_key (str): API key OpenAI, nếu cần cho EmbeddingGenerator.
            qdrant_api_key (str): API key Qdrant (nếu dùng Qdrant Cloud).
            qdrant_url (str): URL Qdrant, vd "http://localhost:6333". Nếu không truyền, build từ host+port.
            prefer_grpc (bool): Ưu tiên gRPC thay vì REST. Mặc định True.
        """
        self.collection_name = collection_name

        # Tạo EmbeddingGenerator
        self.embedding_generator = EmbeddingGenerator(
            api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
        )

        # Nếu qdrant_url chưa có, build từ host + port
        if not qdrant_url:
            qdrant_url = f"http://{host}:{port}"

        # Khởi tạo AsyncQdrantClient (ưu tiên gRPC)
        self.qdrant_client = AsyncQdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            prefer_grpc=prefer_grpc,
            timeout=6000
        )

    async def init_collection(self):
        """
        Gọi hàm này 1 lần (vd trong lifespan) để tạo/kiểm tra collection.
        """
        collections_response = await self.qdrant_client.get_collections()
        existing_collections = [col.name for col in collections_response.collections]

        if self.collection_name not in existing_collections:
            # Lấy kích thước embedding (lấy embedding 1 câu dummy)
            dummy_text = "Test"
            vector_size = len(self.embedding_generator.embedding_model.embed_query(dummy_text))

            # Tạo collection mới
            vector_config = VectorParams(size=vector_size, distance=Distance.COSINE)
            await self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=vector_config
            )
            print(f"[VectorStoreManager] Đã tạo collection '{self.collection_name}' với vector_size={vector_size}")
        else:
            # Kiểm tra trạng thái
            col_info = await self.qdrant_client.get_collection(self.collection_name)
            if col_info.status != CollectionStatus.GREEN:
                raise Exception(f"Collection {self.collection_name} không ở trạng thái GREEN.")

    async def store_embeddings(self, texts: List[str], metadata: List[Dict[str, Any]] = None):
        """
        Lưu trữ embedding và metadata vào Qdrant giống như cách QdrantVectorStore thực hiện.

        Args:
            texts (List[str]): Danh sách văn bản cần lưu.
            metadata (List[Dict[str, Any]]): Danh sách metadata tương ứng với từng văn bản.
        """
        if not texts:
            raise ValueError("Danh sách văn bản không được rỗng.")

        # Tạo embedding từ văn bản
        embeddings = self.embedding_generator.embed_documents(texts)

        # Chuẩn bị metadata (nếu không có thì tạo mặc định)
        if metadata is None:
            metadata = [{} for _ in range(len(texts))]
        for meta in metadata:
            meta["timestamp"] = datetime.now().isoformat()  # Thêm timestamp như QdrantVectorStore

        # Tạo danh sách PointStruct
        points = []
        for text, emb, meta in zip(texts, embeddings, metadata):
            # Tạo payload giống QdrantVectorStore
            payload = {
                "page_content": text,
                "metadata": meta
            }

            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=emb,
                payload=payload
            )
            points.append(point)

        # Upsert vào Qdrant
        await self.qdrant_client.upsert(
            collection_name=self.collection_name,
            wait=True,  # Chờ hoàn tất
            points=points
        )

        print(f"Đã lưu {len(texts)} embedding vào collection '{self.collection_name}'")

    async def get_relevant_documents(self, query: str, top_k: int = 20) -> List[Document]:
        """
        Tìm kiếm các văn bản liên quan theo query embedding. 
        Trả về danh sách Document (chỉ content, metadata).
        """
        await self.init_collection()

        # Embed query
        query_emb = self.embedding_generator.embedding_model.embed_query(query)

        # Gọi search
        search_results: List[ScoredPoint] = await self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_emb,
            limit=top_k,
            with_payload=True,
            with_vectors=False
        )

        # Chuyển thành list Document
        docs: List[Document] = []
        for point in search_results:
            # point.payload["content"] là nội dung gốc
            content = point.payload.get("content", "")
            # Bỏ "content" khỏi payload nếu muốn metadata rành mạch
            meta = dict(point.payload)
            meta.pop("content", None)

            doc = Document(page_content=content, metadata=meta)
            docs.append(doc)
        return docs

    async def get_relevant_documents_with_scores(self, query: str, top_k: int = 50) -> List[Tuple[Document, float]]:
        """
        Trả về danh sách (Document, similarity score) bằng cách sử dụng QdrantClient trực tiếp.

        Args:
            query (str): Truy vấn của người dùng.
            top_k (int): Số lượng tài liệu liên quan trả về (mặc định 50).

        Returns:
            List[Tuple[Document, float]]: Danh sách các tài liệu và điểm tương đồng.
        """
        # Embed truy vấn thành vector
        query_vector = self.embedding_generator.embedding_model.embed_query(query)

        # Thực hiện tìm kiếm với QdrantClient
        search_result = await self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,  # Lấy payload (page_content và metadata)
            with_vectors=False   # Không cần vector trong kết quả
        )

        # Chuyển đổi kết quả thành List[Tuple[Document, float]]
        results = []
        for hit in search_result:
            # Tạo Document từ payload
            doc = Document(
                page_content=hit.payload.get("page_content", ""),
                metadata=hit.payload.get("metadata", {})
            )
            score = hit.score  # Điểm tương đồng
            results.append((doc, score))

        return results


    async def delete_points_by_metadata(self, file_name: str, file_type: str):
        """
        Xóa points theo metadata.
        """
        await self.init_collection()

        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="metadata.file_name",  # Truy cập payload["metadata"]["file_name"]
                    match=MatchValue(value=file_name)
                ),
                FieldCondition(
                    key="metadata.file_type",  # Truy cập payload["metadata"]["file_type"]
                    match=MatchValue(value=file_type)
                )
            ]
        )

        await self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=filter_condition,
            wait=True
        )

        print(f"[VectorStoreManager] Đã xóa points có metadata.file_name='{file_name}' và metadata.file_type='{file_type}'")
