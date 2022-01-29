import typer
import anarcpt.anarcptlib as arlib
import anarcpt.watcher as wch
from anarcpt.watcher import EventAction
from pathlib import Path
from sqlmodel import SQLModel, create_engine

cli = typer.Typer(add_completion=False)

dbcli = typer.Typer()
cli.add_typer(dbcli, name="db")


# @cli.command()
# def hash_image(
#     image_file: Path = typer.Argument(..., help="Path to image of reciept"),
#     should_rename: bool = typer.Option(
#         False, "--rename", "-r", help="Rename image file with hash"
#     ),
# ):
#     """
#     Generate a unique hash signature of a given image.
#     """

#     try:
#         hash_val = arlib.hash_image(image_file, should_rename)
#     except ValueError as e:
#         _, exc_msg = arlib.unpack_exc(e)

#         raise typer.BadParameter(exc_msg)
#     else:
#         typer.echo(hash_val)


@cli.command()
def analyze(
    image_file: Path = typer.Option(
        None, "--image-file", "-f", help="Path to image of reciept"
    ),
    s3document_key: str = typer.Option(
        None, "--s3doc-key", "-s3key", help="S3 document key"
    ),
    s3document_bucket: str = typer.Option(
        "receipt-image", "--s3doc-bucket", "-s3bucket", help="S3 bucket"
    ),
):
    """
    Analyze image of receipt using AWS Textract APIs.
    Displays a summary of receipt as well as any line items.
    """

    if all((image_file, s3document_key, s3document_bucket)):
        raise typer.BadParameter(
            "analyze either a local image reciept or one stored on s3 not both"
        )

    analyze_receipt = arlib.AnayzeReceipt()

    if image_file:
        receipt_summary, reciept_lineitems = analyze_receipt.analyze_local(image_file)
    else:
        receipt_summary, reciept_lineitems = analyze_receipt.analyze_s3(
            s3document_key, s3document_bucket
        )

    import pprint as pp

    pp.pprint(receipt_summary)
    pp.pprint(reciept_lineitems, indent=2)


@cli.command()
def watch(
    watch_dir_path: Path = typer.Argument(
        ..., help="Directory of image reciepts to watch."
    ),
    watch_s3dir_path: Path = typer.Argument(
        ..., help="Directory to watch and upload to s3."
    ),
    pause_for: int = typer.Option(
        5, "--pause", "-p", help="How long to pause the watcher in secs."
    ),
):
    """
    Watch a directory for images created & modified,
    generate hash signature of the image and move the image to s3
    """

    if not watch_dir_path.exists() or not watch_dir_path.is_dir():
        raise typer.BadParameter(f"{watch_dir_path} does not exists.")

    if not watch_s3dir_path.exists() or not watch_s3dir_path.is_dir():
        raise typer.BadParameter(f"{watch_s3dir_path} does not exists.")

    dir_to_watch = str(watch_dir_path.absolute())
    dir_upload_s3 = str(watch_s3dir_path.absolute())

    hash_handler = wch.ImageHashHandler(watch_s3dir_path)
    s3_handler = wch.MoveToS3Handler()

    typer.echo(f"Watching {watch_dir_path} for newly scanned reciepts...")
    typer.echo(f"Watching {watch_s3dir_path} for hashed reciepts...")

    wch.Watcher(
        [
            EventAction(dir_to_watch, hash_handler),
            EventAction(dir_upload_s3, s3_handler),
        ]
    ).run()


@dbcli.command()
def init():
    """
    Create a sqlite database and create tables
    """
    sqlite_file_name = "analyzed_receipts.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"

    engine = create_engine(sqlite_url, echo=True)

    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    cli()
