from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_hostname: str
    database_port: int
    database_name: str
    database_username: str
    database_password: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    google_api_key: str
    gemini_model:str="models/gemini-3.5-flash"
    gemini_embedding_model:str = "models/gemini-embedding-001"
    chroma_persist_dir: str = "chroma_db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
