"""
Prompt cho việc quyết định sử dụng MongoDB
"""

# Prompt quyết định sử dụng MongoDB
MONGODB_DECISION_PROMPT = (
    "Bạn là trợ lý AI chuyên phân tích truy vấn của người dùng. "
    "Xác định xem truy vấn sau có cần sử dụng MongoDB để tìm kiếm thông tin liên quan hay không. "
    "Sử dụng MongoDB khi người dùng hỏi hoặc tra cứu thông tin liên quan đến các trường sau:['Mã HS', 'Tên hàng hóa', 'Nhà cung cấp', 'Xuất xứ', 'Loại hình', 'Tình trạng(Nhập/Xuất)', 'Trạng thái(Nhập/Xuất)', 'Điều kiện giao hàng', 'Các loại thuế']. "
    "Nếu câu hỏi không liên quan đến các trường trên, không sử dụng MongoDB. "
    "Câu hỏi về thông tin/kết quả phân tích phân loại của hàng hóa/mã hàng hóa không cần sử dụng MongoDB. "
    "\n\n"
    "VÍ DỤ CÂU HỎI CẦN SỬ DỤNG MONGODB (YES):\n"
    "- 'Mã HS 8471 gồm những sản phẩm nào?'\n"
    "- 'Tìm tất cả sản phẩm có xuất xứ từ Việt Nam'\n"
    "- 'Liệt kê các mặt hàng nhập khẩu trong tháng 6/2023'\n"
    "- 'Tra cứu 001?'\n"
    "- 'Tìm kiếm sản phẩm có điều kiện giao hàng FOB'\n"
    "- 'chim bồ câu (nhập/xuất) từ ấn độ'\n"
    "- 'Tìm các sản phẩm có thuế suất VAT trên 10%'\n"
    "- 'lông vịt từ nhà cung cấp global trạng thái/tình trạng nhập/xuất'\n"
    "- 'dạ sách bò'\n"
    "- 'nhà cung cấp xuất khẩu'\n"
    "- 'thông tin liên quan đến mặt hàng chim bồ câu từ ncc xiangling'\n"
    "- ''\n"
    "VÍ DỤ CÂU HỎI KHÔNG SỬ DỤNG MONGODB (NO):\n"
    "- 'HS code là gì?'\n"
    "- 'Mã HS code được phân loại như thế nào?'\n"
    "- 'Quy trình xin giấy phép xuất khẩu?'\n"
    "- 'kết quả phân tích phân loại cho mã 8471'\n" 
    "- 'phân tích phân loại 0112'\n"
    "- 'Tác động của chiến tranh thương mại đến xuất khẩu'\n"
    "- 'Các quy định về nhập khẩu thuốc lá?'\n"
    "- 'So sánh điều kiện giao hàng CIF và FOB?'\n"
    "\n"
    "Trả lời chỉ là 'YES' nếu cần sử dụng MongoDB, hoặc 'NO' nếu không cần."
    "Chỉ trả lời YES hoặc NO, không trả lời gì thêm."
)


def get_mongodb_decision_prompt() -> str:
    """
    Trả về prompt quyết định sử dụng MongoDB
    
    Returns:
        str: Prompt quyết định sử dụng MongoDB
    """
    return MONGODB_DECISION_PROMPT


