from anarcpt import config
from anarcpt import models as M
from sqlmodel import create_engine, Session

sqlite_url = f"sqlite:///{config.DB_NAME}"
engine = create_engine(sqlite_url, echo=config.DB_VERBOSE_OUTPUT)


def insert_receipt(rcpt_summaries: list[M.ReceiptSummary]):
    with Session(engine) as sesn:
        for rcpt_summary in rcpt_summaries:
            sesn.add(rcpt_summary)
        sesn.commit()
