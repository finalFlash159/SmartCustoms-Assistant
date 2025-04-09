from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import mysql.connector
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

class DeleteRequest(BaseModel):
    file_name: str

@router.delete("/delete_xlsx")
async def delete_by_file_name(request: Request, delete_req: DeleteRequest):
    """
    Endpoint xóa dữ liệu trên MySQL dựa trên file_name được truyền qua JSON body.
    Xóa tất cả các dòng trong bảng import_data có cột file_name bằng giá trị truyền vào.
    """
    file_name = delete_req.file_name
    try:
        # Sử dụng cấu hình MySQL; bạn có thể thay đổi theo cấu hình của hệ thống
        db_config = request.app.state.db_config
    except Exception as e:
        logger.error("Không tìm thấy cấu hình MySQL: %s", e)
        raise HTTPException(status_code=500, detail="Database configuration not found.")
        
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        delete_query = """
            DELETE FROM import_data WHERE file_name = %s
        """
        cursor.execute(delete_query, (file_name,))
        conn.commit()
        deleted_count = cursor.rowcount
        cursor.close()
        conn.close()
        logger.info("Đã xóa %s dòng với file_name = %s", deleted_count, file_name)
    except Exception as e:
        logger.error("Lỗi khi xóa dữ liệu: %s", e)
        raise HTTPException(status_code=500, detail=f"Error deleting data: {e}")
    
    try:
         # Xóa file từ thư mục uploaded
        uploaded_file_path = f"data/uploaded/{file_name}.xlsx"
        if os.path.exists(uploaded_file_path):
            os.remove(uploaded_file_path)
            logger.info("Đã xóa file: %s", uploaded_file_path)
        else:
            logger.warning("File không tồn tại: %s", uploaded_file_path)
    except Exception as e:
        logger.error("Lỗi khi xóa file: %s", e)
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")
    
    return {
        "file_name": file_name,
        "deleted_count": deleted_count,
        "status": "Data deleted successfully"
    }