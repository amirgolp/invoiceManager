import mongoengine as me
from data.config import AppConfig


class DatabaseConnection:

    def __init__(self, config: AppConfig = None):
        self.config = config

    def connect(self):
        try:
            me.connect(
                db=self.config.database.db_name,
                username=self.config.database.username,
                password=self.config.database.password.get_secret_value(),
                host=self.config.database.host
            )
            print("Database connection successful.")
        except me.ConnectionError as e:
            print(f"Database connection error: {e}")
