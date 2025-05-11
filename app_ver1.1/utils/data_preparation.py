import json

class DataLoader:
    def __init__(self, json_content, content: str = "content"):
        """
        Khởi tạo DataLoader với nội dung JSON.

        :param json_content: Nội dung JSON dưới dạng string hoặc đã được parse (list/dict).
        :param content: Tên trường chứa văn bản cần trích xuất (mặc định là "content").
        """
        self.content = content
        if isinstance(json_content, str):
            try:
                self.data = json.loads(json_content)
            except json.JSONDecodeError as e:
                raise ValueError("Invalid JSON content") from e
        else:
            self.data = json_content

    def prepare_data_from_json(self):
        """
        Trích xuất danh sách văn bản từ JSON.
        """
        texts = [item[self.content] for item in self.data]
        return texts

    def prepare_metadata_from_json(self):
        """
        Trích xuất metadata từ JSON.
        """
        metadata = [item["metadata"] for item in self.data]
        return metadata
