from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_db: str = "agent_manager"
    postgres_user: str = "agent_user"
    postgres_password: str = "agent_pass"
    postgres_port: int = 5432
    
    agents_path: str = "/app/agents"
    backend_host: str = "backend"
    backend_port: str = "5500"
    
    class Config:
        env_file = ".env"


settings = Settings()
