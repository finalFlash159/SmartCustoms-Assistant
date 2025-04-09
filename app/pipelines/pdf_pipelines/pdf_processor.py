import cv2
from PIL import Image
import numpy as np 
from typing import List, Tuple
import math
import json
import os
from concurrent.futures import ThreadPoolExecutor

from .image_processor import ImagePreprocessor
from .yolo_detector import YoloProcessor 
# from .gpt_ocr import ImageOCR

import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_text(text: str) -> List[str]:
    """
    Chia văn bản thành các đoạn dựa trên số token:
      - Nếu token_count <= 700: không chia, trả về toàn bộ văn bản.
      - Nếu 700 < token_count <= 1000: chia thành 2 đoạn.
      - Nếu 1000 < token_count <= 1500: chia thành 3 đoạn.
      - Nếu 1500 < token_count <= 2000: chia thành 4 đoạn.
      - Nếu token_count > 2000: tính số đoạn sao cho mỗi đoạn không quá 500 token.
      
    Args:
        text (str): Văn bản gốc.
        
    Returns:
        List[str]: Danh sách các đoạn văn bản.
    """
    tokens = text.split()
    token_count = len(tokens)
    
    if token_count <= 700:
        splits = 1
    elif token_count <= 1000:
        splits = 2
    elif token_count <= 1500:
        splits = 3
    elif token_count <= 2000:
        splits = 4
    else:
        splits = math.ceil(token_count / 500)
    
    chunk_size = math.ceil(token_count / splits)
    segments = []
    for i in range(splits):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, token_count)
        segment = " ".join(tokens[start:end])
        segments.append(segment)
    
    return segments

def overlap_segments(segments: List[str], overlap_ratio: float = 0.15) -> List[str]:
    """
    Tạo các segments mới có phần overlap giữa các đoạn liên tiếp.
    Với mỗi đoạn (ngoại trừ đoạn cuối), nối thêm phần đầu của đoạn sau vào cuối đoạn hiện tại.
    
    Args:
        segments (List[str]): Danh sách các đoạn văn bản.
        overlap_ratio (float): Tỷ lệ token của đoạn sau sẽ được thêm vào đoạn trước.
        
    Returns:
        List[str]: Danh sách segments đã được bổ sung overlap.
    """
    if not segments:
        return segments

    overlapped = []
    for i in range(len(segments) - 1):
        current_tokens = segments[i].split()
        next_tokens = segments[i + 1].split()
        overlap_count = int(len(next_tokens) * overlap_ratio)
        overlap_tokens = next_tokens[:overlap_count] if overlap_count > 0 else []
        new_segment = segments[i] + " " + " ".join(overlap_tokens)
        overlapped.append(new_segment)
    
    overlapped.append(segments[-1])
    return overlapped

def segments_to_json(segments: List[str], metadata: dict = None) -> str:
    """
    Chuyển danh sách segments thành chuỗi JSON với định dạng:
    [{"content": segment, "metadata": metadata}, ...].

    Args:
        segments (List[str]): Danh sách các chuỗi văn bản (segments).
        metadata (dict): Metadata để gắn vào mỗi segment.

    Returns:
        str: Chuỗi JSON được định dạng.
    """
    data = [{"content": seg, "metadata": metadata} for seg in segments]
    return json.dumps(data, ensure_ascii=False, indent=4)

