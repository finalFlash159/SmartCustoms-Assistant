from langchain.tools import BaseTool
from typing import Optional, List, Dict, Union, Any
import logging
from datetime import datetime
from pydantic import PrivateAttr, Field
from rapidfuzz import fuzz  # Thư viện tính độ tương đồng
from ..utils.hscode_formatter import HSCodeFormatter
from utils.db_connector import DatabaseConnector

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

formatter = HSCodeFormatter()

def calculate_keyword_similarity(query: str, target: str, word_similarity_threshold: float = 80.0) -> float:
    """
    Calculate similarity score based on keyword matching.
    
    Args:
        query (str): The query string.
        target (str): The target string.
        word_similarity_threshold (float): Minimum similarity score for a word to be considered a match.
    
    Returns:
        float: Similarity score (0-100) based on keyword matching.
    """
    query = query.lower()
    target = target.lower()
    
    query_words = query.split()
    target_words = target.split()
    
    if not query_words:
        return 0.0
    
    matched_words = 0
    for query_word in query_words:
        best_match_score = max(
            (fuzz.ratio(query_word, target_word) for target_word in target_words),
            default=0.0
        )
        if best_match_score >= word_similarity_threshold:
            matched_words += 1
    
    similarity = (matched_words / len(query_words)) * 100
    return similarity

def sanitize_query(text: str) -> str:
    """Remove unwanted characters from query string."""
    if not isinstance(text, str):
        return str(text)
    
    # Remove leading and trailing #& markers
    text = text.strip()
    while text.startswith("#&"):
        text = text[2:].lstrip()
    while text.endswith("#&"):
        text = text[:-2].rstrip()
    
    # Replace potentially harmful characters
    text = text.replace("'", "")  # Remove single quotes to prevent SQL injection
    text = text.replace("#&", ",")
    
    return text.lower()  # Convert to lowercase for case-insensitive search

class BaseProductTool(BaseTool):
    """Base class for product search tools."""
    name: str = "BaseProductTool"
    description: str = "Base tool for product searches"
    is_summary: bool = False
    last_result: Optional[str] = None
    threshold: float = Field(default=0.3, description="Minimum score threshold for FULLTEXT search")
    max_results: int = Field(default=40, description="Maximum number of results to display directly")
    similarity_threshold: float = Field(default=80.0, description="Minimum similarity score to keep a result (0-100)")
    _tool_agent: Optional["ToolAgent"] = PrivateAttr(default=None)
    _db_connector: Optional[DatabaseConnector] = PrivateAttr(default=None)
    
    def __init__(self, tool_agent: Optional["ToolAgent"] = None, db_config: dict = None):
        super().__init__()
        if db_config is None:
            raise ValueError("Database configuration must be provided")
        self._tool_agent = tool_agent
        self._db_connector = DatabaseConnector(db_config)
        self.is_summary = False
        self.last_result = None
    
    def get_distinct_dates_from_results(self, results: List[Dict]) -> List[str]:
        """Lấy danh sách các ngày (distinct) từ kết quả."""
        dates = {result['Ngay'].strftime("%Y-%m-%d") for result in results if result.get('Ngay')}
        return sorted(dates, reverse=True)

