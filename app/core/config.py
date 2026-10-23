
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    aws_region: str = "ap-south-1"
    cognito_client_id: str = ""
    cognito_client_secret: str = ""
    cognito_user_pool_id: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
