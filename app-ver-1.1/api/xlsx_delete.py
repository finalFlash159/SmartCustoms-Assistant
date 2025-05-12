from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

class DeleteRequest(BaseModel):
    file_name: str

@router.delete("/delete_xlsx")
async def delete_by_file_name(request: Request, delete_req: DeleteRequest):
    """
    Endpoint xóa dữ liệu trên MongoDB dựa trên file_name được truyền qua JSON body.
    Xóa tất cả các documents trong collection có trường file_name bằng giá trị truyền vào.
    """
    file_name = delete_req.file_name
    mongodb_manager = None
    
    try:
        # Lấy MongoDB Manager từ pool
        logger.info("[delete_by_file_name] Đang lấy MongoDB Manager từ pool...")
        mongodb_manager = await request.app.state.mongo_db_queue.get()
        logger.info("[delete_by_file_name] Đã lấy MongoDB Manager từ pool")
        
        # Xóa documents từ MongoDB dựa trên file_name
        delete_result = await mongodb_manager.delete_by_filename(file_name)
        
        if not delete_result.get("success", False):
            error_msg = delete_result.get("error", "Lỗi không xác định khi xóa dữ liệu từ MongoDB")
            logger.error(f"[delete_by_file_name] {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        deleted_count = delete_result.get("deleted_count", 0)
        logger.info(f"[delete_by_file_name] Đã xóa {deleted_count} documents với file_name = {file_name}")
        
        # Xóa file từ thư mục uploaded nếu tồn tại
        try:
            uploaded_file_path = f"data/uploaded/{file_name}.xlsx"
            if os.path.exists(uploaded_file_path):
                os.remove(uploaded_file_path)
                logger.info(f"[delete_by_file_name] Đã xóa file: {uploaded_file_path}")
            else:
                logger.warning(f"[delete_by_file_name] File không tồn tại: {uploaded_file_path}")
        except Exception as e:
            logger.error(f"[delete_by_file_name] Lỗi khi xóa file: {str(e)}")
            # Chỉ hiển thị cảnh báo nhưng không dừng tiến trình nếu không xóa được file
            
        return {
            "file_name": file_name,
            "deleted_count": deleted_count,
            "status": "Đã xóa dữ liệu thành công"
        }
        
    except Exception as e:
        logger.exception(f"[delete_by_file_name] Lỗi: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa dữ liệu: {str(e)}")
    
    finally:
        # Trả lại MongoDB Manager vào pool
        if mongodb_manager is not None:
            await request.app.state.mongo_db_queue.put(mongodb_manager)
            logger.info("[delete_by_file_name] Đã trả MongoDB Manager về pool")