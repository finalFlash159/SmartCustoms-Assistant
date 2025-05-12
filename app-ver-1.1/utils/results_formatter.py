# hs_code_formatter.py

import random
from typing import Optional, List, Dict
from datetime import datetime
from prompts.constants import RECOMMENDATION_FIELD_MAP
from prompts.suggestion_templates import get_suggestion_templates, get_support_templates, get_fallback_templates

class ResultsFormatter:
    """
    Class để định dạng thông tin HS code thành Markdown.
    
    - Nếu TinhTrang là "nhập": hiển thị tất cả các thông tin trừ thông tin về Lượng và Đơn vị tính.
    - Nếu TinhTrang là "xuất": hiển thị tất cả các thông tin trừ thông tin về Nhà cung cấp, Lượng và Đơn vị tính.
    """

    def clean_field(self, value: Optional[str], field_name: str) -> str:
        """
        Chuẩn hóa giá trị chuỗi.
        Nếu value là None hoặc rỗng thì trả về thông báo "không có thông tin về <field_name>".
        """
        if value is None or str(value).strip() == "":
            return f"không có thông tin về {field_name}"
        return str(value).strip()

    def format_tax(self, val) -> str:
        """
        Định dạng thông tin thuế. Nếu không hợp lệ thì trả về thông báo mặc định.
        """
        try:
            num = float(val)
            return f"{num:.2f}%" if num >= 0 else "KCT"
        except (TypeError, ValueError):
            return "KCT"
        
    
    def get_field_recommendations(self, used_fields: List[str], total_results: int) -> str:
            """
            Tạo gợi ý về các trường người dùng có thể thêm vào truy vấn để cải thiện kết quả tìm kiếm
            
            Args:
                used_fields: Danh sách tên trường MongoDB đã được sử dụng
                total_results: Tổng số kết quả tìm kiếm
                
            Returns:
                str: Chuỗi Markdown chứa gợi ý về các trường có thể thêm
            """
            
            # Tất cả trường trong map
            all_fields = set(RECOMMENDATION_FIELD_MAP.keys())
            
            # Tìm các trường chưa được sử dụng
            missing_fields = [field for field in all_fields if field not in used_fields]
            
            # Nếu không có trường nào bị thiếu, không đưa ra gợi ý
            if not missing_fields:
                return ""
            
            # Chuyển đổi tên trường MongoDB sang tên hiển thị tiếng Việt
            missing_field_names = [RECOMMENDATION_FIELD_MAP.get(field, field) for field in missing_fields]

            formatted_fields = ', '.join([f'**{field}**' for field in missing_field_names])
            
            # Lấy các mẫu từ file suggestion_templates.py
            suggestion_templates = get_suggestion_templates()
            support_templates = get_support_templates()
            
            # Chọn ngẫu nhiên một mẫu gợi ý và một câu hỗ trợ
            suggestion_template = random.choice(suggestion_templates)
            support_template = random.choice(support_templates)
            
            # Điền trường vào mẫu gợi ý
            suggestion = suggestion_template.format(fields=formatted_fields) +'\n' + support_template
            
            return suggestion 


    def format_record(self, record: Dict) -> str:
        """
        Định dạng một bản ghi HS code thành chuỗi Markdown.
        
        Args:
            record (dict): Một bản ghi chứa các trường từ MongoDB
                           
        Returns:
            str: Chuỗi định dạng Markdown.
        """
        # Chuyển key từ MongoDB sang tên hiển thị
        record_display = {
            'TenHang': record.get('ten_hang'),
            'HsCode': record.get('hs_code'),
            'NhaCungCap': record.get('nha_cung_cap'),
            'TinhTrang': record.get('tinh_trang'),
            'Ngay': record.get('ngay'),
            'LoaiHinh': record.get('loai_hinh'),
            'DonViTinh': record.get('don_vi_tinh'),
            'TenNuocXuatXu': record.get('xuat_xu'),
            'DieuKienGiaoHang': record.get('dieu_kien_giao_hang'),
            'ThueSuatXNK': record.get('thue_suat_xnk'),
            'ThueSuatTTDB': record.get('thue_suat_ttdb'),
            'ThueSuatVAT': record.get('thue_suat_vat'),
            'ThueSuatTuVe': record.get('thue_suat_tu_ve'),
            'ThueSuatBVMT': record.get('thue_suat_bvmt')
        }
        
        # Xử lý ngày
        ngay = record_display['Ngay']
        if isinstance(ngay, str):
            try:
                ngay_obj = datetime.fromisoformat(ngay.rstrip('Z'))
                ngay_str = ngay_obj.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                ngay_str = "không có thông tin về ngày"
        elif hasattr(ngay, "strftime"):
            ngay_str = ngay.strftime("%Y-%m-%d")
        else:
            ngay_str = "không có thông tin về ngày"
        
        # Các trường bắt buộc
        ten_hang = self.clean_field(record_display['TenHang'], "tên hàng")
        hs_code = self.clean_field(record_display['HsCode'], "mã HS")
        tinh_trang = self.clean_field(record_display['TinhTrang'], "tình trạng")
        nuoc_xuat = self.clean_field(record_display['TenNuocXuatXu'], "nước xuất xứ")
        dieu_kien = self.clean_field(record_display['DieuKienGiaoHang'], "điều kiện giao hàng")
        xnk = self.format_tax(record_display['ThueSuatXNK'])
        ttdb = self.format_tax(record_display['ThueSuatTTDB'])
        vat = self.format_tax(record_display['ThueSuatVAT'])
        tuve = self.format_tax(record_display['ThueSuatTuVe'])
        
        # Xử lý riêng cho ThueSuatBVMT
        bvmt_value = record_display['ThueSuatBVMT']
        try:
            bvmt_num = float(bvmt_value)
            bvmt = "CT" if bvmt_num >= 0 else "KCT"
        except (TypeError, ValueError):
            bvmt = "KCT"
        
        lines = []
        lines.append(f"**Ngày:** {ngay_str}")
        lines.append(f"- **Tên hàng:** {ten_hang}")
        lines.append(f"- **Mã HS:** {hs_code}")
        lines.append(f"- **Trạng thái:** {tinh_trang}")
        lines.append(f"- **Nước xuất xứ:** {nuoc_xuat}")
        lines.append(f"- **Điều kiện giao hàng:** {dieu_kien}")
        lines.append(f"- **Thuế suất XNK:** {xnk}; **TTĐB:** {ttdb}; **VAT:** {vat}; **Thuế suất tự vệ:** {tuve}; **BVMT:** {bvmt}")
        
        # Kiểm tra dựa trên TinhTrang
        if tinh_trang.lower() == "nhập":
            # Nếu là nhập, hiển thị thông tin Nhà cung cấp (chèn vào sau Mã HS)
            nha_cung_cap = self.clean_field(record_display['NhaCungCap'], "nhà cung cấp")
            lines.insert(3, f"- **Nhà cung cấp:** {nha_cung_cap}")
            # Bỏ qua thông tin Lượng và Đơn vị tính
        elif tinh_trang.lower() == "xuất":
            # Nếu là xuất, bỏ qua thông tin Nhà cung cấp, Lượng và Đơn vị tính
            pass
        else:
            # Với các trường hợp khác, hiển thị thêm thông tin Lượng và Đơn vị tính cùng với Nhà cung cấp
            nha_cung_cap = self.clean_field(record_display['NhaCungCap'], "nhà cung cấp")
            loai_hinh = self.clean_field(record_display['LoaiHinh'], "loại hình")
            don_vi = self.clean_field(record_display['DonViTinh'], "đơn vị tính")
            lines.insert(3, f"- **Nhà cung cấp:** {nha_cung_cap}")
            lines.append(f"- **Loại hình:** {loai_hinh}")
            lines.append(f"- **Đơn vị tính:** {don_vi}")
        
        return "\n".join(lines)

    def format_records(self, records: List[Dict], num_results: int = 5, used_fields: List[str] = None) -> str:
        """
        Định dạng danh sách bản ghi thành chuỗi Markdown, mỗi bản ghi được ngăn cách bởi một dòng phân cách.
        Bao gồm gợi ý về các trường có thể thêm để cải thiện kết quả tìm kiếm.
        
        Args:
            records (List[Dict]): Danh sách các bản ghi.
            num_results (int): Số lượng kết quả tối đa để hiển thị.
            used_fields (List[str]): Danh sách tên trường MongoDB đã được sử dụng
            
        Returns:
            str: Chuỗi Markdown đã được định dạng.
        """

        # Nếu không có kết quả
        if not records:
            fallback_templates = get_fallback_templates()
            return random.choice(fallback_templates)
    
        # Giới hạn số lượng kết quả
        limited_records = records[:num_results]
        
        
        # Định dạng từng bản ghi
        formatted_list = [self.format_record(r) for r in limited_records]
        result_text = "\n\n---\n\n".join(formatted_list)
        
        
        result_text += self.get_field_recommendations(used_fields, num_results)
        
        return result_text
    