"""
Các hằng số và giá trị cố định cho prompt
"""

# Các trường dữ liệu
FIELDS = [
    'ngay',
    'nha_cung_cap',
    'hs_code',
    'ten_hang',
    'loai_hinh', 
    'don_vi_tinh', 
    'xuat_xu',
    'dieu_kien_giao_hang',
    'thue_suat_xnk', 
    'thue_suat_ttdb',
    'thue_suat_vat', 
    'thue_suat_tu_ve', 
    'thue_suat_bvmt',
    'tinh_trang'
]

# Điều kiện giao hàng hợp lệ
VALID_DIEU_KIEN_GIAO_HANG = [
    "EXW", "FCA", "FAS", "FOB", "CFR", "CIF", 
    "CPT", "CIP", "DAP", "DPU", "DDP", "C&F", "DAT"
]

# Các trạng thái giao dịch
TRANSACTION_STATUSES = ["Nhập", "Xuất"]

# Các trường fuzzy search
FUZZY_SEARCH_FIELDS = ["ten_hang", "nha_cung_cap", "xuat_xu"]

# Các trường regex search
REGEX_SEARCH_FIELDS = ["hs_code"]

# Tất cả các trường khác sử dụng exact match
EXACT_MATCH_FIELDS = [field for field in FIELDS if field not in (FUZZY_SEARCH_FIELDS + REGEX_SEARCH_FIELDS)]



MONGODB_FIELD_MAP = {
    'Ngày': 'ngay',
    'Nhà cung cấp': 'nha_cung_cap',
    'Hs code': 'hs_code',
    'Tên hàng': 'ten_hang',
    'Loại hình': 'loai_hinh',
    'Tên nước xuất xứ': 'xuat_xu',
    'Điều kiện giao hàng': 'dieu_kien_giao_hang',
    'Trạng thái': 'tinh_trang',
    'Tên nước xuất xứ': 'xuat_xu_keywords' 
}

# Field map đảo ngược từ tên trường MongoDB sang tên cột tiếng Việt
RECOMMENDATION_FIELD_MAP = {v: k for k, v in MONGODB_FIELD_MAP.items()}

VALID_LOAI_HINH = [
    # Xuất khẩu
    "B11", "B12", "B13", "E42", "E52", "E54", "E62", "E82",
    "G21", "G22", "G23", "G24", "G61", "C12", "C22", "H21",
    # Nhập khẩu
    "A11", "A12", "A21", "A31", "A41", "A42", "A43", "A44",
    "E11", "E13", "E15", "E21", "E23", "E31", "E33", "E41",
    "G11", "G12", "G13", "G14", "G51", "C11", "C21", "H11"
]