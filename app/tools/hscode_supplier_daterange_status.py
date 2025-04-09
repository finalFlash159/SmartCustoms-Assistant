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

class BaseHsCodeSupplierDateRangeStatusTool(BaseTool):
    """
    Lớp cơ sở cho truy vấn HS code theo nhà cung cấp, khoảng ngày và tình trạng.
    Chứa các hàm dùng chung như kết nối CSDL, thực thi truy vấn và định dạng kết quả.
    """
    name: str = "BaseHsCodeSupplierDateRangeStatusTool"
    description: str = "Base tool for supplier HSCode date range queries with status"
    is_summary: bool = False
    last_result: Optional[str] = None

    _tool_agent: Optional["ToolAgent"] = PrivateAttr(default=None)
    _db_config: dict = PrivateAttr()
    _db_connector: DatabaseConnector = PrivateAttr()

    def __init__(self, tool_agent: Optional["ToolAgent"] = None, db_config: dict = None):
        super().__init__()
        if db_config is None:
            raise ValueError("db_config must be provided for BaseHsCodeSupplierDateRangeStatusTool")
        self._tool_agent = tool_agent
        self._db_config = db_config
        self._db_connector = DatabaseConnector(db_config)
        self.is_summary = False
        self.last_result = None
    

    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Thực thi truy vấn qua DatabaseConnector."""
        return self._db_connector.execute_query(query, params)


class HSCodeSupplierDateRangeStatusTool(BaseHsCodeSupplierDateRangeStatusTool):
    """
    Tool truy vấn thông tin HS code cho một nhà cung cấp, trong khoảng ngày và với tình trạng cụ thể.
    Lớp này chỉ triển khai hàm _run, sử dụng các hàm tiện ích từ lớp cơ sở.
    """
    name: str = "HSCodeSupplierDateRangeStatusTool"
    description: str = "Retrieve HS code information for a supplier within a date range and status from a MySQL database"

    @traceable(run_type="tool")
    def _run(self, hs_code: str, supplier: str, start_date: str, end_date: str, status: str) -> str:
        message_to_agent = "Good job!"
        if self._tool_agent is None:
            logger.error("tool_agent not set in HSCodeSupplierDateRangeStatusTool")
            raise ValueError("tool_agent not set")
        self._tool_agent.tool_called[self.name] = True

        # Kiểm tra gói dịch vụ
        package_type = self._tool_agent.get_package()
        # if package_type in ["trial_package", "vip_package"] and supplier:
        #     self.is_summary = True
        #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
        #     return self.last_result

        logger.info(
            "HSCodeSupplierDateRangeStatusTool _run called with hs_code=%s, supplier=%s, start_date=%s, end_date=%s, status=%s",
            hs_code, supplier, start_date, end_date, status
        )
        try:
            query = """
                SELECT *
                FROM import_data
                WHERE HsCode = %s 
                  AND NhaCungCap = %s 
                  AND DATE(Ngay) BETWEEN %s AND %s 
                  AND TinhTrang = %s
                ORDER BY Ngay
            """
            results = self.execute(query, (hs_code, supplier, start_date, end_date, status))
            
            if len(results) <= 20:
                self.is_summary = True
                extra_info = f"Dưới đây là thông tin về:\n- Mã HS **{hs_code}**\n- Nhà cung cấp **{supplier}**\n- Từ ngày **{start_date}** đến **{end_date}**\n- Trạng thái **{status}**:\n\n"
                self.last_result = extra_info + formatter.format_records(results, display_date=True, package_type=package_type)
                return message_to_agent
            else:
                self.is_summary = True
                self.last_result = (
                    f"Có quá nhiều bản ghi ({len(results)}) cho HS code {hs_code}, nhà cung cấp {supplier}, "
                    f"tình trạng {status} trong khoảng {start_date} đến {end_date}.\n"
                    "Vui lòng chọn khoảng thời gian ngắn hơn (tối đa 10 ngày)."
                )
                return message_to_agent

        except Exception as e:
            logger.error("Error retrieving data: %s", e)
            return f"Error retrieving data: {e}"
