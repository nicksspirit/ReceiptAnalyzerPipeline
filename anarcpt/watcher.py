import time
import typer
import shutil
import anarcpt.anarcptlib as arlib
from anarcpt.config import logger
from anarcpt.exceptions import unpack_exc
import anarcpt.db as db
from queue import Queue
from fs_s3fs import S3FS
from fs.move import move_file
from pathlib import Path
from typing import NamedTuple
from watchdog.observers import Observer
from watchdog.events import (
    RegexMatchingEventHandler,
    FileSystemEventHandler,
    FileSystemEvent,
)


class EventAction(NamedTuple):
    src_dir: str
    event_handler: FileSystemEventHandler


class Watcher:
    def __init__(self, event_actions: list[EventAction], pause_for: int = 5):
        self._event_observer = Observer()
        self.pause_for = pause_for
        self.event_actions = event_actions

    def run(self):
        self.start()

        try:
            while True:
                time.sleep(self.pause_for)
        except KeyboardInterrupt:
            self.stop()
            raise typer.Abort()

    def start(self):
        self._schedule()
        self._event_observer.start()

    def stop(self):
        self._event_observer.stop()
        self._event_observer.join()

    def _schedule(self):
        for action in self.event_actions:
            self._event_observer.schedule(
                action.event_handler, action.src_dir, recursive=False
            )


class ImageHashHandler(RegexMatchingEventHandler):
    IMG_RECEIPT_REGEX = [r"^.*Scan_[0-9]+", r'^.*?\.png$']

    def __init__(self, target_dir: Path = None):
        super().__init__(self.IMG_RECEIPT_REGEX)

        self.target_dir = target_dir

    def on_created(self, event):
        if event.is_directory:
            return

        src_path = Path(event.src_path)

        # Check if another program is using file
        while True:
            try:
                with open(src_path, "r"):
                    pass
            except Exception as ex:
                ex_name, ex_msg = unpack_exc(ex)
                logger.error(f"{ex_name}: {ex_msg}")
            else:
                break

        # Check if all the file is available to be read
        file_size = -1

        while file_size != src_path.stat().st_size:
            file_size = src_path.stat().st_size
            time.sleep(1)

        hashed_file = arlib.hash_image(src_path, True)

        logger.info(
            f"Hashed {src_path.name} -> "
            f"{hashed_file.name if isinstance(hashed_file, Path) else hashed_file}"
        )

        if self.target_dir:
            try:
                shutil.move(str(hashed_file), self.target_dir)
            except shutil.Error as ex:
                _, ex_msg = unpack_exc(ex)
                logger.warning(ex_msg)


class MoveToS3Handler(FileSystemEventHandler):
    def __init__(self, s3bucket: str = "receipt-image"):
        self.s3fs = S3FS(s3bucket)

    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return

        src_path = Path(event.src_path)
        src_dir = str(src_path.parent)
        src_file = str(src_path.name)

        move_file(src_dir, src_file, self.s3fs, src_file)

        logger.info(f"Moved {src_path} -> {self.s3fs}")


class ReceiptAnalyzerHandler(FileSystemEventHandler):

    def __init__(self, db_queue: Queue):
        self.analyze_receipt = arlib.AnalyzeReceipt()
        self.queue_count = 0
        self.queue = db_queue

    def on_created(self, event):
        if event.is_directory:
            return

        local_img_path = Path(event.src_path)
        try:
            receipt_summary = self.analyze_receipt.analyze_from_local(local_img_path)

            logger.debug(f"{self.queue_count=}")
            if self.queue_count >= self.queue.maxsize-1:
                logger.debug("Queue is full sending sentinel value.")
                self.queue.put_nowait(None)
                self.queue_count = 0

            logger.debug(f"Adding receipt {receipt_summary.img_id} to queue.")
            self.queue.put(receipt_summary, block=True)
            self.queue_count += 1
        except Exception as e:
            ex_name, ex_msg = unpack_exc(e)
            logger.error(f"({local_img_path.name}) {ex_name}: {ex_msg}")

    @staticmethod
    def write_receipt_to_db(queue: Queue):
        while True:
            if not queue.empty():
                continue

            receipt_summaries = list(iter(queue.get, None))
            logger.debug(f"{len(receipt_summaries)=}")
            db.insert_receipt(receipt_summaries)
