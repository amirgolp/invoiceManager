import yaml


def load_config(config_filepath):
    with open(config_filepath, "r") as file:
        config = yaml.safe_load(file)
    return config
