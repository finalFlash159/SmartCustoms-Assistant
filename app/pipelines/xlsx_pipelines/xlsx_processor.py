import logging
import pandas as pd
import os
import mysql.connector
import re
import math
import numpy as np
import datetime

logger = logging.getLogger(__name__)

# Các hàm không thay đổi giữ nguyên như trong mã gốc
def xlsx_to_df(file_path: str) -> pd.DataFrame:
    logger.info(f"[xlsx_to_df] Đang đọc file Excel: {file_path}")
    df = pd.read_excel(file_path, engine='openpyxl')
    df = df.copy(deep=True)
    logger.info(f"[xlsx_to_df] Đọc xong file Excel, shape={df.shape}")
    return df

def remove_unwanted_chars(text: str) -> str:
    if not isinstance(text, str):
        return text
    while text.startswith("#&"):
        text = text[2:].lstrip()
    while text.endswith("#&"):
        text = text[:-2].rstrip()
    text = text.replace("'", "")
    text = text.replace("#&", ",")
    return text

def clean_special_chars_in_str_cols(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("[clean_special_chars_in_str_cols] Bắt đầu xử lý cột kiểu chuỗi.")
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]):
            df.loc[:, col] = df[col].apply(remove_unwanted_chars)
    logger.info("[clean_special_chars_in_str_cols] Xong xử lý cột kiểu chuỗi.")
    return df

