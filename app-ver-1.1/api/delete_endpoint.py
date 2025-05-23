import os
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter()

# Đường dẫn thư mục chứa file đã upload
UPLOADED_FOLDER = "data/uploaded"
os.makedirs(UPLOADED_FOLDER, exist_ok=True)

@router.get("/uploaded-files")
async def list_uploaded_files():
    """
    Endpoint liệt kê các file đã upload trong thư mục 'data/uploaded'.
    Trả về danh sách file với:
      - file_name: phần base (không đuôi)
      - file_type: phần đuôi (có dấu chấm, vd ".xlsx")
      - file: gộp base + ext
    """
    if not os.path.exists(UPLOADED_FOLDER):
        logger.warning("Thư mục uploaded không tồn tại.")
        raise HTTPException(status_code=404, detail="Thư mục uploaded không tồn tại.")
    
    files = os.listdir(UPLOADED_FOLDER)
    file_list = []
    for f in files:
        base, ext = os.path.splitext(f)  
        item = {
            "file_name": base,   
            "file_type": ext,    
            "file": base + ext     
        }
        file_list.append(item)
    
    logger.info(f"Đã lấy danh sách {len(file_list)} file từ thư mục uploaded.")
    return {"files": file_list}

class UploadedFileDeletionRequest(BaseModel):
    file_name: str 
    file_type: str  


@router.delete("/delete-uploaded-file")
async def delete_uploaded_file(request: Request, deletion_request: UploadedFileDeletionRequest):
    """
    Endpoint xóa file được chọn trong thư mục "data/uploaded" và xóa các vector liên quan trên Qdrant.

    Quá trình:
      - Kiểm tra file có tồn tại trong thư mục uploaded không.
      - Xác định file_type từ phần mở rộng của file.
      - Gọi hàm xóa trên Qdrant dựa theo metadata (file_name và file_type) từ app.state.vector_store.
      - Xóa file khỏi thư mục uploaded.
    """
    base = deletion_request.file_name      
    ext = deletion_request.file_type        
    actual_filename = base + ext  
    uploaded_file_path = os.path.join(UPLOADED_FOLDER, actual_filename)

    if not os.path.exists(uploaded_file_path):
        raise HTTPException(status_code=404, detail="File không tồn tại.")

    try:
        vector_store = await request.app.state.vector_store_queue.get()
        await vector_store.delete_points_by_metadata(base,  ext)
        logging.info(f"Đã xóa vector của file {actual_filename} trên Qdrant.")
    except Exception as e:
        logging.error(f"Lỗi xóa vector: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi xóa vector: {str(e)}")

    try:
        # Xóa file khỏi disk
        os.remove(uploaded_file_path)
        logging.info(f"Đã xóa file {actual_filename} khỏi thư mục uploaded.")
    except Exception as e:
        logging.error(f"Lỗi xóa file {actual_filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi xóa file: {str(e)}")
    finally:
        if vector_store is not None:
            await request.app.state.vector_store_queue.put(vector_store)
            logging.info("Đã trả vector store về hàng đợi.")

    return {
        "status": "Deleted",
        "file_name": base,
        "file_type": ext
    }