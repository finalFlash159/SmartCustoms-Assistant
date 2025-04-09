from __future__ import annotations
from typing import Optional, List, Dict
import logging
from langchain.tools import BaseTool
from pydantic import PrivateAttr
from langsmith import traceable
from collections import defaultdict
import pandas as pd
from ..utils.hscode_formatter import HSCodeFormatter

# Import DatabaseConnector từ module utils.db_connector
from utils.db_connector import DatabaseConnector

logger = logging.getLogger(__name__)

formatter = HSCodeFormatter()

# --- Lớp BaseHsCodeSupplierStatusTool chứa các hàm dùng chung ---
class BaseHsCodeSupplierStatusTool(BaseTool):
    """
    BaseHsCodeSupplierStatusTool chứa các hàm dùng chung cho truy vấn HS code theo hướng supplier-first với tình trạng (status).
    Bao gồm:
      - Kết nối DB qua DatabaseConnector.
      - Fuzzy matching supplier.
      - Lấy DISTINCT HS code với ràng buộc NhaCungCap, HS code (LIKE) và Tình trạng.
      - Lấy dữ liệu chi tiết theo HS code, nhà cung cấp và tình trạng.
      - Định dạng kết quả dạng Markdown.
    """
    name: str = "BaseHsCodeSupplierStatusTool"
    description: str = "Base tool for supplier-first HSCode operations with status filter"
    is_summary: bool = False
    last_result: Optional[str] = None

    _tool_agent: Optional["ToolAgent"] = PrivateAttr(default=None)
    _db_config: dict = PrivateAttr()
    _db_connector: DatabaseConnector = PrivateAttr()

    def __init__(self, tool_agent: Optional["ToolAgent"] = None, db_config: dict = None):
        super().__init__()
        if db_config is None:
            raise ValueError("db_config must be provided for BaseHsCodeSupplierStatusTool")
        self._tool_agent = tool_agent
        self._db_config = db_config
        self._db_connector = DatabaseConnector(db_config)
        self.is_summary = False
        self.last_result = None

    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Thực thi truy vấn bằng cách sử dụng DatabaseConnector."""
        return self._db_connector.execute_query(query, params)

    def match_suppliers_fuzzy(self, user_input: str) -> List[str]:
        """
        Gọi SupplierResolver.match_suppliers_fuzzy(user_input).

        """
        from .supplier_resolver import SupplierResolver
        resolver = SupplierResolver(self._db_config)
        return resolver.match_suppliers_fuzzy(user_input)

    def get_distinct_hs_for_supplier(self, supplier: str, user_hs: str, status: str) -> List[str]:
        """
        Tìm DISTINCT HsCode LIKE '%user_hs%' với ràng buộc NhaCungCap = supplier và Tình trạng = status.
        """
        pattern = f"%{user_hs}%"
        query = """
            SELECT DISTINCT HsCode
            FROM import_data
            WHERE NhaCungCap = %s AND HsCode LIKE %s AND TinhTrang = %s
            ORDER BY HsCode
        """
        results = self.execute(query, (supplier, pattern, status))
        return [r['HsCode'] for r in results if 'HsCode' in r]

    def get_data_by_hs_and_supplier(self, hs_code: str, supplier: str, status: str) -> List[Dict]:
        """
        Lấy dữ liệu cho HsCode = hs_code, NhaCungCap = supplier và TinhTrang = status.
        """
        query = """
            SELECT *
            FROM import_data
            WHERE HsCode = %s AND NhaCungCap = %s AND TinhTrang = %s
            ORDER BY Ngay
        """
        return self.execute(query, (hs_code, supplier, status))

    def query_suppliers_and_dates(self, supplier_list: List[str]) -> str:
        """
        Liệt kê các nhà cung cấp và danh sách ngày (distinct) của họ.
        """
        lines = []
        for sup in supplier_list:
            query = "SELECT DISTINCT Ngay FROM import_data WHERE NhaCungCap = %s ORDER BY Ngay"
            rows = self.execute(query, (sup,))
            lines.append(f"Nhà cung cấp: {sup}")
            for r in rows:
                day_str = r['Ngay'].strftime("%Y-%m-%d") if r['Ngay'] else "N/A"
                lines.append(f"  - Ngày {day_str}")
            lines.append("")
        return "\n".join(lines)



class HSCodeSupplierStatusTool(BaseHsCodeSupplierStatusTool):
    """
    Tool truy vấn HS code theo hướng: supplier -> hs_code -> tình trạng -> in data.
    Lớp này chỉ triển khai hàm _run, các hàm trợ giúp được kế thừa từ BaseHsCodeSupplierStatusTool.
    """
    name: str = "HSCodeSupplierStatusTool"
    description: str = "Retrieve HS code information for a specific supplier and status from a MySQL database"

    @traceable(run_type="tool")
    def _run(self, supplier: str, hs_code: str, status: str) -> str:
        """
        1) Fuzzy supplier: nếu kết quả > 1 thì yêu cầu người dùng chọn.
        2) Nếu chỉ có 1: sử dụng actual_supplier để lấy DISTINCT HS code theo supplier, hs_code và status.
        3) Nếu chỉ có 1 HS code: lấy dữ liệu chi tiết.  
           Nếu dữ liệu quá nhiều, liệt kê danh sách ngày để người dùng chọn.
        """
        message_to_agent = "Good job!"
        if self._tool_agent is None:
            logger.error("tool_agent not set in HSCodeSupplierStatusTool")
            raise ValueError("tool_agent not set")
        self._tool_agent.tool_called[self.name] = True
        logger.info("HSCodeSupplierStatusTool _run called with supplier=%s, hs_code=%s, status=%s", supplier, hs_code, status)

        # Kiểm tra gói dịch vụ
        package_type = self._tool_agent.get_package()
        # if package_type in ["trial_package", "vip_package"] and supplier:
        #     self.is_summary = True
        #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
        #     return self.last_result

        try:
            # B1) Fuzzy supplier
            supplier_list = self.match_suppliers_fuzzy(supplier)
            if not supplier_list:
                self.is_summary = False
                self.last_result = f"Không tìm thấy nhà cung cấp khớp với '**{supplier}**'."
                return self.last_result
            if len(supplier_list) > 1:
                lines = [f"Tìm thấy nhiều nhà cung cấp khớp với tên **'{supplier}'**:\n"]
                for sup in supplier_list:
                    lines.append(f"- {sup}")
                lines.append("\nVui lòng chọn 1 nhà cung cấp chính xác.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

            # => Nếu chỉ có 1 nhà cung cấp
            actual_supplier = supplier_list[0]

            # B2) Lấy DISTINCT HS code theo supplier, hs_code và status
            matched_hs_codes = self.get_distinct_hs_for_supplier(actual_supplier, hs_code, status)
            if not matched_hs_codes:
                self.is_summary = False
                self.last_result = (
                    f"Không tìm thấy HS code khớp với **'{hs_code}'** từ nhà cung cấp: **{actual_supplier}** với tình trạng **{status}**."
                )
                return self.last_result
            if len(matched_hs_codes) > 1:
                lines = [f"Tìm thấy nhiều HS code khớp với mã **'{hs_code}'** từ Nhà cung cấp **{actual_supplier}**:\n"]
                for c in matched_hs_codes:
                    lines.append(f"- {c}")
                lines.append("\nVui lòng chọn 1 HS code chính xác.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

            # => Nếu chỉ có 1 HS code
            actual_hs = matched_hs_codes[0]

            # B3) Lấy dữ liệu theo HS code, supplier và status
            results = self.get_data_by_hs_and_supplier(actual_hs, actual_supplier, status)
            if not results:
                lines = []
                lines.append(
                    f"Không tìm thấy dữ liệu từ nhà cung cấp **{actual_supplier}** với HS code **{actual_hs}** và tình trạng **{status}**."
                )
                lines.append("Dưới đây là danh sách ngày của nhà cung cấp này (nếu có):\n")
                lines.append(self.query_suppliers_and_dates([actual_supplier]))
                lines.append("Vui lòng kiểm tra lại tên nhà cung cấp hoặc HS code.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

            if len(results) <= 20:
                extra_info =  f"Dưới đây là thông tin về:\n- **HS code**: **{hs_code}**- **Nhà cung cấp**: **{supplier}**\n- **Trạng thái**: **{status}**\n\n"
                self.is_summary = True
                self.last_result = extra_info + formatter.format_records(results, display_date=True, package_type=package_type)
            else:
                query = """
                    SELECT DISTINCT Ngay
                    FROM import_data
                    WHERE HsCode = %s AND NhaCungCap = %s AND TinhTrang = %s
                    ORDER BY Ngay
                """
                rows = self.execute(query, (actual_hs, actual_supplier, status))
                lines = [f"Tìm thấy {len(results)} bản ghi cho HS code {actual_hs}, nhà cung cấp {actual_supplier}, tình trạng {status}."]
                lines.append("Dưới đây là các ngày liên quan:\n")
                for row in rows:
                    if row['Ngay'] is not None:
                        day_str = str(row['Ngay'])
                        lines.append(f"- {day_str}")
                lines.append("\nVui lòng chọn một ngày hoặc khoảng ngày để hiển thị chi tiết.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

        except Exception as e:
            logger.error("Error retrieving HS code data: %s", e)
            return f"Error retrieving HS code data: {e}"
