from langchain.tools import BaseTool
from pydantic import PrivateAttr
from langsmith import traceable
from typing import List, Dict, Optional
import logging

# Import DatabaseConnector từ module utils.db_connector
from utils.db_connector import DatabaseConnector
from ..utils.hscode_formatter import HSCodeFormatter

logger = logging.getLogger(__name__)
formatter = HSCodeFormatter()

class BaseHsCodeSupplierDateStatusTool(BaseTool):
    """
    Base tool for retrieving HS code information for a supplier on a specific date and status.
    Chứa các hàm dùng chung: fuzzy matching nhà cung cấp, lấy danh sách HS code, truy vấn dữ liệu,
    và định dạng kết quả trả về dạng Markdown.
    """
    name: str = "BaseHsCodeSupplierDateStatusTool"
    description: str = "Base tool for supplier HSCode queries with date and status"
    is_summary: bool = False
    last_result: Optional[str] = None

    _tool_agent: Optional["ToolAgent"] = PrivateAttr(default=None)
    _db_config: dict = PrivateAttr()
    _db_connector: DatabaseConnector = PrivateAttr()

    def __init__(self, tool_agent: Optional["ToolAgent"] = None, db_config: dict = None):
        super().__init__()
        if db_config is None:
            raise ValueError("db_config must be provided for BaseHsCodeSupplierDateStatusTool")
        self._tool_agent = tool_agent
        self._db_config = db_config
        self._db_connector = DatabaseConnector(db_config)
        self.is_summary = False
        self.last_result = None

    def match_suppliers_fuzzy(self, user_input: str) -> List[str]:
        from .supplier_resolver import SupplierResolver
        resolver = SupplierResolver(self._db_config)
        return resolver.match_suppliers_fuzzy(user_input)

    def get_distinct_hs_for_supplier(self, supplier: str, user_hs: str, status: str) -> List[str]:
        pattern = f"%{user_hs}%"
        query = """
            SELECT DISTINCT HsCode
            FROM import_data
            WHERE NhaCungCap = %s AND HsCode LIKE %s AND TinhTrang = %s
            ORDER BY HsCode
        """
        rows = self._db_connector.execute_query(query, (supplier, pattern, status))
        return [r['HsCode'] for r in rows if 'HsCode' in r]

    def get_data(self, supplier: str, hs_code: str, date_str: str, status: str) -> List[Dict]:
        query = """
            SELECT *
            FROM import_data
            WHERE NhaCungCap = %s AND HsCode = %s AND DATE(Ngay) = %s AND TinhTrang = %s
        """
        results = self._db_connector.execute_query(query, (supplier, hs_code, date_str, status))
        return results


class HSCodeSupplierDateStatusTool(BaseHsCodeSupplierDateStatusTool):
    """
    Tool truy vấn thông tin HS code cho nhà cung cấp trên một ngày cụ thể với tình trạng cụ thể.
    Lớp này chỉ triển khai hàm _run, sử dụng các hàm tiện ích từ lớp cơ sở.
    """
    name: str = "HSCodeSupplierDateStatusTool"
    description: str = "Retrieve HS code information for a supplier on a specific date and status from a MySQL database"

    @traceable(run_type="tool")
    def _run(self, supplier: str, hs_code: str, date_str: str, status: str) -> str:
        message_to_agent = "Good job!"
        if self._tool_agent is None:
            logger.error("tool_agent not set in HSCodeSupplierDateStatusTool")
            raise ValueError("tool_agent not set")
        self._tool_agent.tool_called[self.name] = True

        # Kiểm tra gói dịch vụ
        package_type = self._tool_agent.get_package()
        # if package_type in ["trial_package", "vip_package"] and supplier:
        #     self.is_summary = True
        #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
        #     return self.last_result

        logger.info("HSCodeSupplierDateStatusTool _run called with supplier=%s, hs_code=%s, date=%s, status=%s",
                    supplier, hs_code, date_str, status)
        try:
            # B1: Fuzzy matching nhà cung cấp
            supplier_list = self.match_suppliers_fuzzy(supplier)
            if not supplier_list:
                self.is_summary = False
                self.last_result = f"Không tìm thấy nhà cung cấp khớp với: {supplier}"
                return self.last_result
            if len(supplier_list) > 1:
                lines = [f"Tìm thấy nhiều nhà cung cấp khớp với tên '{supplier}':\n"]
                for sup in supplier_list:
                    lines.append(f"- {sup}")
                lines.append("\nVui lòng chọn 1 nhà cung cấp chính xác.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

            actual_supplier = supplier_list[0]

            # B2: Lấy danh sách HS code phù hợp với yêu cầu và tình trạng
            matched_hs_codes = self.get_distinct_hs_for_supplier(actual_supplier, hs_code, status)
            if not matched_hs_codes:
                self.is_summary = False
                self.last_result = (
                    f"Không tìm thấy HS code khớp với {hs_code} từ nhà cung cấp {actual_supplier} với tình trạng {status}."
                )
                return self.last_result
            if len(matched_hs_codes) > 1:
                lines = [f"Tìm thấy nhiều HS code khớp với yêu cầu từ nhà cung cấp {actual_supplier}:\n"]
                for c in matched_hs_codes:
                    lines.append(f"- {c}")
                lines.append("\nVui lòng chọn 1 HS code chính xác.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

            actual_hs = matched_hs_codes[0]

            # B3: Truy vấn dữ liệu theo nhà cung cấp, HS code, ngày và tình trạng
            results = self.get_data(actual_supplier, actual_hs, date_str, status)
            if results:
                self.is_summary = True
                extra_info = f"Dưới đây là thông tin liên quan về:\n\n- **HS code**: **{hs_code}**.\n- **Nhà cung cấp**: **{supplier}**.\n- **Ngày**: **{date_str}**\n- **Trạng thái**: **{status}** "
                self.last_result = extra_info + "\n---\n" + formatter.format_records(results, display_date=False, package_type=package_type)
                return message_to_agent
            else:
                self.is_summary = False
                self.last_result = (
                    f"Không tìm thấy dữ liệu cho nhà cung cấp {actual_supplier}, HS code {actual_hs}, "
                    f"ngày {date_str}, tình trạng {status}."
                )
                return self.last_result

        except Exception as e:
            logger.error("Error retrieving data: %s", e)
            return f"Error retrieving data: {e}"