def process_supplier_name(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = re.sub(r"(?<!\., )\bLTD\b", r"., LTD", text)
    text = re.sub(r"\bLTD\b(?!\.)(?=\s|$)", r"LTD.", text)
    text = re.sub(r"\s*\.\s*", ".", text)
    text = re.sub(r"\s*,\s*", ",", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r",{2,}", ",", text)
    text = re.sub(r"([.,]+)", lambda m: ".," if '.' in m.group(0) and ',' in m.group(0) else m.group(0), text)
    return text

def process_supplier_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Nhà cung cấp" in df.columns:
        logger.info("[process_supplier_column] Bắt đầu xử lý cột 'Nhà cung cấp'.")
        df.loc[:, "Nhà cung cấp"] = df["Nhà cung cấp"].astype(str).apply(process_supplier_name)
        logger.info("[process_supplier_column] Xong xử lý cột 'Nhà cung cấp'.")
    return df

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("[remove_duplicates] Bắt đầu loại bỏ dòng trùng lặp.")
    before = len(df)
    df = df.drop_duplicates(keep="first")
    after = len(df)
    logger.info(f"[remove_duplicates] Đã loại bỏ {before - after} dòng trùng lặp. Còn {after} dòng.")
    df = df.copy(deep=True)
    return df

def df_processor(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"[df_processor] Bắt đầu xử lý fillna, parse 'Ngày'. shape={df.shape}")
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df.loc[:, col] = df[col].fillna(value=np.nan)
        else:
            df.loc[:, col] = df[col].fillna("")
    if 'Ngày' in df.columns:
        df.loc[:, 'Ngày'] = pd.to_datetime(df['Ngày'], errors='coerce')
    tz_cols = df.select_dtypes(include=["datetimetz"]).columns
    for col in tz_cols:
        df.loc[:, col] = df[col].dt.tz_localize(None)
    for col in df.select_dtypes(include=["object"]).columns:
        if col != "Ngày":
            df.loc[:, col] = df[col].apply(
                lambda x: x.strftime("%Y-%m-%d") if isinstance(x, (pd.Timestamp, datetime.date)) and not pd.isnull(x) else x
            )
    df = clean_special_chars_in_str_cols(df)
    logger.info(f"[df_processor] Xong xử lý fillna, parse 'Ngày'. shape={df.shape}")
    return df

def create_file_name_column(df: pd.DataFrame, file_path: str) -> pd.DataFrame:
    logger.info("[create_file_name_column] Bắt đầu thêm cột 'file_name'.")
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    df.loc[:, "file_name"] = base_name
    logger.info("[create_file_name_column] Đã thêm cột 'file_name'.")
    return df

def default_val(val, numeric: bool = False):
    if numeric:
        if isinstance(val, str):
            val = val.replace(",", ".")
        if pd.isna(val) or val == "" or val == "NaN":
            return None
        else:
            return val
    else:
        if val is None or val == "" or (isinstance(val, float) and math.isnan(val)):
            return ""
        else:
            return val

# Hàm mới để xác định giá trị cột 'Tình trạng'
def determine_status_column(df: pd.DataFrame) -> str:
    """
    Xác định giá trị cho cột 'Trạng thái' dựa trên tên các cột.
    """
    column_names = [col.lower() for col in df.columns]
    if any('nhập' in col or 'nhap' in col for col in column_names):
        return 'Nhập'
    elif any('xuất' in col or 'xuat' in col for col in column_names):
        return 'Xuất'
    else:
        return ''

# Hàm pipeline chính với các thay đổi
def xlsx_processor_pipeline(file_path: str, db_config: dict):
    logger.info(f"[xlsx_processor_pipeline] Bắt đầu, file_path={file_path}")
    df = xlsx_to_df(file_path)
    logger.info(f"[xlsx_processor_pipeline] DataFrame ban đầu shape={df.shape}")

    # Thêm cột 'Tình trạng'
    status_value = determine_status_column(df)
    df['Trạng thái'] = status_value

    # Đổi tên các cột theo thứ tự
    if len(df.columns) < 13:
        raise ValueError("DataFrame có ít hơn 13 cột, không thể đổi tên.")
    new_column_names = [
        'Ngày', 'Nhà cung cấp', 'Hs code', 'Tên hàng', 'Lượng', 'Đơn vị tính',
        'Tên nước xuất xứ', 'Điều kiện giao hàng', 'Thuế suất XNK', 'Thuế suất TTĐB',
        'Thuế suất VAT', 'Thuế suất tự vệ', 'Thuế suất BVMT'
    ]
    # Đổi tên 13 cột đầu tiên, giữ nguyên các cột còn lại (bao gồm 'Tình trạng')
    df.columns = new_column_names + list(df.columns[13:])

    # Tiếp tục xử lý như cũ
    processed_df = df_processor(df)
    logger.info(f"[xlsx_processor_pipeline] Sau df_processor shape={processed_df.shape}")

    processed_df = remove_duplicates(processed_df)
    logger.info(f"[xlsx_processor_pipeline] Sau remove_duplicates shape={processed_df.shape}")

    processed_df = create_file_name_column(processed_df, file_path)
    processed_df = process_supplier_column(processed_df)
    logger.info(f"[xlsx_processor_pipeline] Sau process_supplier_column shape={processed_df.shape}")

    store_dataframe_in_mysql(processed_df, db_config)
    logger.info("[xlsx_processor_pipeline] Hoàn thành pipeline.")

# Hàm lưu vào MySQL với cột 'Trạng thái' được thêm vào
def store_dataframe_in_mysql(df: pd.DataFrame, db_config: dict, table_name: str = "import_data"):
    logger.info("[store_dataframe_in_mysql] Bắt đầu insert vào MySQL.")
    try:
        conn = mysql.connector.connect(**db_config)
        logger.info("[store_dataframe_in_mysql] Kết nối MySQL thành công.")
        
        cursor = conn.cursor()

        insert_query = f"""
            INSERT INTO {table_name} (
                Ngay,
                NhaCungCap,
                HsCode,
                TenHang,
                Luong,
                DonViTinh,
                TenNuocXuatXu,
                DieuKienGiaoHang,
                ThueSuatXNK,
                ThueSuatTTDB,
                ThueSuatVAT,
                ThueSuatTuVe,
                ThueSuatBVMT,
                TinhTrang,
                file_name
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        row_count = len(df)
        logger.info(f"[store_dataframe_in_mysql] Số dòng cần insert: {row_count}")

        for idx, row in df.iterrows():
            ngay_value = row.get("Ngày")
            if pd.isnull(ngay_value):
                ngay_value = None
            else:
                ngay_value = ngay_value.date()

            data_tuple = (
                ngay_value,
                default_val(row.get("Nhà cung cấp", "NaN")),
                default_val(row.get("Hs code", "NaN")),
                default_val(row.get("Tên hàng", "NaN")),
                default_val(row.get("Lượng", "NaN"), numeric=True),
                default_val(row.get("Đơn vị tính", "NaN")),
                default_val(row.get("Tên nước xuất xứ", "NaN")),
                default_val(row.get("Điều kiện giao hàng", "NaN")),
                default_val(row.get("Thuế suất XNK", "NaN"), numeric=True),
                default_val(row.get("Thuế suất TTĐB", "NaN"), numeric=True),
                default_val(row.get("Thuế suất VAT", "NaN"), numeric=True),
                default_val(row.get("Thuế suất tự vệ", "NaN"), numeric=True),
                default_val(row.get("Thuế suất BVMT", "NaN"), numeric=True),
                default_val(row.get("Trạng thái", "NaN")),
                default_val(row.get("file_name", "NaN"))
            )
            logger.info(f"Data tuple for row {idx}: {data_tuple}")
            cursor.execute(insert_query, data_tuple)
            if (idx + 1) % 100 == 0:
                logger.info(f"[store_dataframe_in_mysql] Đã insert {idx+1} / {row_count} dòng...")

        logger.info("[store_dataframe_in_mysql] Tất cả dòng đã insert xong. Đang commit...")
        conn.commit()
        logger.info("[store_dataframe_in_mysql] Commit thành công.")
        cursor.close()
        conn.close()
        logger.info(f"[store_dataframe_in_mysql] Đã lưu dữ liệu vào bảng `{table_name}` thành công!")
    except Exception as e:
        logger.error(f"Lỗi khi lưu dữ liệu vào MySQL: {e}")
        raise