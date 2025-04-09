# hs_code_formatter.py

from typing import Optional, List, Dict
from datetime import datetime

class HSCodeFormatter:
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

    def format_record(self, record: Dict, display_date: bool = True) -> str:
        """
        Định dạng một bản ghi HS code thành chuỗi Markdown.
        
        Args:
            record (dict): Một bản ghi chứa các trường: TenHang, HsCode, NhaCungCap, TinhTrang, Ngay, 
                           Luong, DonViTinh, TenNuocXuatXu, DieuKienGiaoHang, ThueSuatXNK, ThueSuatTTDB,
                           ThueSuatVAT, ThueSuatTuVe, ThueSuatBVMT.
            display_date (bool): Nếu True, hiển thị thông tin ngày; nếu False, bỏ qua thông tin ngày.
                           
        Returns:
            str: Chuỗi định dạng Markdown.
        """
        # Xử lý ngày, nếu hiển thị
        ngay = record.get('Ngay')
        if display_date:
            if ngay and hasattr(ngay, "strftime"):
                ngay_str = ngay.strftime("%Y-%m-%d")
            else:
                ngay_str = "không có thông tin về ngày"
        else:
            ngay_str = None
        
        # Các trường bắt buộc
        ten_hang = self.clean_field(record.get('TenHang'), "tên hàng")
        hs_code = self.clean_field(record.get('HsCode'), "mã HS")
        tinh_trang = self.clean_field(record.get('TinhTrang'), "tình trạng")
        nuoc_xuat = self.clean_field(record.get('TenNuocXuatXu'), "nước xuất xứ")
        dieu_kien = self.clean_field(record.get('DieuKienGiaoHang'), "điều kiện giao hàng")
        xnk = self.format_tax(record.get('ThueSuatXNK'))
        ttdb = self.format_tax(record.get('ThueSuatTTDB'))
        vat = self.format_tax(record.get('ThueSuatVAT'))
        tuve = self.format_tax(record.get('ThueSuatTuVe'))
        
        # Xử lý riêng cho ThueSuatBVMT
        bvmt_value = record.get('ThueSuatBVMT')
        try:
            bvmt_num = float(bvmt_value)
            bvmt = "CT" if bvmt_num >= 0 else "KCT"
        except (TypeError, ValueError):
            bvmt = "KCT"
        
        lines = []
        if display_date:
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
            nha_cung_cap = self.clean_field(record.get('NhaCungCap'), "nhà cung cấp")
            lines.insert(3, f"- **Nhà cung cấp:** {nha_cung_cap}")
            # Bỏ qua thông tin Lượng và Đơn vị tính
        elif tinh_trang.lower() == "xuất":
            # Nếu là xuất, bỏ qua thông tin Nhà cung cấp, Lượng và Đơn vị tính
            pass
        else:
            # Với các trường hợp khác, hiển thị thêm thông tin Lượng và Đơn vị tính cùng với Nhà cung cấp
            nha_cung_cap = self.clean_field(record.get('NhaCungCap'), "nhà cung cấp")
            luong = self.clean_field(record.get('Luong'), "số lượng")
            don_vi = self.clean_field(record.get('DonViTinh'), "đơn vị tính")
            lines.insert(3, f"- **Nhà cung cấp:** {nha_cung_cap}")
            lines.append(f"- **Số lượng:** {luong} {don_vi}")
        
        return "\n".join(lines)

    def format_records(self, records: List[Dict], display_date: bool = True, package_type: str = "max_package") -> str:
        """
        Định dạng danh sách bản ghi thành chuỗi Markdown, mỗi bản ghi được ngăn cách bởi một dòng phân cách.
        
        Args:
            records (List[Dict]): Danh sách các bản ghi.
            display_date (bool): Nếu True, hiển thị thông tin ngày; nếu False, bỏ qua.
            package_type (str): Loại gói người dùng. Nếu là "max_package" thì trả về tối đa 5 bản ghi, 
                                nếu là "trial_package" hoặc "vip_package" thì trả về tối đa 2 bản ghi.
            
        Returns:
            str: Chuỗi Markdown đã được định dạng.
        """
        # Áp dụng giới hạn số bản ghi dựa trên package_type
        if package_type == "max_package":
            limit = 5
        elif package_type in ["trial_package", "vip_package"]:
            limit = 2
        else:
            limit = len(records)
        
        limited_records = records[:limit]
        formatted_list = [self.format_record(r, display_date=display_date) for r in limited_records]
        return "\n\n---\n\n".join(formatted_list)
