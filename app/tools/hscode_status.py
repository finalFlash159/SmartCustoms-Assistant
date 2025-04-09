from langchain.tools import BaseTool
from pydantic import PrivateAttr
from langsmith import traceable
from typing import List, Dict, Optional
import logging
from collections import defaultdict

# Import DatabaseConnector từ module utils.db_connector
from utils.db_connector import DatabaseConnector
from ..utils.hscode_formatter import HSCodeFormatter

logger = logging.getLogger(__name__)
formatter = HSCodeFormatter()

class BaseHsCodeStatusTool(BaseTool):
    """
    Base tool for retrieving HS code information with status (Nhập/Xuất) from a MySQL database.
    Chứa các hàm dùng chung như:
      - Truy vấn danh sách HS code (LIKE) theo tình trạng.
      - Đếm số bản ghi.
      - Lấy dữ liệu chi tiết theo HS code và tình trạng.
      - Lấy danh sách ngày và nhà cung cấp (nếu quá nhiều bản ghi).
      - Định dạng kết quả trả về dạng Markdown.
    """
    name: str = "BaseHsCodeStatusTool"
    description: str = "Base tool for HS code queries with status"
    is_summary: bool = False
    last_result: Optional[str] = None

    _tool_agent: Optional["ToolAgent"] = PrivateAttr(default=None)
    _db_config: dict = PrivateAttr()
    _db_connector: DatabaseConnector = PrivateAttr()

    def __init__(self, tool_agent: Optional["ToolAgent"] = None, db_config: dict = None):
        super().__init__()
        if db_config is None:
            raise ValueError("db_config must be provided for BaseHsCodeStatusTool")
        self._tool_agent = tool_agent
        self._db_config = db_config
        self._db_connector = DatabaseConnector(db_config)
        self.is_summary = False
        self.last_result = None


    def get_distinct_hs_like(self, user_hs: str, status: str) -> List[str]:
        pattern = f"%{user_hs}%"
        query = "SELECT DISTINCT HsCode FROM import_data WHERE HsCode LIKE %s AND TinhTrang = %s ORDER BY HsCode"
        rows = self._db_connector.execute_query(query, (pattern, status))
        return [r['HsCode'] for r in rows if 'HsCode' in r]

    def get_record_count(self, hs_code: str, status: str) -> int:
        query = "SELECT COUNT(*) as count FROM import_data WHERE HsCode = %s AND TinhTrang = %s"
        rows = self._db_connector.execute_query(query, (hs_code, status))
        if rows and "count" in rows[0]:
            return rows[0]["count"]
        return 0

    def get_data_by_hs_status(self, hs_code: str, status: str) -> List[Dict]:
        query = "SELECT * FROM import_data WHERE HsCode = %s AND TinhTrang = %s ORDER BY Ngay"
        return self._db_connector.execute_query(query, (hs_code, status))

    def get_dates_suppliers_by_hs_status(self, hs_code: str, status: str) -> List[Dict]:
        query = """
            SELECT DISTINCT DATE(Ngay) as Ngay, NhaCungCap
            FROM import_data
            WHERE HsCode = %s AND TinhTrang = %s
            ORDER BY Ngay
        """
        return self._db_connector.execute_query(query, (hs_code, status))


class HSCodeStatusTool(BaseHsCodeStatusTool):
    """
    Tool truy vấn thông tin HS code với tình trạng (Nhập/Xuất) từ cơ sở dữ liệu MySQL.
    Lớp này chỉ triển khai hàm _run, sử dụng các hàm tiện ích từ lớp cơ sở.
    """
    name: str = "HSCodeStatusTool"
    description: str = "Retrieve HS code information with status (Nhập/Xuất) from a MySQL database"

    @traceable(run_type="tool")
    def _run(self, hs_code: str, status: str) -> str:
        message_to_agent = "Good job!"
        if self._tool_agent is None:
            logger.error("tool_agent not set in HSCodeStatusTool")
            raise ValueError("tool_agent not set")
        self._tool_agent.tool_called[self.name] = True
        
        logger.info("HSCodeStatusTool _run called with hs_code: %s, status: %s", hs_code, status)
        try:
            # B1: Lấy danh sách HS code phù hợp với yêu cầu (LIKE) và tình trạng
            matched_hs_codes = self.get_distinct_hs_like(hs_code, status)
            if not matched_hs_codes:
                self.is_summary = False
                self.last_result = f"Không tìm thấy HS code nào khớp với: '**{hs_code}**' và tình trạng '**{status}**'."
                return self.last_result
            
            if len(matched_hs_codes) > 1:
                lines = ["Tìm thấy nhiều HS code khớp với yêu cầu:\n"]
                for c in matched_hs_codes:
                    lines.append(f"- {c}")
                lines.append("\nVui lòng chọn 1 HS code chính xác.\n")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return self.last_result
            
            # Kiểm tra gói dịch vụ
            package_type = self._tool_agent.get_package()
            # if package_type in ["trial_package", "vip_package"]:
            #     self.is_summary = True
            #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin chi tiết."
            #     return self.last_result

            actual_hs = matched_hs_codes[0]
            count = self.get_record_count(actual_hs, status)
            # if count <= 20:
            data_list = self.get_data_by_hs_status(actual_hs, status)
            if data_list:
                self.is_summary = True
                extra_info = f"Dưới đây là thông tin về mã HS code {actual_hs} với tình trạng {status}:\n\n"
                self.last_result = extra_info + formatter.format_records(data_list, display_date=True, package_type=package_type)
                return message_to_agent
            else:
                self.is_summary = False
                self.last_result = f"Không tìm thấy dữ liệu cho mã HS: {actual_hs} với tình trạng: {status}"
                return self.last_result
            # else:
            #     # Nếu có quá nhiều bản ghi, liệt kê danh sách ngày và nhà cung cấp liên quan
            #     rows = self.get_dates_suppliers_by_hs_status(actual_hs, status)
            #     date_to_suppliers = defaultdict(set)
            #     for row in rows:
            #         if row.get('Ngay') is not None:
            #             day_str = str(row['Ngay'])
            #             date_to_suppliers[day_str].add( self.clean_str_field(row.get("NhaCungCap"), "nhà cung cấp"))
            #     lines = [f"Tìm thấy {count} bản ghi cho HS code {actual_hs} với tình trạng {status}."]
            #     lines.append("Dưới đây là các ngày và nhà cung cấp liên quan:\n")
            #     for day, suppliers in sorted(date_to_suppliers.items()):
            #         lines.append(f"**Ngày {day}:**")
            #         for sup in sorted(suppliers):
            #             lines.append(f"- {sup}")
            #         lines.append("")
            #     lines.append("Vui lòng chọn một ngày hoặc nhà cung cấp để xem chi tiết.")
            #     self.is_summary = True
            #     self.last_result = "\n".join(lines)
            #     return message_to_agent

        except Exception as e:
            logger.error("Error retrieving HS code data: %s", e)
            return f"Error retrieving HS code data: {e}"
