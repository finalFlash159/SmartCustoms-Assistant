from __future__ import annotations
from typing import Optional, List, Dict
import logging
from langchain.tools import BaseTool
from pydantic import PrivateAttr
from langsmith import traceable
from collections import defaultdict
import pandas as pd

from ..utils.hscode_formatter import HSCodeFormatter
from utils.db_connector import DatabaseConnector

logger = logging.getLogger(__name__)

formatter = HSCodeFormatter()

# --- Lớp cơ sở chứa các hàm dùng chung ---
class BaseHSCodeTool(BaseTool):
    name: str = "BaseHSCodeTool"
    description: str = "Base tool for HSCode operations"
    is_summary: bool = False
    last_result: Optional[str] = None
    _tool_agent: Optional["ToolAgent"] = PrivateAttr(default=None)
    _db_config: dict = PrivateAttr()
    _db_connector: DatabaseConnector = PrivateAttr()

    def __init__(self, tool_agent: Optional["ToolAgent"] = None, db_config: dict = None):
        super().__init__()
        if db_config is None:
            raise ValueError("db_config must be provided for HSCodeTool")
        self._tool_agent = tool_agent
        self._db_config = db_config
        # Sử dụng tiện ích DatabaseConnector thay vì gọi mysql.connector.connect trực tiếp
        self._db_connector = DatabaseConnector(db_config)
        self.is_summary = False
        self.last_result = None

    def clean_str_field(self, value: Optional[str], field_name: str) -> str:
        if value is None or str(value).strip() == "nan":
            return f"Không có thông tin về {field_name}"
        return str(value).strip()

    def get_distinct_hs_like(self, user_hs: str) -> List[str]:
        """
        Lấy danh sách DISTINCT HsCode khớp với user_hs theo kiểu LIKE '%user_hs%'.
        """
        pattern = f"%{user_hs}%"
        query = "SELECT DISTINCT HsCode FROM import_data WHERE HsCode LIKE %s ORDER BY HsCode"
        results = self._db_connector.execute_query(query, (pattern,))
        # row['HsCode'] nếu kết quả là dictionary
        return [record['HsCode'] for record in results if 'HsCode' in record]


# --- Lớp chính kế thừa từ BaseHSCodeTool ---
class HSCodeTool(BaseHSCodeTool):
    name: str = "HSCodeTool"
    description: str = "Retrieve HS code information from a MySQL database"

    @traceable(run_type="tool")
    def _run(self, hs_code: str) -> str:
        """
        Logic:
          1) Dùng LIKE '%hs_code%' lấy danh sách DISTINCT HsCode.
          2) Nếu len>1 => liệt kê => user chọn 1
          3) Nếu len=1 => actual_hs => logic cũ:
             - nếu <10 => in toàn bộ
             - nếu >=10 => nhóm theo ngày
        """
        message_to_agent = "Good job!"
        if self._tool_agent is None:
            logger.error("tool_agent not set in HSCodeTool")
            raise ValueError("tool_agent not set")

        self._tool_agent.tool_called[self.name] = True
        logger.info("HSCodeTool _run method called with hs_code: %s", hs_code)

        try:
            # B1) Tìm DS HsCode theo LIKE
            matched_hs_codes = self.get_distinct_hs_like(hs_code)
            if not matched_hs_codes:
                self.is_summary = False
                self.last_result = f"Không tìm thấy HS code nào khớp với: '**{hs_code}**'."
                return self.last_result

            if len(matched_hs_codes) > 1:
                # Liệt kê => user chọn
                lines = []
                lines.append("Tìm thấy nhiều HS code khớp với yêu cầu:\n")
                for c in matched_hs_codes:
                    lines.append(f"- {c}")
                lines.append("\n")    
                lines.append("Vui lòng chọn 1 HS code chính xác.\n")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return self.last_result

            # => len=1
            actual_hs = matched_hs_codes[0]
            logger.info("Only one HS code matched: %s", actual_hs)

            # B2) Lấy các dòng (Ngày, NhàCungCap) để nhóm
            summary_query = "SELECT Ngay, NhaCungCap FROM import_data WHERE HsCode = %s"
            summary_results = self._db_connector.execute_query(summary_query, (actual_hs,))
            count = len(summary_results)

            package_type = self._tool_agent.get_package()

            # if package_type in ["trial_package", "vip_package"] and supplier:
            #     self.is_summary = True
            #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp. "
            #     return self.last_result

            if count <= 20:
                # Nếu dưới 35 dòng => in toàn bộ
                query = "SELECT * FROM import_data WHERE HsCode = %s"
                results = self._db_connector.execute_query(query, (actual_hs,))
                if results:
                    extra_info = f"Dưới đây là thông tin liên quan đến HS code **{actual_hs}**:"    
                    self.is_summary = True
                    self.last_result = extra_info + "\n\n" + formatter.format_records(results, display_date=True, package_type=package_type)
                    return message_to_agent
                else:
                    self.is_summary = False
                    self.last_result = f"No data found for HS code: {actual_hs}"
                    return self.last_result
            else:
                date_to_suppliers = defaultdict(set)
                for row in summary_results:
                    ngay = row.get("Ngay")
                    supplier = self.clean_str_field(row.get("NhaCungCap"), "nhà cung cấp")
                    if ngay and supplier:
                        date_to_suppliers[ngay].add(supplier)

                lines = []
                lines.append(f"**Tôi tìm thấy {count} bản ghi cho mã HS {actual_hs}.**\n")
                lines.append("Dưới đây là danh sách nhà cung cấp theo từng ngày:\n")

                sorted_dates = sorted(date_to_suppliers.keys())
                for d in sorted_dates:
                    lines.append(f"Ngày {d}:")
                    sorted_suppliers = sorted(date_to_suppliers[d])
                    for sup in sorted_suppliers:
                        lines.append(f"- {sup}")
                    lines.append("")

                lines.append(
                    "Xin vui lòng chỉ định bạn muốn xem thông tin chi tiết về ngày nào hoặc nhà cung cấp nào.  \n"
                    "Nhập theo mẫu: **mã HS '...', nhà cung cấp '...'** hoặc  **mã HS '...', ngày 'YYYY-MM-DD'**. \n"
                )

                message = "\n".join(lines)
                self.is_summary = True
                self.last_result = message
                return message_to_agent

        except Exception as e:
            logger.error("Error retrieving HS code data: %s", e)
            return f"Error retrieving HS code data: {e}"


