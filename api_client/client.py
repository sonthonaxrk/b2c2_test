from typing import Any, Generator, NamedTuple
from requests import Session
from urllib.parse import urljoin


class Rule(NamedTuple):
    method: str
    api_path: str
    response: Any
    body: Any


class BaseAPIClientMeta(type):
    """
    Metaclass for creating API clients.

    The reason I am using a metaclass for this rather
    than overriding the __init__ method of a BaseAPIClient
    is because the resulting class is clearer to introspect.

    When the class is defined, the metaclass will create all
    of the methods with the typing information. This means that
    a developer will not have to instantiate the class to see
    what methods it has.

    But more importantly this separation of concerns between
    class creation and instantiation into two stages, that is,
    metaclass and class, allows us to easily write a MyPy plug-in
    that 'statically' analyse the usage of our API clients.

    This allows us to use MyPy to verify that we are using
    external APIs correctly!
    """

    @staticmethod
    def _generate_method_name(rule: Rule) -> str:
        """
        Creates a method name for the Endpoint
        """
        return '{}_{}'.format(
            rule.method.lower(),
            rule.api_path.strip('/').replace('/', '_')
        )

    @staticmethod
    def _enumerate_definition(
        specification: dict
    ) -> Generator[Rule, None, None]:
        """
        Iterates through the pseudo-openapi specification
        """
        for api_path, spec in specification.items():
            for method, value in spec.items():
                yield Rule(
                    method,
                    api_path,
                    value.get('response'),
                    value.get('body')
                )

    @staticmethod
    def _wrap_request_in_annotations(rule: Rule):
        """
        Creates a new closure the calls the BaseAPIClient's
        client request function.

        The purpose of this is to create a new function
        for each method we find in the definition and
        add the important typing data onto the function.
        """
        if rule.body:
            def wrapped(
                self,
                body: rule.body,  # type: ignore
                **kwargs
            ) -> rule.response:  # type: ignore
                return self._make_request(
                    rule,
                    body,
                    **kwargs,
                )
        else:
            def wrapped(  # type: ignore
                self,
                **kwargs,
            ) -> rule.response:  # type: ignore
                return self._make_request(
                    rule,
                    **kwargs
                )

        return wrapped

    def __new__(cls, name, bases, dct):
        # Only use for subclasses
        Meta = dct['Meta']

        if getattr(Meta, 'abstract', False):
            return super().__new__(cls, name, bases, dct)

        constructed_methods = {}
        # This is for mypy.  It tells our plugin what methods
        # we have created dynamically
        dct['__constructed_methods'] = constructed_methods

        for rule in cls._enumerate_definition(Meta.definition):
            # Add the *functions* to the class dict (functions
            # are later bound)
            method_name = cls._generate_method_name(rule)
            method = cls._wrap_request_in_annotations(rule)
            dct[method_name] = cls._wrap_request_in_annotations(rule)
            constructed_methods[method_name] = method

        # This is the same the built in function type(name, bases, dict)
        return super().__new__(cls, name, bases, dct)


class BaseAPIClient(metaclass=BaseAPIClientMeta):

    class Meta:
        abstract = True

    def __init__(self, base_url: str):
        self._base_url = base_url
        self._session = Session()

    def _make_request(self, rule: Rule, body=None):
        response = self._session.request(
            rule.method,
            urljoin(self._base_url, rule.api_path),
            data=body
        )

        # Error handling a little bit later - that should
        # be done with hooks

        # Not everything is JSON - but making the assumption

        # everything is for the time being
        response_body = response.json()
        return rule.response(response_body)
