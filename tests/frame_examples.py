import asyncio

from weakref import WeakKeyDictionary
from b2c2.frames import (
    ErrorResponseFrame, TradableInstrumentsFrame, UsernameUpdateFrame,
    QuoteUnsubscribeResponseFrame, QuoteStreamFrame,
    QuoteSubscribeResponseFrame
)


class frames:
    """
    Just a namespace for some websocket test utils
    (thus the lowercase classname).
    """

    tradable_instruments = {
        'event': 'tradable_instruments',
        'tradable_instruments': ['BTCUSD', 'BTCEUR', 'ETHEUR'],
        'success': True
    }

    error_response_bad_instrument = {
        'event': 'subscribe',
        'success': False,
        'tag': '8c14906f-4244-4b51-86bc-553711167960',
        'error_code': 3004,
        'error_message': 'Invalid subscription request.',
        'errors': {'instrument': ['Length must be 6.', 'Must be uppercase.']}
    }

    subscribe_request = {
        "event": "subscribe",
        "instrument": "BTCUSD.SPOT",
        "levels": [1, 3],
        "tag": "8c14906f-4244-4b51-86bc-553711167960"
    }

    subscribe_stream_frame = {
        "levels": {
            "buy": [
                {"quantity": "1", "price": "8944.4"},
                {"quantity": "3", "price": "8955.1"}
            ],
            "sell": [
                {"quantity": "1", "price": "8940.5"},
                {"quantity": "3", "price": "8918.7"}
            ]
        },
        "success": True,
        "event": "price",
        "instrument": "BTCUSD.SPOT",
        "timestamp": 1516288053582
    }

    unsub_req = {
      "event": "unsubscribe",
      "instrument": "BTCUSD.SPOT",
      "tag": "8c14906f-4244-4b51-86bc-553711167960"
    }

    unsub_response = {
        "event": "unsubscribe",
        "instrument": "BTCUSD.SPOT",
        "tag": "8c14906f-4244-4b51-86bc-553711167960",
        "success": True
    }

    subscribe_request_success = {
        "event": "subscribe",
        "instrument": "BTCUSD.SPOT",
        "levels": [1, 3],
        "tag": "8c14906f-4244-4b51-86bc-553711167960",
        "success": True
    }

    tradable_instruments_update = {
        "event": "tradable_instruments_update",
        "tradable_instruments": ["BTCUSD", "BTCEUR"],
        "success": True
    }

    username_update = {
        "event": "username_update",
        "old_username": "test@b2c2.com",
        "new_username": "new@b2c2.com",
        "success": True
    }

    cls_mapping = WeakKeyDictionary([
        (TradableInstrumentsFrame, tradable_instruments),
        (ErrorResponseFrame, error_response_bad_instrument),
        (QuoteStreamFrame, subscribe_stream_frame),
        (QuoteSubscribeResponseFrame, subscribe_request_success),
        (QuoteUnsubscribeResponseFrame, unsub_response),
        (TradableInstrumentsFrame, tradable_instruments),
        (UsernameUpdateFrame, username_update),
    ])

    @staticmethod
    def stream(queue: asyncio.Queue):
        """
        Helper method for generating a fake async
        stream for simulating websockets.
        """
        async def _stream():
            while True:
                frame = await queue.get()
                if frame is None:
                    break

                yield frame

        return _stream