class HSCodeDateTool(BaseHSCodeTool):
    name: str = "HSCodeDateTool"
    description: str = "Retrieve HS code information for a specific date from a MySQL database"

    @traceable(run_type="tool")
    def _run(self, hs_code: str, date: str) -> str:
        """
        Logic:
          1) Kiểm tra mã HS code và ngày hợp lệ.
          2) Truy vấn dữ liệu từ database với HS code và ngày cụ thể.
          3) Định dạng và trả về kết quả.
        """
        if self._tool_agent is None:
            logger.error("tool_agent not set in HSCodeDateTool")
            raise ValueError("tool_agent not set")

        self._tool_agent.tool_called[self.name] = True
        logger.info("HSCodeDateTool _run method called with hs_code: %s, date: %s", hs_code, date)

        try:
            # Kiểm tra mã HS code có tồn tại không
            matched_hs_codes = self.get_distinct_hs_like(hs_code)
            if not matched_hs_codes:
                self.is_summary = False
                self.last_result = f"Không tìm thấy HS code nào khớp với: '**{hs_code}**'."
                return self.last_result

            if len(matched_hs_codes) > 1:
                lines = ["Tìm thấy nhiều HS code khớp với yêu cầu:\n"]
                for c in matched_hs_codes:
                    lines.append(f"- {c}")
                lines.append("\nVui lòng chọn 1 HS code chính xác.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return self.last_result

            package_type = self._tool_agent.get_package()
            # print(package_type)
            # if package_type in ["trial_package", "vip_package"]:
            #     self.is_summary = False
            #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
            #     return self.last_result

            actual_hs = matched_hs_codes[0]
            logger.info("Processing HS code: %s for date: %s", actual_hs, date)

            # Truy vấn dữ liệu với HS code và ngày cụ thể
            query = """
                SELECT * FROM import_data 
                WHERE HsCode = %s AND Ngay = %s
            """
            results = self._db_connector.execute_query(query, (actual_hs, date))

            if not results:
                self.is_summary = False
                self.last_result = f"Không tìm thấy dữ liệu cho mã HS '{actual_hs}' vào ngày '{date}'."
                return self.last_result

            # Định dạng và trả về kết quả
            extra_info = f"Dưới đây là thông tin liên quan đến HS code **{actual_hs}** vào ngày **{date}**:"    
            self.is_summary = True
            self.last_result = extra_info + "\n\n" + formatter.format_records(results, display_date=False, package_type=package_type)
            return "Good job!"

        except Exception as e:
            logger.error("Error retrieving HS code data for date: %s", e)
            return f"Error retrieving HS code data for date: {e}"


class HSCodeDateRangeTool(BaseHSCodeTool):
    name: str = "HSCodeDateRangeTool"
    description: str = "Retrieve HS code information for a date range from a MySQL database"

    @traceable(run_type="tool")
    def _run(self, hs_code: str, start_date: str, end_date: str) -> str:
        if self._tool_agent is None:
            logger.error("tool_agent not set in HSCodeDateRangeTool")
            raise ValueError("tool_agent not set")

        self._tool_agent.tool_called[self.name] = True
        logger.info("HSCodeDateRangeTool _run method called with hs_code: %s, start_date: %s, end_date: %s", 
                    hs_code, start_date, end_date)

        try:
            matched_hs_codes = self.get_distinct_hs_like(hs_code)
            if not matched_hs_codes:
                self.is_summary = False
                self.last_result = f"Không tìm thấy HS code nào khớp với: '**{hs_code}**'."
                return self.last_result

            if len(matched_hs_codes) > 1:
                lines = ["Tìm thấy nhiều HS code khớp với yêu cầu:\n"]
                for c in matched_hs_codes:
                    lines.append(f"- {c}")
                lines.append("\nVui lòng chọn 1 HS code chính xác.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return self.last_result


            package_type = self._tool_agent.get_package()
            # print(package_type)
            # if package_type in ["trial_package", "vip_package"]:
            #     self.is_summary = False
            #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
            #     return self.last_result
                
            actual_hs = matched_hs_codes[0]
            logger.info("Processing HS code: %s for date range: %s to %s", actual_hs, start_date, end_date)

            query = """
                SELECT * FROM import_data 
                WHERE HsCode = %s AND Ngay BETWEEN %s AND %s
                ORDER BY Ngay
            """
            results = self._db_connector.execute_query(query, (actual_hs, start_date, end_date))

            if not results:
                self.is_summary = False
                self.last_result = f"Không tìm thấy dữ liệu cho mã HS '{actual_hs}' trong khoảng từ '{start_date}' đến '{end_date}'."
                return self.last_result

            # Thêm extra_info
            extra_info = f"Dưới đây là thông tin liên quan đến HS code **{actual_hs}** từ ngày **{start_date}** đến ngày **{end_date}**:"

            if len(results) <= 20:
                # Trường hợp chi tiết
                self.is_summary = True
                self.last_result = extra_info + "\n\n" + formatter.format_records(results, display_date=True, package_type=package_type)
                return "Good job!"
            else:
                # Trường hợp tóm tắt
                date_to_suppliers = defaultdict(set)
                for row in results:
                    ngay = row.get("Ngay")
                    supplier = row.get("NhaCungCap")
                    if ngay and supplier:
                        date_to_suppliers[ngay].add(supplier)

                lines = [extra_info + "\n"]
                lines.append(f"**Tìm thấy {len(results)} bản ghi cho mã HS {actual_hs} từ {start_date} đến {end_date}.**\n")
                lines.append("Dưới đây là tóm tắt nhà cung cấp theo ngày:\n")

                sorted_dates = sorted(date_to_suppliers.keys())
                for d in sorted_dates:
                    lines.append(f"Ngày {d}:")
                    sorted_suppliers = sorted(date_to_suppliers[d])
                    for sup in sorted_suppliers:
                        lines.append(f"- {sup}")
                    lines.append("")

                lines.append(
                    "Vui lòng chỉ định ngày cụ thể để xem chi tiết bằng cách sử dụng mã HS code và ngày 'YYYY-MM-DD'.\n"
                    "Hoặc cũng có thể chọn khoảng ngày ngắn hơn hoặc kết hợp với thông tin Nhà cung cấp để xem chi tiết.\n"
                )

                self.is_summary = True
                self.last_result = "\n".join(lines)
                return "Good job!"

        except Exception as e:
            logger.error("Error retrieving HS code data for date range: %s", e)
            return f"Error retrieving HS code data for date range: {e}"