import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from decimal import Decimal


@dataclass
class ReceiptSummary:
    img_id: str
    vendor_name: str = "Unknown"
    receiver_address: str = "Unknown"
    receipt_date: dt.datetime = dt.datetime.today()
    total: Decimal = Decimal(0)
    sub_total: Decimal = Decimal(0)
    tax_amnt: Decimal = Decimal(0)
    currency: str = "US Dollars"


@dataclass
class ReceiptLineItem:
    img_id: str
    item_name: str = "Unknown"
    price: Decimal = Decimal(0)
    quantity: int = 1
