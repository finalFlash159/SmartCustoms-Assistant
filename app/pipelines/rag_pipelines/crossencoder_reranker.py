import os
from typing import List, Tuple, Callable
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document

class CrossReranker:
    def __init__(self, 
                 model_id: str = 'itdainb/PhoRanker', 
                 max_length: int = 256, 
                 model_cache_dir: str = 'models/pho_ranker', 
                 segmenter: Callable[[str], str] = None):
        """
        Khởi tạo reranker sử dụng mô hình PhoRanker.
        
        Args:
            model_id (str): ID của mô hình, mặc định 'itdainb/PhoRanker'.
            max_length (int): Độ dài tối đa của input cho mô hình.
            model_cache_dir (str): Thư mục lưu model. Nếu model đã tồn tại ở đây thì load từ đó, nếu không sẽ tải và lưu.
            segmenter (Callable[[str], str], optional): Hàm tiền xử lý (word segmentation) cho văn bản.
                Nếu không cung cấp, mặc định là hàm identity.
        """
        self.model_id = model_id
        self.max_length = max_length
        self.model_cache_dir = model_cache_dir
        self.segmenter = segmenter if segmenter is not None else lambda x: x  # identity function
        
        # Kiểm tra nếu thư mục model_cache_dir đã tồn tại, load model từ đó, ngược lại tải model và lưu
        if os.path.exists(model_cache_dir):
            self.model = CrossEncoder(model_cache_dir, max_length=max_length)
        else:
            self.model = CrossEncoder(model_id, max_length=max_length)
            # Nếu cần sử dụng fp16 (với GPU hỗ trợ), có thể bật:
            # self.model.model.half()
            os.makedirs(model_cache_dir, exist_ok=True)
            self.model.save(model_cache_dir)
    
    def rerank(self, query: str, docs: List[Document]) -> List[Tuple[Document, float]]:
        """
        Re-rank các Document dựa trên mức độ liên quan với truy vấn.
        
        Quy trình:
        - Nếu không có tài liệu, trả về danh sách rỗng
          1. Áp dụng tiền xử lý (segmentation) cho truy vấn và nội dung của từng Document.
          2. Tạo các cặp [query, document_text] cho mô hình.
          3. Dự đoán điểm số cho từng cặp.
          4. Sắp xếp các Document theo điểm số giảm dần và trả về danh sách tuple (document, score).
        
        Args:
            query (str): Truy vấn tìm kiếm.
            docs (List[Document]): Danh sách Document, mỗi Document cần có thuộc tính `page_content` hoặc `text`.
        
        Returns:
            List[Tuple[Document, float]]: Danh sách các tuple (Document, score) đã được sắp xếp giảm dần theo score.
        """
        # Nếu không có tài liệu, trả về danh sách rỗng
        if not docs:
            return []
        
        # Áp dụng segmentation cho truy vấn
        tokenized_query = self.segmenter(query)
        
        pairs = []
        for doc in docs:
            # Lấy nội dung của document: ưu tiên thuộc tính page_content, nếu không có thì dùng text
            doc_text = getattr(doc, 'page_content', None) or getattr(doc, 'text', '')
            tokenized_doc = self.segmenter(doc_text)
            if len(tokenized_doc.split()) > self.max_length:
                tokenized_doc = " ".join(tokenized_doc.split()[:self.max_length])
            pairs.append([tokenized_query, tokenized_doc])
        
        # Dự đoán điểm số cho từng cặp [query, document]
        scores = self.model.predict(pairs)
        
        # Kết hợp Document với score và sắp xếp giảm dần theo score
        doc_scores = list(zip(docs, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        return doc_scores

    def get_score(self, query: str, docs: List[Document]) -> List[float]:
        """
        Tính điểm cho từng Document dựa trên truy vấn mà không sắp xếp kết quả và chỉ trả về danh sách score.
        
        Quy trình:
          1. Áp dụng tiền xử lý (segmentation) cho truy vấn và nội dung của từng Document.
          2. Tạo các cặp [query, document_text] cho mô hình.
          3. Dự đoán điểm số cho từng cặp.
          4. Trả về danh sách các score theo thứ tự tương ứng với danh sách tài liệu.
        
        Args:
            query (str): Truy vấn tìm kiếm.
            docs (List[Document]): Danh sách Document.
        
        Returns:
            List[float]: Danh sách các score không được sắp xếp.
        """
        if not docs:
            return []
        
        tokenized_query = self.segmenter(query)
        pairs = []
        for doc in docs:
            doc_text = getattr(doc, 'page_content', None) or getattr(doc, 'text', '')
            tokenized_doc = self.segmenter(doc_text)
            if len(tokenized_doc.split()) > self.max_length:
                tokenized_doc = " ".join(tokenized_doc.split()[:self.max_length])
            pairs.append([tokenized_query, tokenized_doc])
        
        scores = self.model.predict(pairs)
        return scores
