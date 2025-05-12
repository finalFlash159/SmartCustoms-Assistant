import math
import re
import json
import os
import subprocess
import tempfile
from langchain_community.document_loaders import UnstructuredWordDocumentLoader

# Hàm chuyển đổi .doc sang .docx sử dụng thư mục tạm tự động
def convert_doc_to_docx(doc_path):
    """
    Chuyển đổi file .doc thành .docx bằng LibreOffice.
    Tạo thư mục tạm tự động để lưu file .docx.

    Args:
        doc_path (str): Đường dẫn đến file .doc.

    Returns:
        str: Đường dẫn đến file .docx đã chuyển đổi.

    Raises:
        FileNotFoundError: Nếu file không tồn tại.
        Exception: Nếu có lỗi khi chuyển đổi.
    """
    if not os.path.exists(doc_path):
        raise FileNotFoundError(f"File không tồn tại: {doc_path}")

    # Tạo thư mục tạm để lưu file chuyển đổi
    output_dir = tempfile.mkdtemp(prefix="doc2docx_")
    base_name = os.path.splitext(os.path.basename(doc_path))[0]
    docx_path = os.path.join(output_dir, f"{base_name}.docx")
    print("DEBUG: doc_path =", doc_path)

    try:
        result = subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to", "docx",
                doc_path,
                "--outdir", output_dir
            ],
            check=True,
            capture_output=True, 
            text=True             
        )
        # Kiểm tra log trả về
        print("LibreOffice stdout:", result.stdout)
        print("LibreOffice stderr:", result.stderr)
        return docx_path
    except subprocess.CalledProcessError as e:
        # e.output hoặc e.stderr có thể chứa thông tin lỗi
        print("=== LibreOffice conversion error ===")
        print("Return code:", e.returncode)
        print("Output:", e.output)
        print("Stderr:", e.stderr)
        raise Exception("Lỗi khi chuyển đổi file. Hãy kiểm tra LibreOffice.")

# Hàm đọc file đã được sửa đổi
def read_doc_file(file_path):
    """
    Load a document file and return its content as a string.
    Hỗ trợ cả .doc và .docx.

    Args:
        file_path (str): Path to the document file.

    Returns:
        str: Content of the document file.

    Raises:
        FileNotFoundError: Nếu file không tồn tại.
        Exception: Nếu có lỗi khác khi đọc file.
    """
    try:
        if file_path.endswith('.doc'):
            # Chuyển đổi .doc sang .docx sử dụng thư mục tạm tự động
            docx_path = convert_doc_to_docx(file_path)
            file_path = docx_path  # Cập nhật file_path thành file .docx

        # Đọc file .docx
        loader = UnstructuredWordDocumentLoader(file_path)
        documents = loader.load()
        return documents[0].page_content
    except FileNotFoundError:
        raise FileNotFoundError(f"File không tồn tại: {file_path}")
    except Exception as e:
        raise Exception(f"Lỗi khi đọc file: {str(e)}")

# Các hàm xử lý khác giữ nguyên
def split_document(text: str) -> list[str]:
    pattern = re.compile(
        r'(\n+[ \t]*)'
        r'('
            r'Điều\s+\d+\.|'
            r'\d+\.\s*Bổ\s*sung\s+(?:điều|Điều)|'
            r'\d+\.\s*Khoản\s+\d+\s+(?:Điều|điều)\s+\d+\s+được\s+sửa|'
            r'\d+\.\s*Bổ\s*sung\s+(?:Điều|điều)|'
            r'\d+\.\s*Khoản\/khoản\s+\d+,\s*\d+|'
            r'\d+\.\s*Khoản\s+\d+,\s*khoản\s+\d+|'
            r'\d+\.\s*Điều\s+\d+\s+được\s+sửa|'
            r'\d+\.\s*Bổ\s*sung\s+(?:Điều|điều)|'
            r'Mẫu\s+số|'
            r'Điều\s+\d+\s+được\s+sửa'
        r')'
    )
    new_text = pattern.sub(r'<<<SPLIT>>>\1\2', text)
    parts = new_text.split('<<<SPLIT>>>')
    cleaned_parts = [p.strip() for p in parts if p.strip()]
    return cleaned_parts

def split_segment(segment, num_chunks):
    segment_length = len(segment)
    chunk_size = segment_length // num_chunks
    remainder = segment_length % num_chunks
    
    chunks = []
    start = 0
    for i in range(num_chunks):
        end = start + chunk_size + (1 if i < remainder else 0)
        chunks.append(segment[start:end])
        start = end
    return chunks

def get_num_splits(token_count):
    RANGES = [
        (750, 1), (1500, 2), (2250, 3), (3000, 4), (3750, 5),
        (4500, 6), (5250, 7), (6000, 8), (6750, 9), (7500, 10),
        (8250, 11), (9000, 12), (9750, 13), (10500, 14), (11250, 15), 
        (12000, 16), (12750, 17), (13500, 18), (14250, 19), (15000, 20), 
    ]
    if token_count > 15000:
        return math.ceil(token_count / 1000)
    for upper_bound, splits in RANGES:
        if token_count <= upper_bound:
            return splits
    return 1

def segment_processor(list_segments):
    new_list = []
    for segment in list_segments:
        token_count = len(segment)
        n_splits = get_num_splits(token_count)
        if n_splits == 1:
            new_list.append(segment)
        else:
            new_list.extend(split_segment(segment, n_splits))
    return new_list

def overlap_segments(segments, overlap_ratio=0.20):
    if len(segments) <= 1:
        return segments
    
    overlapped_segments = []
    for i in range(len(segments) - 1):
        current_segment = segments[i]
        next_segment = segments[i + 1]
        overlap_size = math.ceil(len(current_segment) * overlap_ratio)
        overlap_part = current_segment[-overlap_size:]
        new_segment = overlap_part + next_segment
        overlapped_segments.append(current_segment)
        if i == len(segments) - 2:
            overlapped_segments.append(new_segment)
    if len(segments) > 2:
        overlapped_segments.append(segments[-1])
    return overlapped_segments

def save_segments_to_json(segments, metadata=None):
    data = []
    for seg in segments:
        data.append({
            "content": seg,
            "metadata": metadata
        })
    return json.dumps(data, ensure_ascii=False, indent=4)

def doc_processor_pipeline(doc_path):
    """
    Pipeline xử lý văn bản từ file Word (doc hoặc docx) thành các đoạn văn bản và lưu thành file JSON.

    :param doc_path: Đường dẫn đến file Word (doc hoặc docx) cần xử lý.

    Raises:
        FileNotFoundError: Nếu file đầu vào không tồn tại.
        PermissionError: Nếu không có quyền ghi vào thư mục đầu ra.
        Exception: Nếu có lỗi khác trong quá trình xử lý.
    """
    # Đọc nội dung từ file Word
    doc_content = read_doc_file(doc_path)
    
    # Chia văn bản thành các đoạn
    segments = split_document(doc_content)
    processed_segments = segment_processor(segments)
    overlapped_segments = overlap_segments(processed_segments)

    # Metadata cho từng segment
    base_name = os.path.splitext(os.path.basename(doc_path))[0]
    file_type = '.docx' if doc_path.endswith('.docx') else '.doc'
    metadata = {
        "file_name": base_name,
        "file_type": file_type
    }

    # Lưu các đoạn văn bản thành file JSON, kèm metadata
    doc_filename = f"{base_name}.json"
    return save_segments_to_json(overlapped_segments, metadata=metadata)
