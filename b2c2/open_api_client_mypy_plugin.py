"""
This is a plugin that modifies MyPy's AST to
include types that we dynamically generated.

It's just a proof of concept, and there are a
million-and-one edge cases surrounding arguments
and names that I am knowingly ignoring.

However I wanted to experiment with the idea of
strongly typing the interface of a REST API using MyPy.
Lots of Python projects multiply into microservices, and
more often than not, the communication layer is poorly
defined and implemented ad-hoc.

This approach attempts to bridge the gap between rather
restrictive solutions to this problem like Protocol buffers and
more normal Python development practices that tend to involve
metaprogramming.
"""
import inspect

from pydoc import locate
from mypy.plugin import Plugin
from mypy.plugins.common import add_method
from mypy.nodes import Argument, Var

from b2c2.client import OpenAPIClient


def hook(ctx):
    # Limitation: we can't have closures around our classes
    constructed_cls = locate(ctx.cls.fullname)

    if getattr(constructed_cls.Meta, 'abstract', False):
        return

    for method_name, method in constructed_cls.__constructed_methods.items():
        return_type = ctx.api.named_type(
            method.__annotations__['return'].__name__
        )

        self_type = ctx.api.named_type(ctx.cls.name)

        arguments = []
        arg_specification = inspect.getfullargspec(method)
        # Pop the self arg off
        arg_specification.args.pop(0)

        for arg in arg_specification.args:
            arg_type = ctx.api.named_type(
                arg_specification.annotations[arg].__name__
            )

            arg = Argument(
                variable=Var(arg, arg_type),
                type_annotation=arg_type, initializer=None, kind=0
            )

            arguments.append(arg)

        add_method(
            ctx,
            method_name,
            args=arguments,
            return_type=return_type,
            self_type=self_type,
        )


class APIClientPlugin(Plugin):
    def get_base_class_hook(self, fullname: str):
        if fullname == '.'.join([
            OpenAPIClient.__module__, OpenAPIClient.__name__
        ]):
            return hook


def plugin(version: str):
    return APIClientPlugin
