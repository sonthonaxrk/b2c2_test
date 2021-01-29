from functools import lru_cache
from b2c2.frames import ErrorResponseFrame
from http import HTTPStatus


class B2C2ClientException(Exception):
    def __init__(self, message, error_response: ErrorResponseFrame):
        self.error_response = error_response
        super().__init__(message)


class B2C2HTTPException(B2C2ClientException):
    pass


class WebsocketException(B2C2ClientException):
    pass


class QuoteException(WebsocketException):
    pass


class QuoteExceptions:
    @lru_cache(maxsize=None)
    def __getattr__(self, name):
        return type(name, (QuoteException, ), {})


class HttpExceptions:

    _names = dict([
        (
            s.value, 'B2C2' + s.name.title().replace('_', '')
        ) for s in HTTPStatus
    ])

    @lru_cache(maxsize=None)
    def __getattr__(self, name):
        return type(name, (B2C2HTTPException, ), {})

    def get_exception(self, code: int):
        name = self._names[code]
        return getattr(self, name)


quote_exceptions = QuoteExceptions()
http_exceptions = HttpExceptions()
