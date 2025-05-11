from pydantic_settings import BaseSettings

class Config(BaseSettings):
    # ===== LangSmith =====
    LANGSMITH_TRACING: bool = True
    LANGSMITH_ENDPOINT: str = ""
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = ""

    # ===== Qdrant =====
    QDRANT_COLLECTION_NAME: str = "chatbot_embeddings"
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    SEARCH_THRESHOLD: float = 0.4

    # ===== OpenAI =====
    OPENAI_API_KEY: str = ""
    TEMPERATURE: float = 0
    CHUNK_SIZE: int = 1000
    MAX_RETRIES: int = 5


    # ===== Model Configs =====
    GENERATE_MODEL_NAME: str | None = None
    EMBEDDING_MODEL_NAME: str | None = None
    OCR_MODEL_NAME: str | None = None
    YOLO_MODEL_PATH: str | None = None
    REANKER_MODEL_PATH: str | None = None

    # ===== Coordinator =====
    COORDINATOR_MODEL_NAME: str | None = None
    COORDINATOR_TEMPERATURE: float = 0

    # ===== Cohere ======
    COHERE_API_KEY: str = ""


    # ===== Objects =====
    NUM_SEARCH_ENGINES: int = 1
    NUM_RERANKERS: int = 1
    NUM_VECTOR_STORES: int = 1
    NUM_MONGO_DBS: int = 2
    NUM_COORDINATORS: int = 1

    # ===== MongoDB =====
    # ===== MongoDB Field Mapping =====
    # Ánh xạ từ tên cột tiếng Việt sang tên trường MongoDB (English snake_case)
    MONGODB_FIELD_MAP: dict = {
        'Ngày': 'ngay',
        'Nhà cung cấp': 'nha_cung_cap',
        'Hs code': 'hs_code',
        'Tên hàng': 'ten_hang',
        'Loại hình': 'loai_hinh',
        'Đơn vị tính': 'don_vi_tinh',
        'Tên nước xuất xứ': 'xuat_xu',
        'Điều kiện giao hàng': 'dieu_kien_giao_hang',
        'Thuế suất XNK': 'thue_suat_xnk',
        'Thuế suất TTĐB': 'thue_suat_ttdb',
        'Thuế suất VAT': 'thue_suat_vat',
        'Thuế suất tự vệ': 'thue_suat_tu_ve',
        'Thuế suất BVMT': 'thue_suat_bvmt',
        'Trạng thái': 'tinh_trang',
        'file_name': 'file_name',
        'Từ khóa xuất xứ': 'xuat_xu_keywords' 
    }

    MONGODB_URI: str = ""
    MONGODB_DATABASE: str = ""
    MONGODB_COLLECTION: str = ""

    MONGODB_CONNECTION_POOL_CONFIG: dict = {
        "maxPoolSize": 10,
        "minPoolSize": 1,
        "maxIdleTimeMS": 30000,
        "waitQueueTimeoutMS": 5000,
        "retryWrites": True,
        "retryReads": True
    }

    AGGREGATE_PIPELINE_GENERATOR_CONFIG: dict = {
        "fuzzy_search": {
            "maxEdits": 2,
            "prefixLength": 3,
            "maxExpansions": 20,
            "score_threshold": 0.5,
            "pre_filter_threshold": 0.1
        },
        "result_limit": 20,
        "fields_to_project": [
            "ngay",
            "nha_cung_cap",
            "hs_code",
            "ten_hang",
            "loai_hinh",
            "don_vi_tinh",
            "xuat_xu",
            "dieu_kien_giao_hang",
            "thue_suat_xnk",
            "thue_suat_ttdb",
            "thue_suat_vat",
            "thue_suat_tu_ve",
            "thue_suat_bvmt",
            "tinh_trang"
        ]
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