# 1. ProductNameSearchTool
class ProductNameSearchTool(BaseProductTool):
    name: str = "ProductNameSearchTool"
    description: str = "Retrieve product (TenHang) information based on item name, supports compatible search from a MySQL database"
    
    def _run(self, query: str) -> str:
        """Execute product name search query."""
        if self._tool_agent is None:
            logger.error("tool_agent not set in ProductNameSearchTool")
            raise ValueError("tool_agent not set")

        self._tool_agent.tool_called[self.name] = True
        cleaned_query = sanitize_query(query)
        message_to_agent = "Good job!"

        package_type = self._tool_agent.get_package()
        # if package_type in ["trial_package", "vip_package"]:
        #     self.is_summary = False
        #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
        #     return self.last_result
        
        try:
            search_query = """
                SELECT *, MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE) AS score 
                FROM import_data 
                WHERE MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE) 
                ORDER BY score DESC
            """
            
            all_results = self._db_connector.execute_query(search_query, (cleaned_query, cleaned_query))
            if not all_results:
                self.is_summary = True
                self.last_result = "Không tìm thấy sản phẩm nào khớp với yêu cầu."
                return self.last_result
            
            for result in all_results:
                ten_hang = result.get('TenHang', "")
                result['similarity'] = calculate_keyword_similarity(cleaned_query, ten_hang)
            
            filtered_results = [result for result in all_results if result['similarity'] >= self.similarity_threshold]

            # # Nếu số kết quả vượt quá max_results thì trả về danh sách ngày liên quan
            # if len(filtered_results) > self.max_results:
            #     dates = self.get_distinct_dates_from_results(filtered_results)
            #     self.is_summary = True
            #     self.last_result = (
            #         f"Tìm thấy {len(filtered_results)} sản phẩm. Vui lòng chọn ngày cụ thể từ danh sách sau:\n" +
            #         "\n".join(f"- {date}" for date in dates)
            #     )
            #     return message_to_agent
            # else:
            #     self.is_summary = True
            #     self.last_result = "Dưới đây là thông tin về các sản phẩm liên quan:\n" + self.format_result(filtered_results)
            #     return message_to_agent

            self.is_summary = True 
            self.last_result = f"Dưới đây là thông tin về các sản phẩm liên quan **'{query}'**:\n\n" + formatter.format_records(filtered_results, display_date=True, package_type=package_type)
            return message_to_agent

        except Exception as e:
            logger.error(f"Error searching for product name: {e}")
            return f"Lỗi khi tìm kiếm sản phẩm: {str(e)}"


# 2. ProductNameStatusTool
class ProductNameStatusTool(BaseProductTool):
    name: str = "ProductNameStatusTool"
    description: str = "Retrieve product (TenHang) information based on item name and status from a MySQL database"
    
    def _run(self, query: str, status: str) -> str:
        if self._tool_agent is None:
            raise ValueError("tool_agent not set in ProductNameStatusTool")
        self._tool_agent.tool_called[self.name] = True
        cleaned_query = sanitize_query(query)
        message_to_agent = "Good job!"

        package_type = self._tool_agent.get_package()
        # if package_type in ["trial_package", "vip_package"]:
        #     self.is_summary = False
        #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
        #     return self.last_result
        
        try:
            search_query = """
                SELECT *, MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE) AS score 
                FROM import_data 
                WHERE MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE)
                  AND TinhTrang = %s
                ORDER BY score DESC
            """
            all_results = self._db_connector.execute_query(search_query, (cleaned_query, cleaned_query, status))
            if not all_results:
                self.is_summary = True
                self.last_result = f"Không tìm thấy sản phẩm nào với yêu cầu '{query}' và tình trạng '{status}'."
                return self.last_result

            for result in all_results:
                ten_hang = result.get('TenHang', "")
                result['similarity'] = calculate_keyword_similarity(cleaned_query, ten_hang)
            
            filtered_results = [result for result in all_results if result['similarity'] >= self.similarity_threshold]

            # # Nếu số kết quả vượt quá max_results thì trả về danh sách ngày liên quan
            # if len(filtered_results) > self.max_results:
            #     dates = self.get_distinct_dates_from_results(filtered_results)
            #     self.is_summary = True
            #     self.last_result = (
            #         f"Tìm thấy {len(filtered_results)} sản phẩm. Vui lòng chọn ngày cụ thể từ danh sách sau:\n" +
            #         "\n".join(f"- {date}" for date in dates)
            #     )
            #     return  message_to_agent
            # else:
            #     self.is_summary = True
            #     self.last_result = f"Dưới đây là thông tin về các sản phẩm liên quan '{query}', trạng thái '{status}':\n" + self.format_result(filtered_results)
            #     return  message_to_agent
            self.is_summary = True
            self.last_result = f"Dưới đây là thông tin về các sản phẩm liên quan '{query}', trạng thái '{status}':\n\n" + formatter.format_records(filtered_results, display_date=True, package_type=package_type)
            return message_to_agent

        except Exception as e:
            logger.error(f"Error in ProductNameStatusTool: {e}")
            return f"Lỗi khi tìm kiếm sản phẩm: {str(e)}"


