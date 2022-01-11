from anarcpt.anarcptlib import AnayzeReceipt


def lambda_handler(event: dict, context):
    s3bucket = event["detail"]["bucket"]["name"]
    s3document = event["detail"]["object"]["key"]

    analyze_receipt = AnayzeReceipt()

    receipt_summary, reciept_lineitems = analyze_receipt.analyze_s3(
        s3document, s3bucket
    )

    import pprint as pp

    pp.pprint(receipt_summary)
    pp.pprint(reciept_lineitems, indent=2)
