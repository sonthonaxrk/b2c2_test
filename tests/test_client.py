import itertools

from unittest.mock import MagicMock
from b2c2.client import BaseB2C2APIClient, B2C2AuthAdapter, env
from b2c2 import __version__


# There are a number of ways of mocking the requests lib.
# This is the most transparent and least destructive way of doing it.
class B2C2TestAuthAdapter(B2C2AuthAdapter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection = MagicMock()

    def init_poolmanager(self, *args, **kwargs):
        self.poolmanager = MagicMock()

    def get_connection(self, url, proxies):
        return self.connection


class BaseB2C2TestAPIClient(BaseB2C2APIClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        adapter = B2C2TestAuthAdapter(self)
        self.connection = adapter.connection
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)
        self._session.hooks = {'response': []}
        self._logger = MagicMock()
        self._uuid_mock = MagicMock(
            # Infinite generator of increasing str ints
            side_effect=map(str, itertools.count())
        )

    def _get_request_id(self):
        return self._uuid_mock()


def test_auth_and_headers():
    client = BaseB2C2TestAPIClient(env.uat, api_key='api_key')
    resp = client._session.get('http://test/route')

    assert resp.request.headers.items() >= {  # is superset
        'User-Agent': f'RolloB2C2Client/{__version__}',
        'X-Request-ID': '0',
        'Authorization': 'Token api_key'
    }.items()

    assert client._logger.debug.call_count == 2
