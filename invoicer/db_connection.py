from mongoengine import connect
import yaml


def get_mongo_uri(config_filepath: str):
    with open(config_filepath, "r") as file:
        config = yaml.safe_load(file)
    return config['database']['uri'], config['database']['db_name']


def connect_to_db(config_filepath: str):
    uri, db_name = get_mongo_uri(config_filepath)
    connect(db=db_name, host=uri)
