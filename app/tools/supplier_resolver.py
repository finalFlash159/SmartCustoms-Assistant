import logging
import mysql.connector
from typing import List
from rapidfuzz import process, fuzz

logger = logging.getLogger(__name__)

class SupplierResolver:
    """
    Lớp này lấy danh sách DISTINCT nhà cung cấp, sau đó so khớp
    bằng fuzzy matching để gợi ý top 5 kết quả, threshold > 0.75.
    """

    def __init__(self, db_config: dict):
        self.db_config = db_config

    def get_distinct_suppliers(self) -> List[str]:
        """
        Lấy tất cả nhà cung cấp duy nhất từ DB.
        """
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT NhaCungCap FROM import_data ORDER BY NhaCungCap;")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        suppliers = [row[0] for row in rows if row[0]]
        return suppliers

    def match_suppliers_fuzzy(self, user_input: str) -> List[str]:
        """
        Dùng fuzzy matching (rapidfuzz) để tìm top 5 supplier gần nhất
        so với user_input, với threshold = 0.75 (75%).
        Viết hoa toàn bộ user_input trước khi match.
        """
        suppliers = self.get_distinct_suppliers()
        if not suppliers:
            return []

        # Chuyển toàn bộ user_input thành uppercase
        user_input_upper = user_input.upper()

        # Tương tự, nếu muốn, bạn cũng có thể chuyển suppliers thành uppercase
        # suppliers_upper = [s.upper() for s in suppliers]
        # rồi fuzzy match trên suppliers_upper, sau đó map ngược lại.
        # Kiểm tra xem có supplier nào đạt điểm khớp >= 90% không
        
        exact_matches = [s for s in suppliers if fuzz.partial_ratio(user_input_upper, s.upper().strip()) >= 90]
        if exact_matches:
            return exact_matches

        raw_results = process.extract(
            user_input_upper,
            suppliers,   # hoặc suppliers_upper
            limit=5,
            scorer=fuzz.WRatio
        )
        # raw_results: List[(supplier_name, score, index)]

        # Chỉ lấy tên supplier, score >= 75
        top_matches = [r[0] for r in raw_results if r[1] >= 80]

        return top_matches