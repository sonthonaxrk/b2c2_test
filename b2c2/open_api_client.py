from typing import Any, Generator, NamedTuple
from requests import Session
from urllib.parse import urljoin
from pydantic import BaseModel


class Rule(NamedTuple):
    method: str
    api_path: str
    response: Any
    body: Any


class OpenAPIClientMeta(type):
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
        Meta = dct.get('Meta')

        # If not meta class use the MRO list
        # to get the last set meta class
        if not Meta:
            for base in bases:
                if hasattr(base, 'Meta'):
                    Meta = base.Meta
                    break
            else:
                # shoudln't happen
                raise RuntimeError('No meta class found')

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

            # If it's already in the cls dct, it's probably
            # already been bound. No need to add it to a subclass again
            if method_name not in dct:
                constructed_methods[method_name] = method
                dct[method_name] = cls._wrap_request_in_annotations(rule)

        # This is the same the built in function type(name, bases, dict)
        return super().__new__(cls, name, bases, dct)


class OpenAPIClient(metaclass=OpenAPIClientMeta):

    class Meta:
        abstract = True

    def __init__(self, base_url: str):
        self._base_url = base_url
        self._session = Session()

    def _make_request(self, rule: Rule, body=None):

        if isinstance(body, BaseModel):
            response = self._session.request(
                rule.method,
                urljoin(self._base_url, rule.api_path),
                headers={'Content-type': 'application/json'},
                data=body.json(),
            )
        else:
            response = self._session.request(
                rule.method,
                urljoin(self._base_url, rule.api_path),
                data=body,
            )

        # Not everything is JSON, connection errors and
        # proxy errors can return HTML. However as per
        # the spec of the API everything is JSON
        if issubclass(rule.response, BaseModel):
            response_body = response.json()
            response_wrapped = rule.response.parse_obj(response_body)
            response_wrapped._client = self
        else:
            response_wrapped = rule.response(response.text)

        # TODO: find a better way of binding model
        # instances to the client
        return response_wrapped
