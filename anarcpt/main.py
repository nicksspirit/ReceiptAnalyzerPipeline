import queue
import tempfile
import threading
from pathlib import Path
from pprint import pprint

from sqlmodel import SQLModel

import anarcpt.anarcptlib as arlib
import anarcpt.db as db
import anarcpt.watcher as wch
from anarcpt.cli import ArgumentParser
from anarcpt.exceptions import unpack_exc
from anarcpt.watcher import EventAction

S3Key = str
S3Bucket = str
S3Document = tuple[S3Key, S3Bucket]

cli = ArgumentParser(prog="anarcpt")
cli.enable_subcommands()


cli.add_argument(
    "--init-db", action="store_true", help="Create a sqlite database and create tables"
)


@cli.command(
    cli.argument(
        "image_path",
        metavar="IMAGE ...",
        nargs="?",
        type=Path,
        help="Path to image of receipt.",
    ),
    cli.argument(
        "--rename",
        "-r",
        dest="should_rename",
        help="Rename image file with hash.",
        action="store_false",
    ),
    help="Create hash of an image.",
)
def hash_image(image_path: Path, should_rename: bool, **meta_args):
    """Generate a unique hash signature of a given image."""

    cmd_parser: ArgumentParser = meta_args["cmd_parser"]

    if image_path is None:
        cmd_parser.print_usage()
        cmd_parser.print_error("The path to image is required. ")

    try:
        hash_val = arlib.hash_image(image_path)

        if should_rename:
            renamed_img_path = image_path.parent / f"{hash_val}{image_path.suffix}"
            image_path.rename(renamed_img_path)

    except ValueError as e:
        _, exc_msg = unpack_exc(e)

        cmd_parser.print_error(exc_msg)
    else:
        cmd_parser.print_message(str(hash_val))


@cli.command(
    cli.argument(
        "image_path",
        metavar="IMAGE ...",
        nargs="?",
        type=Path,
        help="Path to image of receipt.",
        exclusive_group="a",
        group_required=True,
    ),
    cli.argument(
        "--s3doc-key-bucket",
        "-s3",
        metavar=("KEY", "BUCKET"),
        dest="key_bucket",
        nargs=2,
        action=cli.cast_as(tuple),
        exclusive_group="a",
        help="S3 document key & bucket",
    ),
)
def analyze(image_path: Path, key_bucket: S3Document, **meta_args):
    """
    Analyze image of receipt using AWS Textract APIs.
    Displays a summary of receipt as well as any line items.
    """
    analyze_receipt = arlib.AnalyzeReceipt()

    if image_path:
        receipt_summary = analyze_receipt.analyze_from_local(image_path)
    else:
        s3document_key, s3document_bucket = key_bucket
        receipt_summary= analyze_receipt.analyze_from_s3(
            s3document_key, s3document_bucket
        )

    pprint(receipt_summary.dict(), compact=True)


@cli.command(
    cli.argument(
        "watch_dir_path",
        metavar="WATCH_DIR ...",
        type=Path,
        help="Directory of image receipts to watch.",
    ),
    cli.argument(
        "--staging-dir",
        "-stg",
        type=Path,
        help="Directory that stages hashed images for upload to s3.",
    ),
    cli.argument(
        "--queue-size", "-s", default=10, help="Size of queue for background job."
    ),
    cli.argument(
        "--pause",
        "-p",
        default=5,
        dest="pause_for",
        help="How long to pause the watcher in secs.",
    ),
)
def watch(
    watch_dir_path: Path,
    staging_dir: Path,
    queue_size: int,
    pause_for: int,
    **meta_args,
):
    """
    Watch a directory for images created or  modified,
    generate hash signature of the image and move the image to s3.
    """
    temp_dir = None

    if not watch_dir_path.exists() or not watch_dir_path.is_dir():
        cli.print_error(f"{watch_dir_path} does not exists.")

    if staging_dir:
        if not staging_dir.exists() or not staging_dir.is_dir():
            cli.print_error(f"{staging_dir} does not exists.")

        if watch_dir_path == staging_dir:
            cli.print_error("Staging directory can not be the same as watch directory!")
    else:
        temp_dir = tempfile.TemporaryDirectory(suffix=cli.prog)
        staging_dir = Path(temp_dir.name)

    try:
        dir_to_watch = str(watch_dir_path.absolute())
        dir_rcpt_watch = str(staging_dir.absolute())

        db_queue = queue.Queue(queue_size)
        hash_handler = wch.ImageHashHandler(staging_dir)
        db_handler = wch.ReceiptAnalyzerHandler(db_queue)

        db_worker = threading.Thread(
            name="db-receipt-worker",
            target=wch.ReceiptAnalyzerHandler.write_receipt_to_db,
            args=(db_queue,),
        )
        db_worker.daemon = True
        db_worker.start()

        cli.print_message(f"Watching {watch_dir_path} for newly scanned receipts...")
        cli.print_message(f"Watching {staging_dir} for hashed receipts...")

        wch.Watcher(
            [
                EventAction(dir_to_watch, hash_handler),
                EventAction(dir_rcpt_watch, db_handler),
            ],
            pause_for=pause_for,
        ).run()
    finally:
        if temp_dir:
            temp_dir.cleanup()


if __name__ == "__main__":
    args = cli.parse_args()

    if args.init_db:
        SQLModel.metadata.create_all(db.engine)
        cli.print_message("Done")
    elif args.command is not None:
        args.func(args)
    else:
        cli.print_help()
