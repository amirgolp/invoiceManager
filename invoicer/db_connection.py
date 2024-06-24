import mongoengine as me
from pydantic import BaseModel, SecretStr
import yaml


class DatabaseConfig(BaseModel):
    db_name: str
    username: str
    password: SecretStr
    host: str


class DatabaseConnection:

    def __init__(self, config: DatabaseConfig = None):
        self.config = config

    def connect(self):
        try:
            me.connect(
                db=self.config.db_name,
                username=self.config.username,
                password=self.config.password.get_secret_value(),
                host=self.config.host
            )
            print("Database connection successful.")
        except me.ConnectionError as e:
            print(f"Database connection error: {e}")

    @classmethod
    def load_config(cls, config_file: str) -> DatabaseConfig:
        with open(config_file, 'r') as file:
            config_dict = yaml.safe_load(file)['database']
            return DatabaseConfig(**config_dict)