# 3. ProductNameDateTool (không lọc qua max_results)
class ProductNameDateTool(BaseProductTool):
    name: str = "ProductNameDateTool"
    description: str = "Retrieve product (TenHang) information based on item name and specific date from a MySQL database"
    
    def _run(self, query: str, date_str: str) -> str:
        if self._tool_agent is None:
            raise ValueError("tool_agent not set in ProductNameDateTool")
        self._tool_agent.tool_called[self.name] = True
        cleaned_query = sanitize_query(query)
        message_to_agent = "Good job!"

        package_type = self._tool_agent.get_package()
        # if package_type in ["trial_package", "vip_package"]:
        #     self.is_summary = False
        #     self.last_result = "Hãy đăng ký gói **max_package** để truy cập thông tin nhà cung cấp."
        #     return self.last_result

        try:
            search_query = """
                SELECT *, MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE) AS score 
                FROM import_data 
                WHERE MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE)
                  AND DATE(Ngay) = %s
                ORDER BY score DESC
            """
            all_results = self._db_connector.execute_query(search_query, (cleaned_query, cleaned_query, date_str))
            if not all_results:
                self.is_summary = True
                self.last_result = f"Không tìm thấy sản phẩm nào khớp với yêu cầu '{query}', ngày '{date_str}'."
                return self.last_result

            for result in all_results:
                ten_hang = result.get('TenHang', "")
                result['similarity'] = calculate_keyword_similarity(cleaned_query, ten_hang)
            filtered_results = [result for result in all_results if result['similarity'] >= self.similarity_threshold]

            # if len(filtered_results) > 10:
                # Nhóm theo nhà cung cấp: mỗi nhà cung cấp chỉ lấy 1 record (record có similarity cao nhất)
                # supplier_dict = {}
                # for r in filtered_results:
                #     supplier = r.get('NhaCungCap', "Không có thông tin về nhà cung cấp")
                #     if supplier not in supplier_dict or r['similarity'] > supplier_dict[supplier]['similarity']:
                #         supplier_dict[supplier] = r
                # grouped_results = list(supplier_dict.values())
                # formatted = self.format_result(grouped_results)
                # extra_message = (
                #     "(Số lượng bản sản phẩm trùng khớp rất nhiều, mình in tương ứng 1 bản ghi "
                #     "cho mỗi nhà cung cấp khác nhau, bạn hãy dựa vào thông tin về **mã HS** hoặc **Nhà cung cấp** "
                #     "cùng các thông tin liên quan để tra cứu thêm nhé.)"
                # )
                # self.is_summary = True
                # self.last_result = (
                #     f"Dưới đây là thông tin tóm tắt về các sản phẩm liên quan '{query}' ở ngày '{date_str}':\n"
                #     + formatted + "\n" + extra_message
                # )
                # return message_to_agent
            self.is_summary = True
            self.last_result = f"Dưới đây là thông tin về các sản phẩm liên quan '{query}' ở ngày '{date_str}':\n\n" + formatter.format_records(filtered_results, display_date=False, package_type=package_type)
            return message_to_agent
    
        
        except Exception as e:
            logger.error(f"Error in ProductNameDateTool: {e}")
            return f"Lỗi khi tìm kiếm sản phẩm: {str(e)}"


