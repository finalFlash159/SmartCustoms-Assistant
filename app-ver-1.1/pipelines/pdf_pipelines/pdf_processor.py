import cv2
from PIL import Image
import numpy as np 
from typing import List, Tuple
import math
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

from .image_processor import ImagePreprocessor
from .yolo_detector import YoloProcessor 
from llms.gpt_ocr import ImageOCR


import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- HS code extraction ---

def extract_hs_code(ocr_text: str) -> str:
    """
    Hậu xử lý văn bản OCR để extract HS code và chèn vào đầu đoạn.
    - Tìm các pattern kiểu '7019.90', '7019.90.00' hoặc '12.34.56.78', cho phép khoảng trắng quanh dấu chấm.
    - Loại bỏ khoảng trắng trong các mã khớp.
    - Ưu tiên mã có nhiều nhóm nhất, sau đó là mã dài nhất.
    - Trả về mã chuẩn định dạng 'xxxx.xx[.xx]', 'xx.xx.xx.xx' hoặc None.
    """
    # Regex cho phép khoảng trắng quanh dấu chấm
    hs_pattern = r"\b(?:\d{4}\s*\.\s*\d{2}(?:\s*\.\s*\d{2})?|\d{2}(?:\s*\.\s*\d{2}){3})\b"
    matches = re.findall(hs_pattern, ocr_text)
    if not matches:
        return None
    
    # Loại bỏ khoảng trắng trong các mã khớp
    cleaned_matches = [''.join(m.split()) for m in matches]
    
    # Chọn mã có nhiều dấu chấm nhất (tương ứng nhiều nhóm), sau đó là mã dài nhất
    hs_code = max(cleaned_matches, key=lambda x: (x.count('.'), len(x)))
    return hs_code

# --- Chunking & prefix pipeline ---

digit_to_word = {
    "0": "KHÔNG",
    "1": "MỘT",
    "2": "HAI",
    "3": "BA",
    "4": "BỐN",
    "5": "NĂM",
    "6": "SÁU",
    "7": "BẢY",
    "8": "TÁM",
    "9": "CHÍN",
    ".": ".",
}

def number_to_words(number: str) -> str:
    return " ".join(digit_to_word.get(c, c) for c in number)

def chunk_and_prefix(text: str, overlap_ratio: float = 0.10) -> List[str]:
    words = text.split()
    total_words = len(words)

    # Tính số chunk, mỗi chunk khoảng 200 từ
    chunk_count = max(1, math.floor(total_words / 200))
    chunk_size = math.ceil(total_words / chunk_count)

    # Tạo chunk thô
    raw_chunks = [
        " ".join(words[i * chunk_size : min((i + 1) * chunk_size, total_words)])
        for i in range(chunk_count)
    ]

    # Thêm overlap
    overlapped = []
    for i in range(len(raw_chunks) - 1):
        cur = raw_chunks[i].split()
        nxt = raw_chunks[i + 1].split()
        ov_n = int(len(nxt) * overlap_ratio)
        overlapped.append(" ".join(cur + nxt[:ov_n]))
    overlapped.append(raw_chunks[-1])

    # Trích mã HS
    hs_code = extract_hs_code(text)
    hs_code_in_words = number_to_words(hs_code) if hs_code else None

    # Tạo các chunk có header
    prefixed = []
    for idx, chunk in enumerate(overlapped):
        header_lines = []
        if hs_code:
            header_lines.append(f"[KẾT QUẢ PHÂN TÍCH PHÂN LOẠI - MÃ {hs_code} - {hs_code_in_words}]\n")
        header_lines.append(f"[CHUNK_INDEX: {idx + 1}/{len(overlapped)}]")
        header = "\n".join(header_lines)
        prefixed.append(f"{header}\n{chunk}")

    return prefixed

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
    ocr_processor = ImageOCR()
    
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
        page_text = ocr_processor.ocr_images([merged_page_pil])
        document_text += page_text + "\n\n"
    
    document_text = document_text.strip()
    return final_images, document_text

def pdf_processor_pipeline(
    pdf_path: str,
    model_path: str,
    dpi: int = 300,
    target_size: Tuple[int, int] = (1280, 1920),
    vertical_splits: int = 3,
    horizontal_splits: int = 1,
    overlap_ratio: float = 0.15
) -> str:
    """
    - Xử lý PDF thành ảnh, YOLO và OCR
    - Chunking bằng chunk_and_prefix
    - Trả về JSON segments kèm metadata
    """
    # 1) Ảnh + OCR
    preprocessor = ImagePreprocessor(dpi=dpi, target_size=target_size)
    yolo_processor = YoloProcessor(model_path=model_path)
    ocr_processor = ImageOCR()

    pages = preprocessor.pdf_to_images(pdf_path)
    document_text = ""
    for idx, page in enumerate(pages):
        logger.info(f"Processing page {idx+1}/{len(pages)}")
        proc_np = preprocessor.process_page_to_numpy(page)
        subs = preprocessor.split_image(proc_np, vertical_splits, horizontal_splits)
        with ThreadPoolExecutor() as exe:
            cleaned = list(exe.map(yolo_processor.detect_bounding_boxes, subs))
        merged = preprocessor.merge_subimages(cleaned, vertical_splits, horizontal_splits)
        pil_img = Image.fromarray(cv2.cvtColor(merged, cv2.COLOR_BGR2RGB))
        document_text += ocr_processor.ocr_images([pil_img]) + "\n"
    document_text = document_text.strip()

    # print(document_text)

    # 2) Chunk & prefix HS
    segments = chunk_and_prefix(document_text, overlap_ratio=overlap_ratio)

    # 3) Output JSON with metadata
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    metadata = {"file_name": base, "file_type": ".pdf"}
    data = [{"content": seg, "metadata": metadata} for seg in segments]
    return json.dumps(data, ensure_ascii=False, indent=4)
