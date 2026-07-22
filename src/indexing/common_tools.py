
import logging
import os
import glob
from typing import Any, Dict
import yaml
#import sqlalchemy as db


# load config
def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

# create db connection
def create_db_connection(db_path: str):
    engine = db.create_engine(f'sqlite:///{db_path}')
    connection = engine.connect()
    return connection

# connect to pcloud
def connect_to_pcloud(username: str, password: str):
    # Placeholder for pCloud connection logic
    pass