# 4. ProductNameDateRangeTool
class ProductNameDateRangeTool(BaseProductTool):
    name: str = "ProductNameDateRangeTool"
    description: str = "Retrieve product (TenHang) information based on item name within a date range from a MySQL database"
    
    def _run(self, query: str, start_date: str, end_date: str) -> str:
        if self._tool_agent is None:
            raise ValueError("tool_agent not set in ProductNameDateRangeTool")
        self._tool_agent.tool_called[self.name] = True
        cleaned_query = sanitize_query(query)
        message_to_agent = "Good job!"
        package_type = self._tool_agent.get_package()

        try:
            search_query = """
                SELECT *, MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE) AS score 
                FROM import_data 
                WHERE MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE)
                  AND DATE(Ngay) BETWEEN %s AND %s
                ORDER BY score DESC
            """
            all_results = self._db_connector.execute_query(search_query, (cleaned_query, cleaned_query, start_date, end_date))
            if not all_results:
                self.is_summary = True
                self.last_result = f"Không tìm thấy sản phẩm nào với yêu cầu '{query}', từ ngày '{start_date}' đến ngày '{end_date}'."
                return self.last_result

            for result in all_results:
                ten_hang = result.get('TenHang', "")
                result['similarity'] = calculate_keyword_similarity(cleaned_query, ten_hang)
            filtered_results = [result for result in all_results if result['similarity'] >= self.similarity_threshold]

            # # Nếu quá nhiều kết quả, trả về danh sách các ngày liên quan
            # if len(filtered_results) > self.max_results:
            #     dates = self.get_distinct_dates_from_results(filtered_results)
            #     self.is_summary = True
            #     self.last_result = (
            #         f"Có quá nhiều sản phẩm trong khoảng từ {start_date} đến {end_date}.\n"
            #         f"Vui lòng chọn khoảng ngày cụ thể từ danh sách sau:\n"
            #         + "\n".join(f"- {date}" for date in dates)
            #     )
            #     return  message_to_agent
            # else:
            #     self.is_summary = True
            #     self.last_result = f"Dưới đây là thông tin về các sản phẩm liên quan về {query} từ ngày {start_date} đến {end_date}:\n" + self.format_result(filtered_results)
            #     return  message_to_agent

            self.is_summary = True
            self.last_result = f"Dưới đây là thông tin về các sản phẩm liên quan '{query}' từ ngày {start_date} đến {end_date}:\n\n" + formatter.format_records(filtered_results, display_date=True, package_type=package_type)
            return message_to_agent

        except Exception as e:
            logger.error(f"Error in ProductNameDateRangeTool: {e}")
            return f"Lỗi khi tìm kiếm sản phẩm: {str(e)}"


# 5. ProductNameDateStatusTool (không lọc qua max_results)
class ProductNameDateStatusTool(BaseProductTool):
    name: str = "ProductNameDateStatusTool"
    description: str = "Retrieve product (TenHang) information based on item name, specific date and status from a MySQL database"
    
    def _run(self, query: str, date_str: str, status: str) -> str:
        if self._tool_agent is None:
            raise ValueError("tool_agent not set in ProductNameDateStatusTool")
        self._tool_agent.tool_called[self.name] = True
        cleaned_query = sanitize_query(query)
        message_to_agent = "Good job!"
        package_type = self._tool_agent.get_package()
        try:
            search_query = """
                SELECT *, MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE) AS score 
                FROM import_data 
                WHERE MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE)
                  AND DATE(Ngay) = %s AND TinhTrang = %s
                ORDER BY score DESC
            """
            all_results = self._db_connector.execute_query(search_query, (cleaned_query, cleaned_query, date_str, status))
            if not all_results:
                self.is_summary = True
                self.last_result = f"Không tìm thấy sản phẩm nào với yêu cầu '{query}', ngày '{date_str}' và tình trạng '{status}'."
                return self.last_result

            for result in all_results:
                ten_hang = result.get('TenHang', "")
                result['similarity'] = calculate_keyword_similarity(cleaned_query, ten_hang)
            filtered_results = [result for result in all_results if result['similarity'] >= self.similarity_threshold]

            # if len(filtered_results) > 10:
                # # Nhóm theo nhà cung cấp
                # supplier_dict = {}
                # for r in filtered_results:
                #     supplier = r.get('NhaCungCap', "Không có thông tin về nhà cung cấp")
                #     if supplier not in supplier_dict or r['similarity'] > supplier_dict[supplier]['similarity']:
                #         supplier_dict[supplier] = r
                # grouped_results = list(supplier_dict.values())
                # formatted = self.format_result(grouped_results)
                # extra_message = (
                #     "(Số lượng bản sản phẩm trùng khớp rất nhiều, mình in tương ứng 1 bản ghi "
                #     "cho mỗi nhà cung cấp khác nhau, bạn hãy dựa vào thông tin về **mã HS** hoặc **Nhà cung cấp** "
                #     "cùng các thông tin liên quan để tra cứu thêm nhé.)"
                # )
                # self.is_summary = True
                # self.last_result = (
                #     f"Dưới đây là thông tin tóm tắt về các sản phẩm liên quan '{query}', ngày '{date_str}' và tình trạng '{status}':\n"
                #     + formatted + "\n" + extra_message
                # )
                # return message_to_agent
            self.is_summary = True
            self.last_result = f"Dưới đây là thông tin về các sản phẩm liên quan '{query}', ngày '{date_str}' và tình trạng '{status}':\n\n" + formatter.format_records(filtered_results, display_date=False, package_type=package_type)
            return message_to_agent

        except Exception as e:
            logger.error(f"Error in ProductNameDateStatusTool: {e}")
            return f"Lỗi khi tìm kiếm sản phẩm: {str(e)}"


