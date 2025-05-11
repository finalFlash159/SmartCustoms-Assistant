import cv2
import base64
import logging
import openai
import pytesseract

from PIL import Image
import numpy as np
from config import Config
from io import BytesIO

from prompts.ocr_prompts import get_ocr_system_message, get_ocr_user_instruction

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

config = Config()

class ImageOCR:
    def __init__(self, 
                 api_key: str = None, 
                 model_name: str = None, 
                 max_tokens: int = 15000):
        """
        Khởi tạo lớp OCR sử dụng GPT-4o thông qua OpenAI API.

        Args:
            api_key (str): API key của OpenAI.
            model_name (str): Tên mô hình. Nếu không truyền, sẽ lấy từ cấu hình.
            max_tokens (int): Số token tối đa cho phản hồi.
        """
        self.api_key = api_key if api_key is not None else config.OPENAI_API_KEY
        self.model_name = model_name if model_name is not None else config.OCR_MODEL_NAME
        self.max_tokens = max_tokens
        
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        
        self.system_message = get_ocr_system_message()
        self.user_text_instruction = get_ocr_user_instruction()

    def image_to_base64(self, image: Image.Image) -> str:
        """
        Chuyển đổi đối tượng PIL Image thành chuỗi base64 (định dạng PNG).
        """
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return img_str
    
    def ocr_images(self, images: list) -> str:
        """
        Nhận diện và trích xuất văn bản từ danh sách ảnh bằng GPT-4o thông qua OpenAI API.
        Nếu số từ OCR được từ GPT-4o ít hơn 50, sẽ sử dụng Tesseract để trích xuất văn bản từ trang đó.
        
        Args:
            images (list): Danh sách các đối tượng PIL Image.
        
        Returns:
            str: Văn bản được trích xuất từ tất cả ảnh, kết hợp thành một document.
        """
        full_text = ""
        
        for image in images:
            img_str = self.image_to_base64(image)
            
            user_content = [
                {"type": "text", "text": self.user_text_instruction},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
            ]
            
            messages = [
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": user_content}
            ]
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=self.max_tokens
                )
                ocr_text = response.choices[0].message.content
            except Exception as e:
                ocr_text = ""
                logger.error(f"Lỗi khi sử dụng GPT-4o: {e}")
            
            # Kiểm tra số từ được trích xuất
            word_count = len(ocr_text.split())
            if word_count < 20:
                logger.info("Số từ OCR từ GPT-4o dưới 20, chuyển sang sử dụng Tesseract.")
                # Chuyển đổi ảnh PIL thành NumPy với định dạng BGR
                img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                try:
                    # Sử dụng Tesseract cho văn bản tiếng Việt
                    tesseract_text = pytesseract.image_to_string(img_cv, lang='vie')
                except Exception as te:
                    logger.error(f"Lỗi khi sử dụng Tesseract: {te}")
                    tesseract_text = ""
                ocr_text = tesseract_text
            
            full_text += ocr_text + "\n\n"
        
        return full_text.strip()
