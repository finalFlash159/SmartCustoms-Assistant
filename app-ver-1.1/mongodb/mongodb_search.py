# mongodb_search.py
from typing import Dict, Any, List, Optional
from utils.results_formatter import ResultsFormatter
from mongodb.mongodb_manager import MongoDBManager
from llms.aggregate_pipeline_generator import AggregatePipelineGenerator


class MongoDBSearch:
    def __init__(self, 
                 db_manager: MongoDBManager,
                 pipeline_generator: AggregatePipelineGenerator,
                 formatter: Optional[ResultsFormatter] = None):
        """
        Khởi tạo MongoDBSearch với dependencies được truyền vào
        
        Args:
            db_manager: Instance của MongoDBManager
            pipeline_generator: Instance của AggregatePipelineGenerator
            config: Dictionary chứa cấu hình tìm kiếm
        """
        # Sử dụng db_manager được truyền vào
        self.db_manager = db_manager
        
        self.pipeline_generator = pipeline_generator
        
        self.formatter = formatter or ResultsFormatter()
    
    async def search(self, user_query: str) -> Dict[str, Any]:
        """
        Thực hiện tìm kiếm từ câu query của user
        
        Args:
            user_query: Câu query của user
            
        Returns:
            Dict chứa kết quả tìm kiếm và các trường đã sử dụng
        """
        try:
            # Tạo pipeline và lấy các trường đã sử dụng
            pipeline_data = await self.pipeline_generator.generate_pipeline_and_fields(user_query)
            pipeline = pipeline_data["pipeline"]
            used_fields = pipeline_data["used_fields"]
            
            # Thực thi pipeline
            results = await self.db_manager.execute_aggregate(pipeline)
            
            return {
                "results": results,
                "used_fields": used_fields
            }
        except Exception as e:
            print(f"Error performing search: {str(e)}")
            raise
    
    def format_results(self, search_result: Dict[str, Any], num_results: int = 5) -> str:
        """
        Định dạng kết quả tìm kiếm
        
        Args:
            search_result: Kết quả tìm kiếm bao gồm results và used_fields
            num_results: Số lượng kết quả tối đa hiển thị
            
        Returns:
            Chuỗi định dạng
        """
        results = search_result.get("results", [])
        used_fields = search_result.get("used_fields", [])
        
        return self.formatter.format_records(results, num_results, used_fields)
    
    def format_summary(self, results: List[Dict[str, Any]]) -> str:
        """
        Tạo bản tóm tắt từ kết quả tìm kiếm
        
        Args:
            results: Kết quả tìm kiếm
            
        Returns:
            Chuỗi tóm tắt
        """
        return self.formatter.format_summary(results)
    
    async def handle_query(self, user_query: str, num_results: int = 5) -> str:
        """
        Search và format kết quả sau đó xử lý và trả về cho user
        
        Args:
            user_query: Câu query của người dùng
            
        Returns:
            Tuple[str, List]: Tuple chứa kết quả đã được định dạng và pipeline đã sử dụng
        """
        try:
            # Gọi phương thức search mới trả về cả results và used_fields
            search_result = await self.search(user_query)
            # Format kết quả với used_fields
            formatted_results = self.format_results(search_result, num_results)
            return formatted_results
        except Exception as e:
            print(f"Error handling query: {str(e)}")
            raise
    

    async def get_pipeline_for_debug(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Lấy MongoDB pipeline để debug
        
        Args:
            user_query: Câu query của user
            
        Returns:
            MongoDB pipeline
        """
        return await self.pipeline_generator.generate_pipeline_from_query(user_query)