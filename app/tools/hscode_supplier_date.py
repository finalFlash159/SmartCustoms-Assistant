from __future__ import annotations
from typing import Optional, List, Dict
import logging
from langchain.tools import BaseTool
from pydantic import PrivateAttr
from langsmith import traceable

# Import DatabaseConnector từ module utils.db_connector
from utils.db_connector import DatabaseConnector
from .supplier_resolver import SupplierResolver
from ..utils.hscode_formatter import HSCodeFormatter

logger = logging.getLogger(__name__)

formatter = HSCodeFormatter()

class BaseHsCodeSupplierDateTool(BaseTool):
    """
    Lớp cơ sở cho truy vấn theo nhà cung cấp -> HS code -> ngày.
    Chứa các hàm dùng chung: kết nối CSDL, fuzzy matching nhà cung cấp,
    lấy danh sách HS code, lấy data và định dạng kết quả theo Markdown.
    """
    name: str = "BaseHsCodeSupplierDateTool"
    description: str = "Base tool for supplier-first HSCode queries by date"
    is_summary: bool = False
    last_result: Optional[str] = None

    _tool_agent: Optional["ToolAgent"] = PrivateAttr(default=None)
    _db_config: dict = PrivateAttr()
    _db_connector: DatabaseConnector = PrivateAttr()

    def __init__(self, tool_agent: Optional["ToolAgent"] = None, db_config: dict = None):
        super().__init__()
        if db_config is None:
            raise ValueError("db_config must be provided for BaseHsCodeSupplierDateTool")
        self._tool_agent = tool_agent
        self._db_config = db_config
        self._db_connector = DatabaseConnector(db_config)
        self.is_summary = False
        self.last_result = None

    def match_suppliers_fuzzy(self, user_input: str) -> List[str]:
        """
        Gọi SupplierResolver.match_suppliers_fuzzy(user_input).
        """
        resolver = SupplierResolver(self._db_config)
        return resolver.match_suppliers_fuzzy(user_input)

    def get_distinct_hs_for_supplier(self, supplier: str, user_hs: str) -> List[str]:
        """
        Tìm DISTINCT HS code LIKE '%user_hs%' với ràng buộc NhaCungCap = supplier.
        """
        pattern = f"%{user_hs}%"
        query = """
            SELECT DISTINCT HsCode
            FROM import_data
            WHERE NhaCungCap = %s
              AND HsCode LIKE %s
            ORDER BY HsCode
        """
        rows = self._db_connector.execute_query(query, (supplier, pattern))
        return [r['HsCode'] for r in rows if 'HsCode' in r]

    def get_data(self, supplier: str, hs_code: str, date_str: str) -> List[Dict]:
        """
        Lấy toàn bộ record theo: NhaCungCap, HS code và ngày (date_str).
        """
        query = """
            SELECT *
            FROM import_data
            WHERE NhaCungCap = %s
              AND HsCode = %s
              AND DATE(Ngay) = %s
        """
        results = self._db_connector.execute_query(query, (supplier, hs_code, date_str))
        return results

    def get_dates_for_supplier_hs(self, supplier: str, hs_code: str) -> List[str]:
        """
        Lấy danh sách DISTINCT ngày có dữ liệu cho một nhà cung cấp và HS code.
        """
        query = """
            SELECT DISTINCT DATE(Ngay) as Ngay
            FROM import_data
            WHERE NhaCungCap = %s
              AND HsCode = %s
            ORDER BY Ngay
        """
        rows = self._db_connector.execute_query(query, (supplier, hs_code))
        return [str(r['Ngay']) for r in rows if r.get('Ngay') is not None]


