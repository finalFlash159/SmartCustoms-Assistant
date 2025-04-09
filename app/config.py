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
    AGENT_MODEL_NAME: str | None = None
    AGENT_TEMPERATURE: float = 0

    # ===== Model Configs =====
    GENERATE_MODEL_NAME: str | None = None
    EMBEDDING_MODEL_NAME: str | None = None
    OCR_MODEL_NAME: str | None = None
    YOLO_MODEL_PATH: str | None = None
    REANKER_MODEL_PATH: str | None = None

    # ===== Cohere ======
    COHERE_API_KEY: str = ""

    # ===== MySQL ======
    backend_host: str | None = None
    backend_user: str | None = None
    backend_password: str | None = None
    backend_databasse: str | None = None
    backend_user_pure: bool = True 
    backend_port: int = 3306 


    # ===== Objects =====
    NUM_AGENTS: int = 10
    NUM_SEARCH_ENGINES: int = 6
    NUM_RERANKERS: int = 6


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
