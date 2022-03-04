from anarcpt import config
from anarcpt import models as M
from sqlmodel import SQLModel, create_engine

sqlite_url = f"sqlite:///{config.DB_NAME}"
engine = create_engine(sqlite_url, echo=config.DB_VERBOSE_OUTPUT)
