import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

config_file = "/app/config/storage/storage_config.yml"
with open(config_file, "r") as f:
    config = yaml.safe_load(f)

datastore = config["datastore"]
user = datastore["user"]
password = datastore["password"]
hostname = datastore["hostname"]
port = datastore["port"]
database = datastore["db"]

engine = create_engine(f"mysql+pymysql://{user}:{password}@{hostname}:{port}/{database}")

def make_session():
    return sessionmaker(bind=engine)()