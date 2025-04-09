from typing import Optional, List, Dict
import logging
from langchain.tools import BaseTool
from pydantic import PrivateAttr
from langsmith import traceable
from ..utils.hscode_formatter import HSCodeFormatter

# Import DatabaseConnector từ module utils.db_connector
from utils.db_connector import DatabaseConnector

logger = logging.getLogger(__name__)

formatter = HSCodeFormatter()

class BaseHsCodeSupplierDateRangeTool(BaseTool):
    """
    Lớp cơ sở cho các truy vấn theo HS code, nhà cung cấp và khoảng ngày.
    Chứa:
      - Kết nối CSDL qua DatabaseConnector.
      - Hàm execute để thực thi truy vấn.
      - Hàm format_result định dạng dữ liệu trả về.
    """
    name: str = "BaseHsCodeSupplierDateRangeTool"
    description: str = "Base tool for supplier HSCode date range queries"
    is_summary: bool = False
    last_result: Optional[str] = None

    _tool_agent: Optional["ToolAgent"] = PrivateAttr(default=None)
    _db_config: dict = PrivateAttr()
    _db_connector: DatabaseConnector = PrivateAttr()

    def __init__(self, tool_agent: Optional["ToolAgent"] = None, db_config: dict = None):
        super().__init__()
        if db_config is None:
            raise ValueError("db_config must be provided for BaseHsCodeSupplierDateRangeTool")
        self._tool_agent = tool_agent
        self._db_config = db_config
        self._db_connector = DatabaseConnector(db_config)
        self.is_summary = False
        self.last_result = None


    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Thực thi truy vấn thông qua DatabaseConnector."""
        return self._db_connector.execute_query(query, params)


class HSCodeSupplierDateRangeTool(BaseHsCodeSupplierDateRangeTool):
    """
    Tool truy vấn thông tin HS code cho một nhà cung cấp trong khoảng ngày cụ thể.
    Lớp này chỉ giữ lại hàm _run, sử dụng kết nối CSDL và các hàm tiện ích từ lớp base.
    """
    name: str = "HSCodeSupplierDateRangeTool"
    description: str = (
        "Retrieve HS code information for a specific supplier within a date range "
        "from a MySQL database"
    )

    @traceable(run_type="tool")
    def _run(self, hs_code: str, supplier: str, start_date: str, end_date: str) -> str:
        message_to_agent = "Good job!"
        if self._tool_agent is None:
            logger.error("tool_agent not set in HSCodeSupplierDateRangeTool")
            raise ValueError("tool_agent not set")
        self._tool_agent.tool_called[self.name] = True

        # Kiểm tra gói dịch vụ
        package_type = self._tool_agent.get_package()  
        # if package_type in ["trial_package", "vip_package"] and supplier:
        #     self.is_summary = False
        #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
        #     return self.last_result

        try:
            query = """
                SELECT *
                FROM import_data
                WHERE HsCode = %s
                  AND NhaCungCap = %s
                  AND DATE(Ngay) BETWEEN %s AND %s
                ORDER BY Ngay
            """
            results = self.execute(query, (hs_code, supplier, start_date, end_date))
            if not results:
                self.is_summary = False
                self.last_result = (
                    f"Không tìm thấy dữ liệu cho mã HS code: **{hs_code}**, "
                    f"nhà cung cấp: **{supplier}**, trong khoảng thời gian từ **{start_date}** đến **{end_date}**."
                )
                return self.last_result

            if len(results) <= 20:
                self.is_summary = True
                extra_info = f"Dưới đây là thông tin về:\n- HS code: **{hs_code}**\n- Nhà cung cấp: **{supplier}**\n- Từ ngày **{start_date}** đến **{end_date}**:\n\n"
                self.last_result = extra_info + formatter.format_records(results, display_date=True, package_type=package_type)
                return message_to_agent
            else:
                # Nếu có quá nhiều bản ghi, liệt kê danh sách các ngày liên quan
                query_dates = """
                    SELECT DISTINCT DATE(Ngay) as Ngay
                    FROM import_data
                    WHERE HsCode = %s
                      AND NhaCungCap = %s
                    ORDER BY Ngay
                """
                dates = self.execute(query_dates, (hs_code, supplier))
                date_list = ["- " + str(date['Ngay']) for date in dates if date['Ngay'] is not None]
                self.is_summary = True
                self.last_result = (
                    "Có quá nhiều bản ghi liên quan đến HS code và nhà cung cấp trong khoảng thời gian này.\n"
                    "Dưới đây là danh sách các ngày có dữ liệu liên quan:\n"
                    + "\n".join(date_list) +
                    "\nVui lòng chọn khoảng thời gian ngắn hơn.\n"
                )
                return message_to_agent

        except Exception as e:
            logger.error("Error retrieving HS code + supplier + date range data: %s", e)
            return f"Error retrieving data: {e}"
