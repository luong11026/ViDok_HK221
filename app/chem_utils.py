import os
from app.config import Config

def save_compound(user_id, file_name, compound):
    with open(
                os.path.join(Config.CHEM_DIR, "compounds", str(user_id), file_name), \
                "w", encoding="utf-8"
             ) as f:
        f.write(compound)

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class DockingAgent(metaclass=Singleton):
    def __init__(self) -> None:
        pass


    def run(self, user_id, compound):
        pass