def image_processor_pipeline(
    pdf_path: str, 
    model_path: str, 
    dpi: int = 300, 
    target_size: Tuple[int, int] = (1280, 1920),
    vertical_splits: int = 3, 
    horizontal_splits: int = 1
) -> Tuple[List[Image.Image], str]:
    """
    Pipeline xử lý file PDF:
      - Chuyển PDF thành ảnh.
      - Resize.
      - Chia nhỏ ảnh thành sub-images.
      - Phát hiện & xóa đối tượng không mong muốn bằng YOLO.
      - Ghép lại thành ảnh gốc.
    
    Args:
        pdf_path (str): Đường dẫn file PDF đầu vào.
        model_path (str): Đường dẫn model YOLO.
        dpi (int, optional): DPI khi chuyển PDF -> ảnh. Mặc định 300.
        target_size (tuple, optional): Kích thước (width, height) để resize. Mặc định (1280, 1920).
        vertical_splits (int, optional): Số hàng khi chia ảnh. Mặc định 3.
        horizontal_splits (int, optional): Số cột khi chia ảnh. Mặc định 2.
    
    Returns:
        Tuple[List[Image.Image], str]:
            - Danh sách các trang ảnh đã xử lý (PIL Images).
            - Văn bản trích xuất từ toàn bộ PDF (hiện tại để trống vì chưa có OCR).
    """
    # Khởi tạo các processor
    preprocessor = ImagePreprocessor(dpi=dpi, target_size=target_size)
    yolo_processor = YoloProcessor(model_path=model_path)
    # ocr_processor = ImageOCR()
    
    # Chuyển PDF thành danh sách các trang ảnh (PIL Images)
    pages = preprocessor.pdf_to_images(pdf_path)
    final_images = []
    document_text = ""  # Để trống vì chưa tích hợp OCR
    
    # Duyệt qua từng trang
    for page_idx, page in enumerate(pages):
        logger.info(f"Processing page {page_idx + 1}/{len(pages)}")
        
        # a) Tiền xử lý: resize
        processed_page = preprocessor.process_page_to_numpy(page)
        
        # b) Chia nhỏ ảnh thành các sub-images
        sub_imgs = preprocessor.split_image(processed_page, vertical_splits, horizontal_splits)
        
        # c) Áp dụng YOLO song song để phát hiện và xóa đối tượng không mong muốn
        with ThreadPoolExecutor() as executor:
            filled_sub_imgs = list(executor.map(yolo_processor.detect_bounding_boxes, sub_imgs))
        
        # d) Ghép lại các sub-images thành trang ảnh gốc
        merged_page_np = preprocessor.merge_subimages(filled_sub_imgs, vertical_splits, horizontal_splits)
        
        # e) Chuyển từ NumPy BGR sang PIL RGB
        merged_page_pil = Image.fromarray(cv2.cvtColor(merged_page_np, cv2.COLOR_BGR2RGB))
        final_images.append(merged_page_pil)
        
        # f) OCR (chưa tích hợp, để trống)
        # page_text = ocr_processor.ocr_images([merged_page_pil])
        # document_text += page_text + "\n\n"
    
    document_text = document_text.strip()
    return final_images #, document_text

def pdf_processor_pipeline(
    pdf_path: str,
    model_path: str,
    dpi: int = 300,
    target_size: Tuple[int, int] = (1280, 1920),
    vertical_splits: int = 3,
    horizontal_splits: int = 1,
    overlap_ratio: float = 0.1
):
    """
    Pipeline tổng hợp xử lý file PDF:
      - Chuyển PDF thành ảnh, thực hiện tiền xử lý, YOLO và OCR.
      - Xử lý văn bản:
          + Chia văn bản thành các đoạn theo số token theo quy tắc:
              * 700 < token_count <= 1000: chia thành 2 đoạn.
              * 1000 < token_count <= 1500: chia thành 3 đoạn.
              * 1500 < token_count <= 2000: chia thành 4 đoạn.
              * Nếu token_count > 2000: tính số đoạn sao cho mỗi đoạn không quá 500 token.
          + Thêm overlap giữa các đoạn: đoạn trước được nối thêm phần đầu của đoạn sau.
      - Xuất kết quả thành chuỗi JSON với metadata.
      
    Args:
        pdf_path (str): Đường dẫn file PDF.
        model_path (str): Đường dẫn model YOLO.
        dpi (int, optional): DPI khi chuyển PDF -> ảnh.
        target_size (tuple, optional): Kích thước resize ảnh.
        vertical_splits (int, optional): Số hàng chia ảnh.
        horizontal_splits (int, optional): Số cột chia ảnh.
        overlap_ratio (float, optional): Tỷ lệ overlap giữa các đoạn. Mặc định 0.1.
        
    Returns:
        str: Chuỗi JSON chứa các đoạn văn bản (segments) đã xử lý kèm metadata.
    """
    # Xử lý PDF: lấy danh sách ảnh đã xử lý và văn bản trích xuất từ toàn bộ PDF
    images, document_text = image_processor_pipeline(
        pdf_path, model_path, dpi, target_size, vertical_splits, horizontal_splits
    )
    
    # Xử lý văn bản: chia thành các đoạn dựa trên số token
    segments = process_text(document_text)
    # Thêm overlap: mỗi đoạn trước được nối thêm phần đầu của đoạn sau
    overlapped_segments = overlap_segments(segments, overlap_ratio=overlap_ratio)
    
    # Tạo metadata cho file PDF
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    metadata = {
        "file_name": base_name,
        "file_type": ".pdf"
    }
    
    return segments_to_json(overlapped_segments, metadata)
