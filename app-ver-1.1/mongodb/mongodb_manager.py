# mongodb_manager.py
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import pandas as pd
import math
import datetime
import logging

logger = logging.getLogger(__name__)

class MongoDBManager:
    def __init__(self, mongodb_uri: Optional[str] = None, 
                 database_name: Optional[str] = None,
                 collection_name: Optional[str] = None,
                 pool_config: Optional[Dict[str, Any]] = None):
        """
        Khởi tạo MongoDBManager với cấu hình kết nối và pool
        
        Args:
            mongodb_uri: URI kết nối MongoDB
            database_name: Tên database
            collection_name: Tên collection
            pool_config: Cấu hình connection pool
        """
        # Load environment variables
        load_dotenv()
        
        # MongoDB connection settings
        self.mongodb_uri = mongodb_uri or os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = database_name or os.environ.get("MONGODB_DATABASE", "project230255")
        self.collection_name = collection_name or os.environ.get("MONGODB_COLLECTION", "hs_code")
        
        # MongoDB connection pool settings
        self.connection_pool_config = pool_config or {
            "maxPoolSize": 10,  # Số kết nối tối đa trong pool
            "minPoolSize": 1,   # Số kết nối tối thiểu trong pool
            "maxIdleTimeMS": 30000,  # 30 giây
            "waitQueueTimeoutMS": 5000,  # 5 giây
            "retryWrites": True,
            "retryReads": True
        }
        
        self.client = None
        self.db = None
        self.collection = None
        
        # Khởi tạo kết nối
        self._init_connection()
        
    def _init_connection(self) -> None:
        """
        Khởi tạo kết nối MongoDB với connection pool
        """
        try:
            # Tạo client với connection pool settings
            self.client = AsyncIOMotorClient(
                self.mongodb_uri,
                maxPoolSize=self.connection_pool_config["maxPoolSize"],
                minPoolSize=self.connection_pool_config["minPoolSize"],
                maxIdleTimeMS=self.connection_pool_config["maxIdleTimeMS"],
                waitQueueTimeoutMS=self.connection_pool_config["waitQueueTimeoutMS"],
                retryWrites=self.connection_pool_config["retryWrites"],
                retryReads=self.connection_pool_config["retryReads"]
            )
            
            # Lấy database và collection
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            print(f"Kết nối thành công đến MongoDB: {self.database_name}.{self.collection_name}")
            
        except Exception as e:
            print(f"Lỗi kết nối MongoDB: {str(e)}")
            raise
    
    async def execute_aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Thực thi aggregate pipeline trên collection
        
        Args:
            pipeline: MongoDB aggregate pipeline
            
        Returns:
            List các document kết quả
        """
        try:
            cursor = self.collection.aggregate(pipeline)
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Lỗi thực thi aggregate pipeline: {str(e)}")
            raise
    
    async def execute_find(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Thực thi find query trên collection
        
        Args:
            query: MongoDB query
            projection: Projection để chọn fields
            
        Returns:
            List các document kết quả
        """
        try:
            cursor = self.collection.find(query, projection)
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Lỗi thực thi find query: {str(e)}")
            raise
    
    def get_collection(self) -> AsyncIOMotorCollection:
        """
        Lấy MongoDB collection để sử dụng trực tiếp nếu cần
        
        Returns:
            MongoDB Collection object
        """
        return self.collection
    
    def close_connections(self) -> None:
        """
        Đóng tất cả kết nối đến MongoDB
        """
        if hasattr(self, 'client') and self.client:
            self.client.close()
            print("Đã đóng tất cả kết nối MongoDB")
    
    def _default_val(self, val, numeric: bool = False):
        """
        Định dạng giá trị mặc định cho các trường
        
        Args:
            val: Giá trị cần định dạng
            numeric: True nếu trường là số
            
        Returns:
            Giá trị đã được định dạng
        """
        if numeric:
            if isinstance(val, str):
                val = val.replace(',', '.')
            if pd.isna(val) or val == '' or val == 'NaN':
                return None
            else:
                return val
        else:
            if val is None or val == '' or (isinstance(val, float) and math.isnan(val)):
                return ''
            else:
                return val
    
    async def upload_dataframe(self, df: pd.DataFrame, field_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Tải DataFrame lên MongoDB
        
        Args:
            df: DataFrame chứa dữ liệu cần lưu
            field_map: Dictionary ánh xạ từ tên cột sang tên trường MongoDB
            
        Returns:
            Dict thông tin kết quả thao tác
        """
        try:
            # Đổi tên cột trong DataFrame theo field_map
            df_renamed = df.rename(columns=field_map)
            
            # Chuyển DataFrame thành danh sách các document
            records = []
            numeric_fields = ['luong', 'thue_suat_xnk', 'thue_suat_ttdb', 'thue_suat_vat', 
                             'thue_suat_tu_ve', 'thue_suat_bvmt']
            
            for rec in df_renamed.to_dict(orient='records'):
                # Xử lý trường ngày
                if isinstance(rec.get('ngay'), (pd.Timestamp, datetime.date)):
                    rec['ngay'] = rec['ngay'].isoformat()
                
                # Áp dụng giá trị mặc định cho mỗi trường
                processed_rec = {}
                for k, v in rec.items():
                    processed_rec[k] = self._default_val(v, k in numeric_fields)
                
                records.append(processed_rec)
            
            # Insert nhiều document cùng lúc
            result = await self.collection.insert_many(records)
            
            return {
                "success": True,
                "inserted_count": len(result.inserted_ids),
                "inserted_ids": [str(id) for id in result.inserted_ids]
            }
            
        except Exception as e:
            print(f"Lỗi khi tải DataFrame lên MongoDB: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_by_filename(self, file_name: str) -> Dict[str, Any]:
        """
        Xóa các document theo trường file_name
        
        Args:
            file_name: Tên file cần xóa các document liên quan
            
        Returns:
            Dict thông tin kết quả thao tác
        """
        try:
            # kiểm tra xem có document nào có file_name tương ứng không
            find_result = await self.collection.find_one({"file_name": file_name})
            if find_result is None:
                return {
                    "success": False,
                    "error": "Không tìm thấy document có file_name tương ứng"
                }
            else:
                logger.info(f"Đã tìm thấy document có file_name tương ứng: {file_name}")

            # Xóa tất cả document có file_name tương ứng
            result = await self.collection.delete_many({"file_name": file_name})
            
            return {
                "success": True,
                "deleted_count": result.deleted_count
            }
            
        except Exception as e:
            print(f"Lỗi khi xóa document theo file_name '{file_name}': {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }