"""
Prompt và schema cho việc tạo MongoDB pipeline
"""
from typing import Dict, Any, List
from prompts.constants import FIELDS, VALID_DIEU_KIEN_GIAO_HANG, TRANSACTION_STATUSES, VALID_LOAI_HINH

# MongoDB search template
MONGODB_SEARCH_TEMPLATE = (
    "Bạn là chuyên gia MongoDB search và query. "
    "User có thể hỏi bất kỳ trường nào trong bộ dữ liệu sau:"
    "['ngay','nha_cung_cap','hs_code','ten_hang','loai_hinh','don_vi_tinh',"
    "'xuat_xu','dieu_kien_giao_hang','thue_suat_xnk','thue_suat_ttdb',"
    "'thue_suat_vat','thue_suat_tu_ve','thue_suat_bvmt', tinh_trang']" 
    "Phân tích câu hỏi và phân loại truy vấn vào các nhóm sau:"
    "1. FUZZY_SEARCH: Áp dụng cho trường 'ten_hang', 'nha_cung_cap' và 'xuat_xu'"
    "2. REGEX: Chỉ áp dụng cho trường 'hs_code'"
    "3. EXACT_MATCH: Áp dụng cho tất cả các trường còn lại"
    "Lưu ý đặc biệt:"
    "- Trường 'tinh_trang' chỉ có thể nhận một trong hai giá trị: 'Nhập' hoặc 'Xuất'"
    "- Trường 'ngay' lưu trữ theo định dạng ISO với thời gian: 'yyyy-mm-ddT00:00:00' (VD: 2023-05-15T00:00:00). Người dùng có thể nhập theo cách khác là dd/mm/yyyy (VD: 15/05/2023). Khi so khớp ngày cụ thể, sử dụng regex để tìm tất cả record trong ngày đó: {'ngay': {'$regex': '^2023-05-15'}}"
    "- Khi truy vấn khoảng ngày (từ ngày X đến ngày Y), sử dụng: {'ngay': {'$gte': 'X:T00:00:00', '$lte': 'Y:T23:59:59'}}"
    "- Trường 'dieu_kien_giao_hang' chỉ có thể nhận một trong các giá trị: "
    f"{VALID_DIEU_KIEN_GIAO_HANG}"
    "- Trường 'loai_hinh' chỉ có thể nhận một trong các giá trị: "
    f"{VALID_LOAI_HINH}"
    "- Trường 'xuat_xu' cần được tìm kiếm fuzzy với mapping quốc gia"
    "Sinh JSON arguments cho function 'generate_search_query'"
)

# Function schema cho việc tạo query
GENERATE_SEARCH_QUERY_SCHEMA = {
    "name": "generate_search_query",
    "description": "Generate search queries for different field types in MongoDB",
    "parameters": {
        "type": "object",
        "properties": {
            "fuzzy_search": {
                "type": "object",
                "properties": {
                    "ten_hang": {"type": "string", "description": "Search term for ten_hang field using fuzzy match"},
                    "nha_cung_cap": {"type": "string", "description": "Search term for nha_cung_cap field using fuzzy match"},
                    "xuat_xu_keywords": {"type": "string", "description": "Tên quốc gia hoặc mã quốc gia để tìm kiếm theo xuất xứ với fuzzy match"}
                }
            },
            "regex_search": {
                "type": "object",
                "properties": {
                    "hs_code": {"type": "string", "description": "Search pattern for hs_code field using regex"}
                }
            },
            "exact_match": {
                "type": "object",
                "properties": {
                    "ngay": {
                        "type": "string",
                        "description": "Exact date in YYYY-MM-DD format. IMPORTANT: In database, dates are stored as ISO format like '2025-02-01T00:00:00'. Use regex match with prefix: {'ngay': {'$regex': '^2025-02-01'}}."
                    },
                    "loai_hinh": {
                        "type": "string", 
                        "description": "Exact value for loai_hinh field, one of valid loai_hinh values",
                        "enum": VALID_LOAI_HINH
                    },
                    "don_vi_tinh": {"type": "string", "description": "Exact value for don_vi_tinh field"},
                    "dieu_kien_giao_hang": {
                        "type": "string", 
                        "description": "Exact value for dieu_kien_giao_hang field, one of Incoterms values",
                        "enum": VALID_DIEU_KIEN_GIAO_HANG
                    },
                    "thue_suat_xnk": {"type": "string", "description": "Exact value for thue_suat_xnk field"},
                    "thue_suat_ttdb": {"type": "string", "description": "Exact value for thue_suat_ttdb field"},
                    "thue_suat_vat": {"type": "string", "description": "Exact value for thue_suat_vat field"},
                    "thue_suat_tu_ve": {"type": "string", "description": "Exact value for thue_suat_tu_ve field"},
                    "thue_suat_bvmt": {"type": "string", "description": "Exact value for thue_suat_bvmt field"},
                    "tinh_trang": {
                        "type": "string", 
                        "description": "Transaction type, only accepts two values: 'Nhập' or 'Xuất'",
                        "enum": TRANSACTION_STATUSES
                    }
                }
            },
            "range_queries": {
                "type": "object",
                "properties": {
                    "ngay": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                            "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"}
                        },
                        "description": "For date range queries with dates stored as ISO format in database, use: {'ngay': {'$gte': start_date+'T00:00:00', '$lte': end_date+'T23:59:59'}}"
                    }
                }
            }
        }
    }
}

