from anarcpt.anarcptlib import AnalyzeReceipt


def lambda_handler(event: dict, context):
    s3bucket = event["detail"]["bucket"]["name"]
    s3document = event["detail"]["object"]["key"]

    analyze_receipt = AnalyzeReceipt()

    receipt_summary, receipt_lineitems = analyze_receipt.analyze_s3(
        s3document, s3bucket
    )

    import pprint as pp

    pp.pprint(receipt_summary)
    pp.pprint(receipt_lineitems, indent=2)
