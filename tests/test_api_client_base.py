from unittest.mock import MagicMock
from b2c2.open_api_client import OpenAPIClient


class APITestClient(OpenAPIClient):
    def __init__(self, *args, **kwargs):
        super().__init__(
            base_url='', *args, **kwargs
        )
        self._session = MagicMock()

    class Meta:
        definition = {
            '/test/': {
                # Endpoint that takes a string and returns
                # an integer
                'POST': {
                    'response': str,
                    'body': int
                },
                'GET': {
                    'response': int,
                }
            }
        }


def test_has_method():
    client = APITestClient()
    assert client.get_test


def test_return_type():
    client = APITestClient()
    assert client.get_test.__annotations__['return'] == int


def test_body_parameterization():
    client = APITestClient()
    client._session.request().body = 1
    assert client.get_test() == 1
