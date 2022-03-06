import datetime as dt
from typing import Optional, List
from pydantic import condecimal
from sqlmodel import Field, Relationship, SQLModel, Column, JSON


class ReceiptSummary(SQLModel, table=True):
    pk: Optional[int] = Field(default=None, primary_key=True)
    img_id: str
    vendor_name: str = "Unknown"
    receiver_address: Optional[str] = None
    receipt_date: dt.datetime = dt.datetime.today()
    total: condecimal(max_digits=6, decimal_places=2) = Field(default=0)
    sub_total: condecimal(max_digits=6, decimal_places=2) = Field(default=0)
    tax_amount: condecimal(max_digits=6, decimal_places=2) = Field(default=0)
    currency: str = "US Dollars"
    other_data: dict = Field(default={}, sa_column=Column(JSON))
    line_items: List["ReceiptLineItem"] = Relationship(back_populates="receipt")

    class Config:
        arbitrary_types_allowed = True


class ReceiptLineItem(SQLModel, table=True):
    pk: Optional[int] = Field(default=None, primary_key=True)
    img_id: str
    item_name: str = "Unknown"
    price: condecimal(max_digits=6, decimal_places=2) = Field(default=0)
    quantity: int = 1
    receipt_id: Optional[int] = Field(default=None, foreign_key="receiptsummary.pk")
    receipt: Optional[ReceiptSummary] = Relationship(back_populates="line_items")


__all__ = [
    "ReceiptSummary",
    "ReceiptLineItem"
]
