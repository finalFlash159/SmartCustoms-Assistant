import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple
import logging
# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ImagePreprocessor:
    def __init__(self, dpi: int = 300, target_size: Tuple[int, int] = (1280, 1920)):
        """Khởi tạo tham số xử lý ảnh."""
        self.dpi = dpi
        self.target_size = target_size

    def pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """Chuyển PDF thành danh sách các trang PIL Image."""
        try:
            pages = convert_from_path(pdf_path, dpi=self.dpi)
            logger.info(f"Converted {pdf_path} to {len(pages)} pages")
            return pages
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            return []

    def process_page_to_numpy(self, pil_img: Image.Image) -> np.ndarray:
        """Chuyển PIL Image sang NumPy BGR và resize."""
        img_cv = np.array(pil_img.convert('RGB'))
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
        resized_image = cv2.resize(img_cv, self.target_size, interpolation=cv2.INTER_AREA)
        return resized_image

    def process_pages(self, pages: List[Image.Image]) -> List[np.ndarray]:
        """Xử lý song song các trang ảnh."""
        with ThreadPoolExecutor() as executor:
            processed_pages = list(executor.map(self.process_page_to_numpy, pages))
        return processed_pages

    def split_image(self, image: np.ndarray, vertical_splits: int = 3, horizontal_splits: int = 1) -> List[np.ndarray]:
        """Chia ảnh NumPy thành các sub-images."""
        height, width = image.shape[:2]
        sub_height = height // vertical_splits
        sub_width = width // horizontal_splits

        sub_images = []
        for i in range(vertical_splits):
            for j in range(horizontal_splits):
                sub_img = image[i * sub_height:(i + 1) * sub_height, j * sub_width:(j + 1) * sub_width]
                sub_images.append(sub_img)
        return sub_images

    def merge_subimages(self, sub_images: List[np.ndarray], vertical_splits: int, horizontal_splits: int) -> np.ndarray:
        """Ghép các sub-images NumPy thành ảnh gốc."""
        if not sub_images:
            raise ValueError("Danh sách sub_images rỗng")

        sub_height, sub_width = sub_images[0].shape[:2]
        merged_height = sub_height * vertical_splits
        merged_width = sub_width * horizontal_splits
        merged_image = np.zeros((merged_height, merged_width, 3), dtype=np.uint8)

        index = 0
        for i in range(vertical_splits):
            for j in range(horizontal_splits):
                merged_image[i * sub_height:(i + 1) * sub_height, j * sub_width:(j + 1) * sub_width] = sub_images[index]
                index += 1

        return merged_image