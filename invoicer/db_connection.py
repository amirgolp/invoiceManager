import mongoengine as me
from pydantic import BaseModel, SecretStr


class DatabaseConfig(BaseModel):
    db_name: str
    username: str
    password: SecretStr
    host: str


class DatabaseConnection:

    def __init__(self, config: DatabaseConfig):
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
