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

# --- Lớp BaseHsCodeSupplierTool chứa các hàm dùng chung ---
class BaseHsCodeSupplierTool(BaseTool):
    """
    BaseHsCodeSupplierTool chứa các hàm dùng chung cho truy vấn HSCode theo hướng supplier-first.
    Bao gồm:
      - Kết nối DB qua DatabaseConnector
      - Fuzzy matching supplier
      - Lấy DISTINCT HS code theo supplier
      - Lấy dữ liệu chi tiết theo HS code và supplier
      - Định dạng kết quả dạng Markdown và liệt kê ngày
    """
    name: str = "BaseHsCodeSupplierTool"
    description: str = "Base tool for supplier-first HSCode operations"
    is_summary: bool = False
    last_result: Optional[str] = None

    _tool_agent: Optional["ToolAgent"] = PrivateAttr(default=None)
    _db_config: dict = PrivateAttr()
    _db_connector: DatabaseConnector = PrivateAttr()

    def __init__(self, tool_agent: Optional["ToolAgent"] = None, db_config: dict = None):
        super().__init__()
        if db_config is None:
            raise ValueError("db_config must be provided for BaseHsCodeSupplierTool")
        self._tool_agent = tool_agent
        self._db_config = db_config
        self._db_connector = DatabaseConnector(db_config)
        self.is_summary = False
        self.last_result = None

    def clean_str_field(self, value: Optional[str], field_name: str) -> str:
        if value is None or str(value).strip() == "nan":
            return f"Không có thông tin về {field_name}"
        return str(value).strip()

    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Thực thi truy vấn bằng DatabaseConnector."""
        return self._db_connector.execute_query(query, params)

    def match_suppliers_fuzzy(self, user_input: str) -> List[str]:
        """
        Gọi SupplierResolver.match_suppliers_fuzzy(user_input).
        (Giả sử SupplierResolver được định nghĩa trong module supplier_resolver)
        """
        from .supplier_resolver import SupplierResolver
        resolver = SupplierResolver(self._db_config)
        return resolver.match_suppliers_fuzzy(user_input)

    def get_distinct_hs_for_supplier(self, supplier: str, user_hs: str) -> List[str]:
        """
        Tìm DISTINCT HsCode LIKE '%user_hs%' với ràng buộc NhaCungCap = supplier.
        """
        pattern = f"%{user_hs}%"
        query = """
            SELECT DISTINCT HsCode
            FROM import_data
            WHERE NhaCungCap = %s
              AND HsCode LIKE %s
            ORDER BY HsCode
        """
        results = self.execute(query, (supplier, pattern))
        return [r['HsCode'] for r in results if 'HsCode' in r]

    def get_data_by_hs_and_supplier(self, hs_code: str, supplier: str) -> List[Dict]:
        """
        Lấy dữ liệu cho HsCode = hs_code và NhaCungCap = supplier.
        """
        query = """
            SELECT *
            FROM import_data
            WHERE HsCode = %s
              AND NhaCungCap = %s
            ORDER BY Ngay
        """
        return self.execute(query, (hs_code, supplier))

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

    def format_hs_code_info(self, hs_code: str, supplier: str, data_list: List[Dict]) -> str:
        """
        Định dạng dữ liệu (theo supplier và hs_code) thành Markdown.
        """
        filtered_data = [
            r for r in data_list
            if r['HsCode'] == hs_code and r['NhaCungCap'] == supplier
        ]
        if not filtered_data:
            return f"Không tìm thấy dữ liệu cho HS code={hs_code}, supplier={supplier}."
        
        filtered_data = [record for record in filtered_data if record['Ngay'] is not None]
        filtered_data.sort(key=lambda x: x["Ngay"])
        lines = []
        lines.append(
            f"Dưới đây là thông tin liên quan về:\n"
            f"- **HS code**: **{hs_code}**\n"
            f"- **Nhà cung cấp**: **{supplier}**\n"
            f"- **Tổng**: {len(filtered_data)} bản ghi\n"
            f"---\n"
        )
        for record in filtered_data:
            day_str = str(record["Ngay"])
            lines.append(f"- **Ngày**: {day_str} ")
            lines.append(f"  - **Tên Hàng**: {self.clean_str_field(record.get('TenHang'), 'tên hàng')} ")
            lines.append(f"  - **Trạng thái:** {self.clean_str_field(record.get('TinhTrang'), 'trạng thái')} ")
            lines.append(f"  - **Lượng**: {record.get('Luong', 0):,} {self.clean_str_field(record.get('DonViTinh'), 'đơn vị tính')} ")
            lines.append(f"  - **Xuất xứ**: {self.clean_str_field(record.get('TenNuocXuatXu'), 'nước xuất xứ')} ")
            lines.append(f"  - **Điều Kiện Giao Hàng**: {self.clean_str_field(record.get('DieuKienGiaoHang'), 'điều kiện giao hàng')}. ")

            def format_tax(val):
                try:
                    num = float(val)
                    return f"{num:.2f}%" if num != 0 else "KCT"
                except (TypeError, ValueError):
                    return "KCT"
            xnk_str = format_tax(record.get('ThueSuatXNK'))
            ttdb_str = format_tax(record.get('ThueSuatTTDB'))
            vat_str = format_tax(record.get('ThueSuatVAT'))
            tuve_str = format_tax(record.get('ThueSuatTuVe'))
            bvmt_str = format_tax(record.get('ThueSuatBVMT'))
            lines.append(
                "  - **Thuế suất XNK:** {} ; **TTĐB:** {} ; **VAT:** {} ; "
                "**Tự vệ:** {} ; **BVMT:** {}  \n\n".format(xnk_str, ttdb_str, vat_str, tuve_str, bvmt_str)
            )
            lines.append("---")
        return "\n".join(lines)



class HSCodeSupplierTool(BaseHsCodeSupplierTool):
    """
    Tool cho phép truy vấn theo hướng: supplier -> hs_code -> in data.
    Lớp này chỉ triển khai hàm _run, các hàm trợ giúp được kế thừa từ BaseHsCodeSupplierTool.
    """
    name: str = "HSCodeSupplierTool"
    description: str = "Retrieve HS code information for a specific supplier from a MySQL database (supplier-first logic)."

    @traceable(run_type="tool")
    def _run(self, supplier: str, hs_code: str) -> str:
        """
        1) Fuzzy supplier: nếu kết quả > 1 thì yêu cầu người dùng chọn.
        2) Nếu chỉ có 1: sử dụng actual_supplier để lấy DISTINCT HS code theo supplier và hs_code.
        3) Nếu chỉ có 1 HS code: lấy dữ liệu chi tiết.
           Nếu dữ liệu quá nhiều, liệt kê danh sách ngày để người dùng chọn.
        """
        message_to_agent = "Good job!"
        if self._tool_agent is None:
            logger.error("tool_agent not set in HSCodeSupplierTool")
            raise ValueError("tool_agent not set")
        self._tool_agent.tool_called[self.name] = True
        logger.info("HSCodeSupplierTool _run called with supplier=%s, hs_code=%s", supplier, hs_code)

        # Kiểm tra gói dịch vụ
        package_type = self._tool_agent.get_package()
        # print(package_type)
        # if package_type in ["trial_package", "vip_package"] and supplier:
        #     self.is_summary = False
        #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
        #     return self.last_result

        try:
            # B1) Fuzzy supplier
            supplier_list = self.match_suppliers_fuzzy(supplier)
            if not supplier_list:
                self.is_summary = False
                self.last_result = (
                    f"Không tìm thấy nhà cung cấp khớp với '**{supplier}**'. Vui lòng kiểm tra lại tên nhà cung cấp."
                )
                return self.last_result

            if len(supplier_list) > 1:
                lines = []
                lines.append(f"Tìm thấy nhiều nhà cung cấp khớp với tên **'{supplier}'**:\n")
                for sup in supplier_list:
                    lines.append(f"- {sup}")
                lines.append("\nVui lòng chọn 1 nhà cung cấp chính xác.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

            # => Nếu chỉ có 1 nhà cung cấp
            actual_supplier = supplier_list[0]
            if actual_supplier.upper() != supplier.upper():
                logger.info("Fuzzy matched supplier: %s -> %s", supplier, actual_supplier)

            # B2) Lấy DISTINCT HS code theo supplier
            matched_hs_codes = self.get_distinct_hs_for_supplier(actual_supplier, hs_code)
            if not matched_hs_codes:
                self.is_summary = False
                self.last_result = (
                    f"Không tìm thấy HS code khớp với **'{hs_code}'** từ nhà cung cấp: **{actual_supplier}**"
                )
                return self.last_result

            if len(matched_hs_codes) > 1:
                lines = []
                lines.append(f"Tìm thấy nhiều HS code khớp với mã **'{hs_code}'** từ nhà cung cấp **{actual_supplier}**:\n")
                for c in matched_hs_codes:
                    lines.append(f"- {c}")
                lines.append("\nVui lòng chọn 1 HS code chính xác.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

            # => Nếu chỉ có 1 HS code
            actual_hs = matched_hs_codes[0]
            # B3) Lấy dữ liệu theo HS code và supplier
            results = self.get_data_by_hs_and_supplier(actual_hs, actual_supplier)
            if not results:
                lines = []
                lines.append(
                    f"Không tìm thấy dữ liệu từ nhà cung cấp **{actual_supplier}** với HS code **{actual_hs}**."
                )
                lines.append("Dưới đây là danh sách ngày của nhà cung cấp này (nếu có):\n")
                lines.append(self.query_suppliers_and_dates([actual_supplier]))
                lines.append("Vui lòng kiểm tra lại Tên nhà cung cấp hoặc HS code.")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

            if len(results) <= 20:
                extra_info = f"Dưới đây là thông tin liên quan về:\n- **HS code**: **{hs_code}**\n- **Nhà cung cấp**: **{supplier}**\n\n"
                self.is_summary = True
                self.last_result = extra_info + formatter.format_records(results, display_date=True, package_type=package_type)
                return message_to_agent
            else:
                date_set = set()
                for r in results:
                    if r["Ngay"]:
                        date_set.add(r["Ngay"].strftime("%Y-%m-%d"))
                lines = []
                lines.append(
                    f"Tôi tìm thấy {len(results)} bản ghi từ nhà cung cấp **{actual_supplier}**, "
                    f"với HS code là **{actual_hs}**. Dữ liệu quá lớn, không thể in hết."
                )
                lines.append("Dưới đây là danh sách ngày liên quan:\n")
                for d in sorted(date_set):
                    lines.append(f"- {d}")
                lines.append("")
                lines.append("Vui lòng chọn 1 ngày (hoặc khoảng ngày <= 10 ngày) để hiển thị chi tiết.\n")
                lines.append("Nhập theo mẫu: mã hs code '...', nhà cung cấp '...', ngày 'YYYY-MM-DD'\n")
                lines.append("Hoặc: mã hs code '...', nhà cung cấp '...', từ ngày 'YYYY-MM-DD' đến ngày 'YYYY-MM-DD'\n")
                self.is_summary = True
                self.last_result = "\n".join(lines)
                return message_to_agent

        except Exception as e:
            logger.error("Error retrieving HS code data: %s", e)
            return f"Error retrieving HS code data: {e}"
