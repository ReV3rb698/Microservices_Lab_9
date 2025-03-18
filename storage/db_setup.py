from db_class import Base
from db import engine

def create_tables():
    Base.metadata.create_all(engine)
    print("All tables created.")

def drop_tables():
    Base.metadata.drop_all(engine)
    print("All tables dropped.")

if __name__ == "__main__":
    drop_tables()
    create_tables()

    