def get_mongodb_search_template() -> str:
    """
    Trả về template cho MongoDB search
    
    Returns:
        str: Template cho MongoDB search
    """
    return MONGODB_SEARCH_TEMPLATE

def get_generate_search_query_schema() -> Dict[str, Any]:
    """
    Trả về schema cho function generate_search_query
    
    Returns:
        Dict[str, Any]: Schema cho function generate_search_query
    """
    return GENERATE_SEARCH_QUERY_SCHEMA

def create_custom_search_template(fields: List[str] = None, 
                                include_examples: bool = True) -> str:
    """
    Tạo template tùy chỉnh dựa trên các trường cần tìm kiếm
    
    Args:
        fields: Danh sách các trường cần tìm kiếm, mặc định là tất cả các trường
        include_examples: Có bao gồm ví dụ hay không
        
    Returns:
        str: Template tùy chỉnh
    """
    # Sử dụng tất cả các trường nếu không có trường nào được chỉ định
    if fields is None:
        fields = FIELDS
    
    template = (
        "Bạn là chuyên gia MongoDB search và query. "
        f"User có thể hỏi bất kỳ trường nào trong bộ dữ liệu sau: {fields}" 
        "Phân tích câu hỏi và phân loại truy vấn vào các nhóm sau:"
        "1. FUZZY_SEARCH: Áp dụng cho trường 'ten_hang', 'nha_cung_cap' và 'xuat_xu'"
        "2. REGEX: Chỉ áp dụng cho trường 'hs_code'"
        "3. EXACT_MATCH: Áp dụng cho tất cả các trường còn lại"
        "Lưu ý đặc biệt:"
        "- Trường 'tinh_trang' chỉ có thể nhận một trong hai giá trị: 'Nhập' hoặc 'Xuất'"
        "- Trường 'ngay' phải được định dạng theo chuẩn: yyyy-mm-dd (VD: 2023-05-15). Người dùng có thể nhập theo cách khác là dd/mm/yyyy (VD: 15/05/2023)"
        "- Trường 'dieu_kien_giao_hang' chỉ có thể nhận một trong các giá trị: "
        f"{VALID_DIEU_KIEN_GIAO_HANG}"
        "- Trường 'xuat_xu' cần được tìm kiếm fuzzy với mapping quốc gia"
    )
    
    if include_examples:
        template += (
            "\n\nVí dụ câu hỏi và JSON arguments tương ứng:"
            "\nCâu hỏi: 'Tìm tất cả sản phẩm từ Việt Nam nhập khẩu trong tháng 6/2023'"
            "\nArguments: {"
            "\n  'fuzzy_search': {'xuat_xu_keywords': 'Việt Nam'},"
            "\n  'regex_search': {},"
            "\n  'exact_match': {'tinh_trang': 'Nhập', 'ngay': '2023-06'}"
            "\n}"
            "\n\nCâu hỏi: 'Tìm mặt hàng với mã HS bắt đầu bằng 8471'"
            "\nArguments: {"
            "\n  'fuzzy_search': {},"
            "\n  'regex_search': {'hs_code': '^8471'},"
            "\n  'exact_match': {}"
            "\n}"
        )
    
    template += "\nSinh JSON arguments cho function 'generate_search_query'"
    
    return template
