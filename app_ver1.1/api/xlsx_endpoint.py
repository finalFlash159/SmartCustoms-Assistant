import logging
import os
import sys
import asyncio

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
sys.path.append('../')  
from pipelines.xlsx_pipelines.xlsx_processor import xlsx_processor_pipeline

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_xlsx(request: Request, file: UploadFile = File(...)):
    """
    Endpoint để upload và xử lý file XLSX.
    - Nhận file `.xlsx`, kiểm tra định dạng và kích thước.
    - Lưu file vào thư mục tạm, xử lý bằng xlsx_processor_pipeline và lưu vào MongoDB.
    - Trả về trạng thái xử lý và số lượng bản ghi đã thêm.
    """
    mongodb_manager = None
    
    try:
        # Kiểm tra định dạng file
        if not file.filename.lower().endswith(".xlsx"):
            logger.error("[upload_xlsx] File không phải XLSX.")
            raise HTTPException(status_code=400, detail="File phải là XLSX.")

        # Kiểm tra kích thước file
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            logger.error("[upload_xlsx] File quá lớn >10MB.")
            raise HTTPException(status_code=400, detail="File quá lớn, tối đa 10MB.")
        
        # Lưu file tạm
        save_dir = "data/uploaded"
        os.makedirs(save_dir, exist_ok=True)
        save_file_path = os.path.join(save_dir, file.filename)
        
        with open(save_file_path, "wb") as save_file:
            save_file.write(contents)

        logger.info(f"[upload_xlsx] Đã lưu file tạm: {save_file_path}")

        # Lấy MongoDB Manager từ pool
        logger.info("[upload_xlsx] Đang lấy MongoDB Manager từ pool...")
        mongodb_manager = await request.app.state.mongo_db_queue.get()
        logger.info("[upload_xlsx] Đã lấy MongoDB Manager từ pool")

        # Sử dụng xlsx_processor_pipeline để xử lý file và lấy DataFrame + FIELD_MAP
        logger.info("[upload_xlsx] Gọi xlsx_processor_pipeline để xử lý file Excel")
        df = await asyncio.to_thread(xlsx_processor_pipeline, save_file_path)
        
        # # Xóa dữ liệu cũ (nếu có) dựa trên file_name
        # file_name = os.path.splitext(os.path.basename(save_file_path))[0]
        # delete_result = await mongodb_manager.delete_by_filename(file_name)
        # logger.info(f"[upload_xlsx] Đã xóa {delete_result.get('deleted_count', 0)} documents cũ")
        
        # Lưu DataFrame mới vào MongoDB
        upload_result = await mongodb_manager.upload_dataframe(df, request.app.state.config.MONGODB_FIELD_MAP)
        
        if not upload_result.get("success", False):
            raise ValueError(upload_result.get("error", "Lỗi không xác định khi tải lên MongoDB"))
            
        logger.info(f"[upload_xlsx] Đã insert {upload_result.get('inserted_count', 0)} documents mới")
        
        return {
            "filename": file.filename,
            "status": "success",
            "inserted_documents": upload_result.get("inserted_count", 0)
        }
        
    except FileNotFoundError:
        logger.exception("[upload_xlsx] Không tìm thấy file")
        raise HTTPException(status_code=500, detail="Không tìm thấy file hoặc thư mục")
    except PermissionError:
        logger.exception("[upload_xlsx] Không có quyền truy cập")
        raise HTTPException(status_code=500, detail="Không có quyền truy cập thư mục")
    except ValueError as e:
        logger.exception(f"[upload_xlsx] Lỗi dữ liệu: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"[upload_xlsx] Lỗi không xác định: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")
    finally:
        # Trả lại MongoDB Manager vào pool
        if mongodb_manager is not None:
            await request.app.state.mongo_db_queue.put(mongodb_manager)
            logger.info("[upload_xlsx] Đã trả MongoDB Manager về pool")