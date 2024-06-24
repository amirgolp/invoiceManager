from pydantic import BaseModel, SecretStr
import yaml


class DatabaseConfig(BaseModel):
    db_name: str
    username: str
    password: SecretStr
    host: str


class GeminiConfig(BaseModel):
    api_url: str
    access_token: SecretStr


class AppConfig(BaseModel):
    database: DatabaseConfig
    gemini: GeminiConfig


def load_config(config_file: str) -> AppConfig:
    with open(config_file, 'r') as file:
        config_dict = yaml.safe_load(file)
        return AppConfig(**config_dict)
