# aggregate_pipeline_generator.py
import json
import os

from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from prompts import get_mongodb_search_template, get_generate_search_query_schema


class AggregatePipelineGenerator:
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo AggregatePipelineGenerator với cấu hình tùy chọn
        
        Args:
            api_key: OpenAI API key
            config: Dictionary chứa cấu hình tùy chỉnh cho tìm kiếm
        """
        # Load environment variables
        load_dotenv()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        # Default configuration
        self.config = {
            "fuzzy_search": {
                "maxEdits": 2,
                "prefixLength": 3,
                "maxExpansions": 20,
                "score_threshold": 0.5,
                "pre_filter_threshold": 0.1
            },
            "result_limit": 20,
            "fields_to_project": [
                "ngay",
                "nha_cung_cap",
                "hs_code",
                "ten_hang",
                "luong",
                "don_vi_tinh",
                "xuat_xu",
                "dieu_kien_giao_hang",
                "thue_suat_xnk",
                "thue_suat_ttdb",
                "thue_suat_vat",
                "thue_suat_tu_ve",
                "thue_suat_bvmt",
                "tinh_trang"
            ]
        }
        
        # Update config with custom values if provided
        if config:
            self._update_config(config)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model="gpt-4-0613",
            temperature=0
        )
        
        # Lấy template và schema từ module prompts
        self.template_system = get_mongodb_search_template()
        self.generate_search_query_schema = get_generate_search_query_schema()
    
    def _update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Cập nhật cấu hình với các giá trị mới
        
        Args:
            new_config: Dictionary chứa các giá trị cấu hình mới
        """
        def deep_update(d: Dict, u: Dict) -> Dict:
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    d[k] = deep_update(d[k], v)
                else:
                    d[k] = v
            return d
        
        self.config = deep_update(self.config, new_config)
    
    async def generate_search_snippet(self, user_query: str) -> Dict[str, Any]:
        """
        Tạo snippet tìm kiếm từ câu query của user
        
        Args:
            user_query: Câu query của user
            
        Returns:
            Dictionary chứa các điều kiện tìm kiếm
        """
        try:
            messages = [
                SystemMessage(content=self.template_system),
                HumanMessage(content=user_query)
            ]
            
            response = await self.llm.ainvoke(
                input=messages,
                tools=[{
                    "type": "function",
                    "function": self.generate_search_query_schema
                }],
                tool_choice={"type": "function", "function": {"name": "generate_search_query"}}
            )
            
            # Xử lý tool_calls từ additional_kwargs
            additional_kwargs = getattr(response, "additional_kwargs", {})
            if "tool_calls" in additional_kwargs and additional_kwargs["tool_calls"]:
                tool_call = additional_kwargs["tool_calls"][0]
                if "function" in tool_call and "arguments" in tool_call["function"]:
                    return json.loads(tool_call["function"]["arguments"])
            
            # Xử lý tool_calls từ thuộc tính trực tiếp
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_call = response.tool_calls[0]
                if isinstance(tool_call, dict) and "args" in tool_call:
                    return tool_call["args"]
                if hasattr(tool_call, "args"):
                    return tool_call.args
            
            raise ValueError("LLM did not return a valid function call.")
        except Exception as e:
            print(f"Error generating search snippet: {str(e)}")
            raise

    async def build_pipeline(self, search_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            pipeline = []
            
            # Process fuzzy search fields
            fuzzy_fields = search_data.get("fuzzy_search", {})
            fuzzy_conditions = []
            
            # Xử lý các trường fuzzy search 
            for field, value in fuzzy_fields.items():
                if value:
                    fuzzy_conditions.append({
                        "text": {
                            "query": value,
                            "path": field,
                            "fuzzy": {k: v for k, v in self.config["fuzzy_search"].items() 
                                    if k not in ["score_boost", "score_threshold", "pre_filter_threshold"]}
                        }
                    })
            
            # Build match conditions
            match_conditions = {}
            
            # Xử lý regex search
            regex_fields = search_data.get("regex_search", {})
            for field, pattern in regex_fields.items():
                if pattern:
                    match_conditions[field] = {"$regex": pattern, "$options": "i"}
            
            # Xử lý exact match - Với xử lý đặc biệt cho trường ngày
            exact_fields = search_data.get("exact_match", {})
            for field, value in exact_fields.items():
                if value:
                    # Xử lý đặc biệt cho trường ngày
                    if field == "ngay" and isinstance(value, str):
                        # Nếu ngày chỉ có dạng YYYY-MM-DD mà không có phần thời gian
                        if "T" not in value:
                            match_conditions[field] = {"$regex": f"^{value}", "$options": "i"}
                        else:
                            match_conditions[field] = value
                    else:
                        match_conditions[field] = value
            
            # Xử lý range queries (khoảng ngày)
            range_queries = search_data.get("range_queries", {})
            date_range = range_queries.get("ngay", {})
            if date_range and "start_date" in date_range and "end_date" in date_range:
                start_date = date_range["start_date"]
                end_date = date_range["end_date"]
                
                # Thêm thành phần thời gian nếu cần
                if "T" not in start_date:
                    start_date = f"{start_date}T00:00:00"
                if "T" not in end_date:
                    end_date = f"{end_date}T23:59:59"
                    
                # Thay thế điều kiện ngày hiện có (nếu có) bằng điều kiện khoảng
                if "ngay" in match_conditions:
                    del match_conditions["ngay"]
                
                match_conditions["ngay"] = {"$gte": start_date, "$lte": end_date}
            
            # Tạo pipeline
            # 1. Thêm $search stage (PHẢI LÀ STAGE ĐẦU TIÊN)
            if fuzzy_conditions:
                pipeline.extend([
                    {"$search": {"index": "default", "compound": {"should": fuzzy_conditions}}},
                    {"$addFields": {"searchScore": {"$meta": "searchScore"}}},
                    
                    # Thêm pre-filter dựa trên threshold tuyệt đối
                    {"$match": {"searchScore": {"$gte": self.config["fuzzy_search"].get("pre_filter_threshold", 0.3)}}},
                    
                    # Tiếp tục với relative threshold như hiện tại
                    {"$facet": {
                        "results": [],
                        "maxScore": [{"$sort": {"searchScore": -1}}, {"$limit": 1}, 
                                {"$project": {"maxScore": "$searchScore"}}]
                    }},
                    {"$project": {
                        "results": {
                            "$filter": {
                                "input": "$results",
                                "as": "item",
                                "cond": {"$gte": ["$$item.searchScore", 
                                        {"$multiply": [{"$arrayElemAt": ["$maxScore.maxScore", 0]}, 
                                                    self.config["fuzzy_search"]["score_threshold"]]}]}
                            }
                        }
                    }},
                    {"$unwind": "$results"},
                    {"$replaceRoot": {"newRoot": "$results"}}
                ])
            
            # 2. Thêm $match stage nếu có match_conditions
            if match_conditions:
                pipeline.append({"$match": match_conditions})
            
            # 3. Thêm các stage cuối cùng
            pipeline.extend([
                {"$project": {field: 1 for field in self.config["fields_to_project"]}},
                {"$limit": self.config["result_limit"]}
            ])
            
            return pipeline
        except Exception as e:
            print(f"Error building MongoDB query: {str(e)}")
            raise
    
    async def generate_pipeline_from_query(self, user_query: str) -> List[Dict[str, Any]]:
        """
        Tạo MongoDB pipeline trực tiếp từ user query
        
        Args:
            user_query: Câu query của user
            
        Returns:
            MongoDB pipeline
        """
        search_data = await self.generate_search_snippet(user_query)
        return await self.build_pipeline(search_data)
    
    async def get_used_fields_from_pipeline(self, pipeline: List[Dict[str, Any]]) -> List[str]:
        """
        Trả về danh sách các trường đã sử dụng trong pipeline, 
        không bao gồm các trường được định nghĩa sẵn trong $project
        
        Args:
            pipeline: MongoDB pipeline đã tạo
            
        Returns:
            List[str]: Danh sách các trường đã sử dụng
        """
        used_fields = set()
        
        for stage in pipeline:
            # Kiểm tra trường trong $search
            if "$search" in stage:
                search_stage = stage["$search"]
                if "compound" in search_stage and "should" in search_stage["compound"]:
                    for condition in search_stage["compound"]["should"]:
                        if "text" in condition and "path" in condition["text"]:
                            used_fields.add(condition["text"]["path"])
            
            # Kiểm tra trường trong $match
            if "$match" in stage:
                match_stage = stage["$match"]
                for field in match_stage:
                    if field != "searchScore":  # Bỏ qua trường meta
                        used_fields.add(field.split('.')[0])  # Lấy trường gốc nếu là trường con
        
        # Trả về danh sách các trường đã sắp xếp
        return sorted(list(used_fields))
    
    async def generate_pipeline_and_fields(self, user_query: str) -> Dict[str, Any]:
        """
        Tạo MongoDB pipeline và trả về cả pipeline và danh sách các trường đã sử dụng
        
        Args:
            user_query: Câu query của người dùng
            
        Returns:
            Dict: Chứa pipeline và danh sách các trường đã sử dụng
        """
        pipeline = await self.generate_pipeline_from_query(user_query)
        used_fields = await self.get_used_fields_from_pipeline(pipeline)
        
        return {
            "pipeline": pipeline,
            "used_fields": used_fields
        }