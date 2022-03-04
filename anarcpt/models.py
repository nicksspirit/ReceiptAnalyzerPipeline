import datetime as dt
from decimal import Decimal
from typing import Optional
from pydantic import condecimal
from sqlmodel import Field, Relationship, SQLModel


class ReceiptSummary(SQLModel, table=True):
    pk: Optional[int] = Field(default=None, primary_key=True)
    img_id: str
    vendor_name: str = "Unknown"
    receiver_address: str = "Unknown"
    receipt_date: dt.datetime = dt.datetime.today()
    total: Decimal = Decimal(0)
    sub_total: condecimal(max_digits=6, decimal_places=2) = Field(default=0)
    tax_amount: condecimal(max_digits=6, decimal_places=2) = Field(default=0)
    currency: str = "US Dollars"
    line_items: 'list[ReceiptLineItem]' = Relationship(back_populates="receipt")


class ReceiptLineItem(SQLModel, table=True):
    pk: Optional[int] = Field(default=None, primary_key=True)
    img_id: str
    item_name: str = "Unknown"
    price: condecimal(max_digits=6, decimal_places=2) = Field(default=0)
    quantity: int = 1
    receipt_id: Optional[int] = Field(default=None, foreign_key="receiptsummary.pk")
    receipt: Optional[ReceiptSummary] = Relationship(back_populates="line_items")
