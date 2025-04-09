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
    - Lưu file vào thư mục tạm cụ thể, xử lý bằng xlsx_processor_pipeline, 
      và lưu kết quả vào MySQL.
    - Trả về trạng thái xử lý.
    """

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

    # Cấu hình DB
    db_config = request.app.state.db_config
    # Xử lý file XLSX
    # Do xlsx_processor_pipeline là hàm đồng bộ, ta có thể gọi trực tiếp
    # hoặc đưa vào executor nếu muốn tránh block event loop.
    try:
        logger.info("[upload_xlsx] Bắt đầu gọi xlsx_processor_pipeline")
        await asyncio.to_thread(xlsx_processor_pipeline, save_file_path, db_config)
        logger.info("[upload_xlsx] Hoàn thành xlsx_processor_pipeline")
    except FileNotFoundError:
        logger.exception("[upload_xlsx] FileNotFoundError")
        raise HTTPException(status_code=500, detail="Không tìm thấy file hoặc thư mục")
    except PermissionError:
        logger.exception("[upload_xlsx] PermissionError")
        raise HTTPException(status_code=500, detail="Không có quyền truy cập thư mục")
    except Exception as e:
        logger.exception("[upload_xlsx] Exception")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    return {"filename": file.filename, "status": "Processed and saved to MySQL"}
