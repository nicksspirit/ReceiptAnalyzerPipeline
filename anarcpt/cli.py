import argparse
import re
from pprint import pprint
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Generic, NoReturn, TypeVar

import anarcpt.anarcptlib as arlib
from anarcpt.exceptions import unpack_exc

TERM_CODE_REGEX = r"\[\d{1,2}m"
TERM_COLOR_CODE_REGEX = r"(.{2})(?=\[\d{1,2}m)"

S3Key, S3Bucket = str, str
S3Document = tuple[S3Key, S3Bucket]
F = TypeVar("F", bound=Callable[..., Any])


class copy_signature(Generic[F]):  # noqa
    def __init__(self, target: F) -> None:
        ...

    def __call__(self, wrapped: Callable[..., Any]) -> F:  # type: ignore
        return wrapped  # type: ignore


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return str.__str__(self)


class TermColors(StrEnum):
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class CustomArgParser(argparse.ArgumentParser):
    @staticmethod
    def _strip_termcodes(msg: str) -> str:
        stripped_msg = re.sub(TERM_COLOR_CODE_REGEX, "", msg)
        fmt_err_msg = re.sub(TERM_CODE_REGEX, " ", stripped_msg)

        return fmt_err_msg

    def print_message(self, message: str, is_colored=True):
        msg = f"({self.prog}) {message}\n"

        if is_colored:
            fmt_err_msg = TermColors.OKBLUE + msg + TermColors.ENDC
        else:
            fmt_err_msg = self._strip_termcodes(msg)

        self._print_message(fmt_err_msg)

    def print_error(self, message: str, is_colored=False) -> NoReturn:
        err_msg = f"{self.prog}: error: {message}\n"

        if is_colored:
            fmt_err_msg = TermColors.FAIL + err_msg + TermColors.ENDC
        else:
            fmt_err_msg = self._strip_termcodes(err_msg)

        self.exit(2, fmt_err_msg)


def collect_as(type):
    class _(argparse.Action):
        def __call__(self, parser, namespace, values, options_string=None):
            setattr(namespace, self.dest, type(values))

    return _


cli = CustomArgParser(prog="anarcpt")
sub_parsers = cli.add_subparsers(
    dest="command", title="available commands", metavar="command [options ...]"
)


@copy_signature(cli.add_argument)
def argument(*args, **kwargs):
    return args, kwargs


def command(*arguments, help: str = "⎼", parent=sub_parsers):
    def decorator(func):
        group_store = {}
        func_name = func.__name__.replace("_", "-")
        func_descr = func.__doc__

        cmd_parser = parent.add_parser(func_name, description=func_descr, help=help)

        @wraps(func)
        def wrapper(kwargs):
            return func(**{"cmd_parser": cmd_parser, **vars(kwargs)})

        for args in arguments:
            cmd_args, cmd_kwargs = args

            if "exclusive_group" in cmd_kwargs:
                group_key = cmd_kwargs.pop("exclusive_group")

                if group_key not in group_store:
                    group_store[group_key] = cmd_parser.add_mutually_exclusive_group()

                group_store[group_key].add_argument(*cmd_args, **cmd_kwargs)
            else:
                cmd_parser.add_argument(*cmd_args, **cmd_kwargs)
            cmd_parser.set_defaults(func=wrapper)

    return decorator


@command(
    argument(
        "image_path",
        metavar="IMAGE ...",
        nargs="?",
        type=Path,
        help="Path to image of receipt.",
    ),
    argument(
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

    cmd_parser: CustomArgParser = meta_args["cmd_parser"]

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


@command(
    argument(
        "image_path",
        metavar="IMAGE ...",
        nargs="?",
        type=Path,
        help="Path to image of receipt.",
        exclusive_group="a",
    ),
    argument(
        "--s3doc-key-bucket",
        "-s3",
        metavar=("KEY", "BUCKET"),
        dest="key_bucket",
        nargs=2,
        action=collect_as(tuple),
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
        receipt_summary, _ = analyze_receipt.analyze_from_s3(
            s3document_key, s3document_bucket
        )

    pprint(receipt_summary.dict(), compact=True)


if __name__ == "__main__":
    args = cli.parse_args()

    if args.command is None:
        cli.print_help()
    else:
        args.func(args)
