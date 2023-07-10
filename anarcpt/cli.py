import re
from argparse import Action
from argparse import ArgumentParser as BaseArgParser
from enum import Enum
from functools import wraps
from typing import (Any, Callable, Generic, NoReturn, Optional, Sequence,
                    TypeVar)

F = TypeVar("F", bound=Callable[..., Any])

TERM_CODE_REGEX = re.compile(r"\[\d{1,2}m")
TERM_COLOR_CODE_REGEX = re.compile(r"(.{2})(?=\[\d{1,2}m)")


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


class ArgumentParser(BaseArgParser):
    @staticmethod
    def _strip_termcodes(msg: str) -> str:
        stripped_msg = TERM_COLOR_CODE_REGEX.sub("", msg)
        fmt_err_msg = TERM_CODE_REGEX.sub(" ", stripped_msg)

        return fmt_err_msg

    @staticmethod
    def cast_as(type_: Callable):
        class _(Action):
            def __call__(self, parser, namespace, values, options_string=None):
                setattr(namespace, self.dest, type_(values))

        return _

    def print_message(self, message: str, is_colored=True):
        if is_colored:
            fmt_err_msg = (
                f"{TermColors.OKBLUE}({self.prog}){TermColors.ENDC} {message}\n"
            )
        else:
            fmt_err_msg = self._strip_termcodes(f"({self.prog}) {message}\n")

        self._print_message(fmt_err_msg)

    def print_error(self, message: str, is_colored=False) -> NoReturn:
        if is_colored:
            fmt_err_msg = (
                f"{TermColors.FAIL}{self.prog}: error: {TermColors.ENDC} {message}\n"
            )
        else:
            fmt_err_msg = self._strip_termcodes(f"{self.prog}: error: {message}\n")

        self.exit(2, fmt_err_msg)

    def enable_subcommands(self):
        self.sub_parser = self.add_subparsers(
            dest="command", title="available commands", metavar="command [options ...]"
        )

    def command(self, *arguments, help: str = "⎼", parents: Optional[Sequence] = None):
        parents_ = [] if parents is None else parents

        if not hasattr(self, "sub_parser") or getattr(self, "sub_parser", None) is None:
            raise AttributeError(
                "Sub parser not found! Did you forget to call `enable_subcommands`?"
            )

        def decorator(func):
            group_store = {}
            func_name = func.__name__.replace("_", "-")
            func_descr = func.__doc__

            cmd_parser = self.sub_parser.add_parser(
                func_name, description=func_descr, help=help, parents=parents_
            )

            @wraps(func)
            def wrapper(kwargs):
                return func(**{"cmd_parser": cmd_parser, **vars(kwargs)})

            for args in arguments:
                cmd_args, cmd_kwargs = args
                if "exclusive_group" in cmd_kwargs:
                    group_key = cmd_kwargs.pop("exclusive_group")
                    is_group_required = cmd_kwargs.pop("group_required", False)

                    if group_key not in group_store:
                        group_store[
                            group_key
                        ] = cmd_parser.add_mutually_exclusive_group(
                            required=is_group_required
                        )

                    group_store[group_key].add_argument(*cmd_args, **cmd_kwargs)
                else:
                    cmd_parser.add_argument(*cmd_args, **cmd_kwargs)

                cmd_parser.set_defaults(func=wrapper)

        return decorator

    @copy_signature(BaseArgParser.add_argument)
    def argument(self, *args, **kwargs):
        return args, kwargs