# 6. ProductNameDaterangeStatusTool
class ProductNameDaterangeStatusTool(BaseProductTool):
    name: str = "ProductNameDaterangeStatusTool"
    description: str = "Retrieve product (TenHang) information based on item name within a date range and status from a MySQL database"
    
    def _run(self, query: str, start_date: str, end_date: str, status: str) -> str:
        if self._tool_agent is None:
            raise ValueError("tool_agent not set in ProductNameDaterangeStatusTool")
        self._tool_agent.tool_called[self.name] = True
        cleaned_query = sanitize_query(query)
        message_to_agent = "Good job!"
        package_type = self._tool_agent.get_package()
        try:
            search_query = """
                SELECT *, MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE) AS score 
                FROM import_data 
                WHERE MATCH(TenHang) AGAINST(%s IN NATURAL LANGUAGE MODE)
                  AND DATE(Ngay) BETWEEN %s AND %s AND TinhTrang = %s
                HAVING score > %s 
                ORDER BY score DESC
            """
            all_results = self._db_connector.execute_query(
                search_query, 
                (cleaned_query, cleaned_query, start_date, end_date, status, self.threshold)
            )
            if not all_results:
                self.is_summary = True
                self.last_result = f"Không tìm thấy sản phẩm nào với yêu cầu '{query}', từ ngày '{start_date}' đến '{end_date}' với tình trạng '{status}'."
                return self.last_result

            for result in all_results:
                ten_hang = result.get('TenHang', "")
                result['similarity'] = calculate_keyword_similarity(cleaned_query, ten_hang)
            filtered_results = [result for result in all_results if result['similarity'] >= self.similarity_threshold]

            # Nếu quá nhiều kết quả, trả về danh sách các ngày liên quan
            # if len(filtered_results) > self.max_results:
            #     dates = self.get_distinct_dates_from_results(filtered_results)
            #     self.is_summary = True
            #     self.last_result = (
            #         f"Có quá nhiều sản phẩm trong khoảng từ {start_date} đến {end_date} với tình trạng '{status}'.\n"
            #         f"Vui lòng chọn khoảng ngày cụ thể từ danh sách sau:\n"
            #         + "\n".join(f"- {date}" for date in dates)
            #     )
            #     return message_to_agent
            # else:
            #     self.is_summary = True
            #     self.last_result = f"Dưới đây là thông tin về các sản phẩm liên quan về {query} từ ngày {start_date} đến {end_date} với tình trạng '{status}':\n" + self.format_result(filtered_results)
            #     return  message_to_agent
            self.is_summary = True
            self.last_result = f"Dưới đây là thông tin về các sản phẩm liên quan '{query}' từ ngày {start_date} đến {end_date} với tình trạng '{status}':\n\n" + formatter.format_records(filtered_results, display_date=True, package_type=package_type)
            return message_to_agent
            
        except Exception as e:
            logger.error(f"Error in ProductNameDaterangeStatusTool: {e}")
            return f"Lỗi khi tìm kiếm sản phẩm: {str(e)}"
