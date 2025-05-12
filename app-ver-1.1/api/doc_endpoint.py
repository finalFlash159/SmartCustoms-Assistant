from fastapi import APIRouter, UploadFile, File, HTTPException, Request
import os
import sys
import asyncio
sys.path.append('../') 

from pipelines.doc_pipelines.doc_processor import doc_processor_pipeline
from utils.data_preparation import DataLoader


router = APIRouter()

@router.post("/upload")
async def upload_doc(request: Request, file: UploadFile = File(...)):
    """
    Endpoint để upload và xử lý file DOC hoặc DOCX.
    - Nhận file `.doc` hoặc `.docx`, kiểm tra định dạng và kích thước.
    - Lưu file tạm thời, xử lý bằng doc_processor_pipeline, và lưu kết quả thành JSON.
    - Trả về trạng thái xử lý.
    """
    if not file.filename.endswith((".doc", ".docx")):
        raise HTTPException(status_code=400, detail="File phải là DOC hoặc DOCX.")
    
    # Kiểm tra kích thước file (tối đa 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File quá lớn, tối đa 10MB.")

    # Xác định thư mục tạm cụ thể cho file upload
    save_dir = "data/uploaded"
    os.makedirs(save_dir, exist_ok=True)
    save_file_path = os.path.join(save_dir, file.filename)
    save_file_path = os.path.abspath(save_file_path)
    
    # Lưu file upload vào thư mục
    with open(save_file_path, "wb") as save_file:
        save_file.write(contents)

        loop = asyncio.get_running_loop()
        try:
            json_str = doc_processor_pipeline(save_file_path)
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Không tìm thấy file hoặc thư mục")
        except PermissionError:
            raise HTTPException(status_code=500, detail="Không có quyền truy cập thư mục")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

        # Đọc dữ liệu từ file JSON để lấy danh sách văn bản cần tạo embedding
        try:
            dataloader = DataLoader(json_str, content="content")
            texts = dataloader.prepare_data_from_json()
            metadata = dataloader.prepare_metadata_from_json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi chuẩn bị dữ liệu: {str(e)}")

        # Lấy VectorStoreManager từ queue
        vector_store = await request.app.state.vector_store_queue.get()
        try:
            # Tạo embedding và lưu vào Qdrant
            await vector_store.store_embeddings(texts, metadata)
        except Exception as e:
            # Nếu có lỗi, vẫn trả VectorStoreManager về queue trước khi raise exception
            await request.app.state.vector_store_queue.put(vector_store)
            raise HTTPException(status_code=500, detail=f"Lỗi lưu embeddings vào Qdrant: {str(e)}")
        finally:
            # Trả VectorStoreManager về queue sau khi sử dụng
            await request.app.state.vector_store_queue.put(vector_store)

    # Trả về phản hồi
    return {"filename": file.filename, "status": "Processed, embeddings created and saved to Qdrant"}