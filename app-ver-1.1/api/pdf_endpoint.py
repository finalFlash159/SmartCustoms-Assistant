from fastapi import APIRouter, UploadFile, File, HTTPException, Request
import os
import sys
import asyncio
sys.path.append('../')  

from pipelines.pdf_pipelines.pdf_processor import pdf_processor_pipeline
from utils.data_preparation import DataLoader
from fastapi.responses import FileResponse

router = APIRouter()

@router.post("/upload")
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    """
    Endpoint để upload và xử lý file PDF.
    - Nhận file `.pdf`, `.PDF`, kiểm tra định dạng và kích thước.
    - Lưu file vào thư mục tạm cụ thể, xử lý bằng pdf_processor_pipeline, 
      và lưu kết quả thành JSON với tên dựa trên file gốc.
    - Tạo embedding cho các văn bản trong JSON và lưu vào Qdrant.
    - Trả về trạng thái xử lý.
    """

    # Kiểm tra định dạng file
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File phải là pdf.")

    # Kiểm tra kích thước file (tối đa 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File quá lớn, tối đa 10MB.")
    
    # Xác định thư mục tạm cụ thể cho file upload
    save_dir = "data/uploaded"
    os.makedirs(save_dir, exist_ok=True)
    save_file_path = os.path.join(save_dir, file.filename)
    
    # Lưu file upload vào thư mục
    with open(save_file_path, "wb") as save_file:
        save_file.write(contents)

    # Xử lý file và bắt lỗi nếu có
    loop = asyncio.get_running_loop()
    try:
       json_str =  pdf_processor_pipeline(save_file_path, model_path=request.app.state.config.YOLO_MODEL_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Không tìm thấy file hoặc thư mục")
    except PermissionError:
        raise HTTPException(status_code=500, detail="Không có quyền truy cập thư mục")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    try:
        # Tạo URL tải xuống
        host_url = str(request.base_url).rstrip('/')
        download_url = f"{host_url}/pdf/download/{file.filename}"

        dataloader = DataLoader(json_str, content="content")
        texts = dataloader.prepare_data_from_json()
        metadata = dataloader.prepare_metadata_from_json()

        # Thêm download_url vào metadata của mỗi phần
        for meta in metadata:
            meta["download_url"] = download_url

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


@router.get("/download/{file_name}")
async def download_pdf(file_name: str):
    """Endpoint để tải xuống file PDF đã upload"""
    file_path = os.path.join("data/uploaded", file_name)
    
    # Kiểm tra file tồn tại
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File không tồn tại")
    
    # Tạo response để tải file
    return FileResponse(
        path=file_path, 
        filename=file_name,
        media_type="application/pdf"
    )