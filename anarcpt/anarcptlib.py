import re
import boto3
import csv
import dateutil.parser as dtparser
import imagehash
from decimal import Decimal
from anarcpt import models
from anarcpt.config import logger
from functools import partial
from pathlib import Path
from PIL import Image
from textractprettyprinter.t_pretty_print_expense import (
    get_string,
    Textract_Expense_Pretty_Print,
    Pretty_Print_Table_Format,
)
from typing import cast

# jmespath
# ExpenseDocuments[].SummaryFields[].[{TypeText: Type.Text, TypeConfidence: Type.Confidence, ValueText: ValueDetection.Text, ValueConfidence: ValueDetection.Confidence}][]
MONEY_REGEX = re.compile(r"(?P<currency>[\£\$\€]{1})?(?P<amount>[,\d]+.?\d*)")

get_summary_expense = partial(
    get_string,
    output_type=[Textract_Expense_Pretty_Print.SUMMARY],
    table_format=Pretty_Print_Table_Format.csv,
)
get_lineitem_expense = partial(
    get_string,
    output_type=[Textract_Expense_Pretty_Print.LINEITEMGROUPS],
    table_format=Pretty_Print_Table_Format.csv,
)


def parse_summary_csv(img_id: str, receipt_summary_csv: str) -> models.ReceiptSummary:
    summary_lines = receipt_summary_csv.splitlines()
    csv_reader = filter(bool, csv.reader(summary_lines))

    # This skips the first row of the CSV file.
    next(csv_reader)

    receipt_summary = models.ReceiptSummary(img_id=img_id)

    try:
        for row in csv_reader:
            row_val = row[1].replace("$", "")

            if "$" in row[1]:
                receipt_summary.currency = "US Dollars"

            if "VENDOR_NAME" in row[0]:
                receipt_summary.vendor_name = row_val
            elif "RECEIVER_ADDRESS" in row[0]:
                receipt_summary.receiver_address = row_val
            elif "INVOICE_RECEIPT_DATE" in row[0]:
                receipt_summary.receipt_date = dtparser.parse(row_val)
            elif "SUBTOTAL" in row[0]:
                receipt_summary.sub_total = Decimal(row_val)
            elif any(val in row[0] for val in ("TOTAL", "Total")):
                receipt_summary.total = Decimal(row_val)
            elif "TAX" in row[0]:
                receipt_summary.tax_amnt = Decimal(row_val)
    except Exception as e:
        logger.exception("Unknown Exception")

    return receipt_summary


def parse_lineitem_csv(img_id: str, lineitem_csv: str) -> list[models.ReceiptLineItem]:
    line_items = []
    lineitem_lines = lineitem_csv.splitlines()
    csv_reader = filter(bool, csv.reader(lineitem_lines))

    try:
        for row in csv_reader:
            # Remove (FieldType) value and trailing spaces
            row_cln = [str.strip(re.sub(r"(\([A-Z]+\))", "", val)) for val in row]

            if match := MONEY_REGEX.match(row_cln[1]):
                price_str = match.group("amount")
            else:
                price_str = 0

            kwargs = {
                "item_name": row_cln[0],
                "price": Decimal(price_str) if row_cln[1] else 0,
                "quantity": int(row_cln[2])
                if 0 <= 2 < len(row_cln) and row_cln[2]
                else 1,
            }
            line_item = models.ReceiptLineItem(img_id=img_id, **kwargs)
            line_items.append(line_item)
    except Exception as e:
        logger.exception("Unknown Exception")

    return line_items


class AnalyzeReceipt:
    def __init__(self, region="us-east-2"):
        self.textract_client = boto3.client("textract", region_name=region)

    @classmethod
    def analyze_local(cls, image_file: Path):
        instance = cls()

        with open(image_file, "rb") as fb:
            image_bytes = fb.read()

        img_id = image_file.stem
        resp = instance.textract_client.analyze_expense(Document={"Bytes": image_bytes})

        resp_dict = cast(dict, resp)

        return instance._analyze_receipt(resp_dict, img_id)

    @classmethod
    def analyze_s3(cls, s3document: str, s3bucket: str = "receipt-image"):
        instance = cls()

        img_id = s3document.replace(".png", "")
        resp = instance.textract_client.analyze_expense(
            Document={"S3Object": {"Bucket": s3bucket, "Name": s3document}}
        )
        resp_dict = cast(dict, resp)

        return instance._analyze_receipt(resp_dict, img_id)

    def _analyze_receipt(self, textract_resp: dict, img_id: str):
        summary_csv = get_summary_expense(textract_json=textract_resp)
        lineitem_csv = get_lineitem_expense(textract_json=textract_resp)

        receipt_summary = parse_summary_csv(img_id, summary_csv)
        receipt_lineitem = parse_lineitem_csv(img_id, lineitem_csv)

        return receipt_summary, receipt_lineitem


def hash_image(image_file: Path, should_rename: bool) -> Path | str:
    if not image_file.exists() or not image_file.is_file():
        raise ValueError(f"{image_file} does not exists.")

    if image_file.suffix not in (".png", ".jpg", ".jpeg"):
        raise ValueError("Image must be either png, jpg or jpeg")

    img_hash = ""

    with Image.open(image_file) as img:
        img_hash = imagehash.average_hash(img)

    if should_rename:
        renamed_img_file = image_file.parent / f"{img_hash}{image_file.suffix}"
        image_file.rename(renamed_img_file)

        return renamed_img_file

    return img_hash
