from anarcpt import config
from anarcpt import models as M
from sqlmodel import SQLModel, create_engine, Session

sqlite_url = f"sqlite:///{config.DB_NAME}"
engine = create_engine(sqlite_url, echo=config.DB_VERBOSE_OUTPUT)


def insert_receipt(rcpt_summary: M.ReceiptSummary):
    with Session(engine) as sesn:
        sesn.add(rcpt_summary)
        sesn.commit()