class HSCodeSupplierDateTool(BaseHsCodeSupplierDateTool):
    """
    Tool truy vấn theo hướng: nhà cung cấp -> HS code -> ngày.
    Lớp này chỉ giữ lại hàm _run, sử dụng các hàm tiện ích từ lớp cơ sở.
    """
    name: str = "HSCodeSupplierDateTool"
    description: str = (
        "Retrieve HS code information for a specific supplier and date from a MySQL database."
    )

    @traceable(run_type="tool")
    def _run(self, supplier: str, hs_code: str, date_str: str) -> str:
        message_to_agent = "Good job!"
        if self._tool_agent is None:
            logger.error("tool_agent not set in HSCodeSupplierDateTool")
            raise ValueError("tool_agent not set")
        self._tool_agent.tool_called[self.name] = True

        # Kiểm tra gói dịch vụ
        package_type = self._tool_agent.get_package()
        # if package_type in ["trial_package", "vip_package"] and supplier:
        #     self.is_summary = False
        #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
        #     return self.last_result

        try:
            # B1: Fuzzy supplier
            supplier_list = self.match_suppliers_fuzzy(supplier)
            if not supplier_list:
                self.is_summary = False
                self.last_result = f"Không tìm thấy nhà cung cấp khớp với: {supplier}"
                return self.last_result

            if len(supplier_list) > 1:
                lines = []
                lines.append(f"Tìm thấy nhiều nhà cung cấp khớp với '{supplier}':\n")
                for sup in supplier_list:
                    lines.append(f"- {sup}")
                lines.append("\nVui lòng chọn 1 nhà cung cấp chính xác.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

            actual_supplier = supplier_list[0]
            if actual_supplier.upper() != supplier.upper():
                logger.info("Fuzzy matched supplier: %s -> %s", supplier, actual_supplier)

            # B2: Lấy danh sách HS code phù hợp
            matched_hs_codes = self.get_distinct_hs_for_supplier(actual_supplier, hs_code)
            if not matched_hs_codes:
                self.is_summary = False
                self.last_result = (
                    f"Không tìm thấy HS code khớp với {hs_code} từ nhà cung cấp {actual_supplier}.\n"
                    "Vui lòng kiểm tra lại thông tin."
                )
                return self.last_result

            if len(matched_hs_codes) > 1:
                lines = []
                lines.append(f"Tìm thấy nhiều HS code khớp với yêu cầu từ nhà cung cấp {actual_supplier}:\n")
                for code in matched_hs_codes:
                    lines.append(f"- {code}")
                lines.append("\nVui lòng chọn 1 HS code chính xác.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

            actual_hs = matched_hs_codes[0]

            # B3: Lấy data theo nhà cung cấp, HS code và ngày
            results = self.get_data(actual_supplier, actual_hs, date_str)

            if results:
                self.is_summary = True
                extra_info = f"Dưới đây là thông tin liên quan về:\n\n- **HS code**: **{hs_code}**.\n- **Nhà cung cấp**: **{supplier}**.\n- **Ngày**: **{date_str}**.\n\n"
                self.last_result = extra_info + formatter.format_records(results, display_date=False, package_type=package_type)
                return message_to_agent
            else:
                # Không tìm thấy data cho ngày date_str, liệt kê danh sách ngày có dữ liệu
                date_list = self.get_dates_for_supplier_hs(actual_supplier, actual_hs)
                if not date_list:
                    self.is_summary = False
                    self.last_result = f"Không tìm thấy dữ liệu cho nhà cung cấp {actual_supplier} với HS code {actual_hs}."
                    return message_to_agent
                lines = []
                lines.append(
                    f"Không tìm thấy dữ liệu cho nhà cung cấp {actual_supplier}, HS code {actual_hs} vào ngày **{date_str}**.\n"
                )
                lines.append(
                    f"Dưới đây là danh sách các ngày có dữ liệu cho HS code {actual_hs} từ nhà cung cấp {actual_supplier}:"
                )
                for day in date_list:
                    lines.append(f"- {day}")
                lines.append("\nVui lòng chọn 1 ngày hợp lệ và truy vấn lại.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

        except Exception as e:
            logger.error("Error retrieving HS code + supplier + date data: %s", e)
            return f"Error retrieving data: {e}"
