from argparse import Namespace
from distutils.util import strtobool
from typing import Type, Tuple, Any

from flask import request
from werkzeug.exceptions import BadRequest

from tools import HTTP_METHOD


class ArgLocation:
    QUERY = 'args'
    FORM = 'form'
    JSON = 'json'

    @classmethod
    def values(cls):
        return cls.__dict__.values()


class Argument:
    name: str
    location: str = None
    choices: list = []
    type: Type = str
    required: bool = False
    default: Any = None

    def __init__(self, name, **options):
        self.name = name
        self._parse_options(**options)

    def __repr__(self) -> str:
        return '<Argument "{name}">'.format(name=self.name)

    def _parse_options(self, **options):
        for opt, value in options.items():
            if opt == 'location' and value not in ArgLocation.values():
                raise BadRequest(f'Invalid argument location : {value!r}')
            setattr(self, opt, value)

        if self.location is None:
            if request.method == HTTP_METHOD.GET:
                self.location = ArgLocation.QUERY
            else:
                self.location = ArgLocation.JSON


class RequestParser:
    arguments: dict

    def __init__(self):
        self.raw_args = dict()
        self.parsed_args = dict()

    def add_argument(self, name: str, **options):
        if self.raw_args.get(name) is not None:
            raise BadRequest(f'Argument {name!r} has bean already declared')

        self.raw_args[name] = options

    def parse_args(self, include_only: Tuple[str] = tuple(), ignore_required: bool = False) -> Namespace:
        """
        Parse the current request object for the given args.
        Various data location can be set to the specific argument

        :param Tuple[str] include_only: tuple of argument names. If given will only parse the args
            for the current parser. Implemented to use the same parser for multiple http-methods
        :param bool ignore_required: Will ignore required flag for the arguments.
        :return: argparse.Namespace for the convenience
        """

        errors = []
        request_args = dict()

        for raw_arg, options in self.raw_args.items():
            arg = Argument(raw_arg, **options)
            request_args[arg.name] = arg

        for arg in request_args.values():

            if include_only and arg.name not in include_only:
                continue

            query = getattr(request, arg.location)
            if query is None:
                raise BadRequest(f'Arg {arg.name} were not parsed from the request. '
                                 f'Expected location: {arg.location!r}')

            parsed_value = query.get(arg.name)

            if arg.default is not None and parsed_value is None:
                parsed_value = arg.default

            self.parsed_args[arg.name] = parsed_value

            if hasattr(arg, 'choices') and parsed_value not in arg.choices:
                errors.append(f'Bad choice - {parsed_value!r} for {arg.type!r} argument {arg.name!r}. '
                              f'Available choices - {list(arg.choices)}')
                continue

            if parsed_value is None:
                if arg.required and not ignore_required:
                    errors.append(f'Missed required argument: {arg.name}')
                continue

            try:
                if arg.type is bool:
                    self.parsed_args[arg.name] = bool(strtobool(parsed_value))
                elif arg.type is list:
                    if self.parsed_args.get(arg.name):
                        self.parsed_args[arg.name].append(parsed_value)
                    else:
                        self.parsed_args[arg.name] = [parsed_value]
                else:
                    self.parsed_args[arg.name] = arg.type(parsed_value)
            except ValueError:
                errors.append(f'Argument {arg.name!r} expected type {arg.type!r}, got value {parsed_value!r}')
                continue

        if errors:
            raise BadRequest(', '.join(errors))

        return Namespace(**self.parsed_args)

    def has_passed_args(self, *args_to_check: str) -> bool:
        """Check that specific args were passed and have not null value"""

        if not self.parsed_args:
            return False
        return all(self.parsed_args.get(arg_name) is not None for arg_name in args_to_check)
