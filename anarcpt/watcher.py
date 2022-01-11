import time
import typer
import shutil
import anarcpt.anarcptlib as arlib
from anarcpt.config import logger
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
    IMG_RECIEPT_REGEX = [r"^.*Scan_[0-9]+"]

    def __init__(self, target_dir: Path = None):
        super().__init__(self.IMG_RECIEPT_REGEX)

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
            except Exception:
                pass
            else:
                break

        # Check if all of the file is available to be read
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
            shutil.move(str(hashed_file), self.target_dir)


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
