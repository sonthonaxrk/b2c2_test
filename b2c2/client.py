import warnings
import asyncio
import requests.adapters
import os
import uuid
import logging

from b2c2 import __version__
from b2c2.websocket import Fanout
from b2c2.views.instrument import InstrumentView
from b2c2.views.quote import QuoteView
from b2c2.views.history import HistoryView
from b2c2.views.balance import BalanceView
from b2c2.open_api_client import OpenAPIClient
from b2c2.models import (
    Instruments, RequestForQuote, Quote,
    Trade, TradeResponse, Balances
)


class _gui_descriptor:
    def __init__(self, gui_cls):
        self._gui_cls = gui_cls

    def __get__(self, _obj, objtype=None):
        """
        Returns a GUI element that's bound to
        the client instance.

        Makes _client implicitly available.

        I know this looks dirty, but the client
        is effectively the application object,
        and that's typically a singleton. The alternative
        is to pass around the client to everything (messy code
        everywhere) or use a threadlocal (very dirty).
        """
        if not _obj._client._loop:
            warnings.warn(
                'Trying to access GUI without an event loop.',
                RuntimeWarning
            )

        return type(
            self._gui_cls.__name__, (self._gui_cls, ),
            {'_client': _obj._client}
        )


class _gui:
    instrument_selector = _gui_descriptor(InstrumentView)
    quote_executor = _gui_descriptor(QuoteView)
    history = _gui_descriptor(HistoryView)
    balances = _gui_descriptor(BalanceView)

    def __init__(self, client):
        self._client = client


class History:
    """
    Interactive users will probably want a history
    of what they have requested and traded.
    """

    def add_trade(self, trade: TradeResponse):
        self.completed_trades.append(trade)
        self._trade_fanout._queue.put_nowait(trade)

    def add_quote(self, quote: Quote):
        self.quotes.append(quote)
        self._quote_fanout._queue.put_nowait(quote)

    def __init__(self):
        self.completed_trades = []
        self.quotes = []
        # If I had more time I would do some backpressure
        # error handling.
        self._trade_fanout = Fanout(asyncio.Queue())
        self._quote_fanout = Fanout(asyncio.Queue())


class B2C2AuthAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, client: 'BaseB2C2APIClient', *args, **kwargs):
        self._client = client
        super().__init__(*args, **kwargs)

    def add_headers(self, request, **kwargs):
        request.headers.update(self._client._get_headers())
        super().add_headers(request, **kwargs)

    def send(self, request, *args, **kwargs):
        # Logging goes here
        self._client._logger.debug('Outgoing Request %s', request)
        response = super().send(request, *args, **kwargs)
        self._client._logger.debug('Incomming Response %s', response)
        return response


class env:
    uat = {
        'websocket': 'wss://socket.uat.b2c2.net/quotes',
        'rest_api': 'https://api.uat.b2c2.net/',
    }


class BaseB2C2APIClient(OpenAPIClient):
    """
    Base API client. Useful for application
    developers.
    """

    def __init__(self, env: dict, api_key=None, **kwargs):
        if api_key:
            warnings.warn(
                'Passing the API key through the client is '
                'insecure. Please consider using environment '
                'variables.',
                UserWarning
            )
            self._api_key = api_key
        elif 'B2C2_APIKEY' in os.environ:
            self._api_key = os.environ['B2C2_APIKEY']
        else:
            raise ValueError('No API Key Found')

        self.env = env
        super().__init__(self.env['rest_api'])
        adapter = B2C2AuthAdapter(self)
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)
        self._logger = self._get_logger()

    # Exposing this for tests
    def _get_request_id(self):
        return str(uuid.uuid4())

    def _get_headers(self):
        return {
            'User-Agent': f'RolloB2C2Client/{__version__}',
            'X-Request-ID': self._get_request_id(),
            'Authorization': f'Token {self._api_key}'
        }

    def _get_logger(self):
        return logging.getLogger(
            'b2c2.client.{}'.format(
                self._api_key[:5]
            )
        )

    class Meta:
        # This is a poor mans OpenAPI definition.
        #
        # This is passed into the Meta class of the B2C2APIClient
        # and it's methods are generated from it.
        #
        # I did not create a real OpenAPI specification due to time
        # constraints. But this *should* suffice to get the gist of
        # what I am doing across.
        definition = {
            '/instruments/': {
                'GET': {
                    'response': Instruments
                }
            },
            '/request_for_quote/': {
                'POST': {
                    'body': RequestForQuote,
                    'response': Quote
                }
            },
            '/trade/': {
                'POST': {
                    'body': Trade,
                    'response': TradeResponse,
                }
            },
            '/balance/': {
                'GET': {
                    'response': Balances
                }
            }
        }


class B2C2APIClient(BaseB2C2APIClient):
    """
    Rich GUI API client. Useful for exploring
    data on Jupyter.
    """
    # Methods like
    # get_instruments(self)
    # are autogenerated from the open spec

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The Gui class uses descriptors to
        # provide a reference to clients
        self._loop = None

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            warnings.warn(
                'No event loop found. The GUI must run '
                'in an asyncio event loop. Jupyter should '
                'provide this. Try the line magic `%%gui async`.',
                RuntimeWarning
            )

        self.gui = _gui(self)
        self.history = History()

    # I appreciate that I am copying the annotations
    # onto these overriden methods. I think there's
    # a way to get mypy to automatically do this.

    def post_trade(self, body: Trade) -> TradeResponse:
        resp = super().post_trade(body)
        self.history.add_trade(resp)
        return resp

    def post_request_for_quote(self, body: RequestForQuote) -> Quote:
        resp = super().post_request_for_quote(body)
        self.history.add_quote(resp)
        return resp
