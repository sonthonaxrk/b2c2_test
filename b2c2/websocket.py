import websockets
import asyncio
# This is a nice little pattern matching library
# (I hate if, elif, elif, chains with a passion)
import pampy

from weakref import WeakKeyDictionary, WeakSet
from contextlib import contextmanager
from collections import defaultdict
from typing import Dict, Any

from b2c2.frames import (
    ErrorResponseFrame, TradableInstrumentsFrame, UsernameUpdateFrame,
    QuoteUnsubscribeResponseFrame, QuoteResponseFrame
)

# create a queue that can create subqueues
class Fanout(asyncio.Queue):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._listeners = WeakSet()





class B2C2WebsocketClient:
    """
    These are the websocket frame types


        - tradable_instruments and tradable_instruments_update
        - username_update

    This is an obvious choice for a context manager:

        - subscribe - request
        - subscribe - stream response
        - unsubscribe - request
    """

    # List of rules - paired (not the most readable API, but
    # it is a lot more readable, testable, and maintainable
    # than the if else statements).
    _frame_matching_rules = (
        # This pair is a matching rule. It will match
        # all dictionaries where success=False and the
        # error_code=Any. On match the lambda is called and returned
        {'success': False, 'error_code': Any},
        lambda _: ErrorResponseFrame,

        # Statements are checked in order (so check for errors first)
        {'event': 'tradable_instruments'},
        lambda _: TradableInstrumentsFrame,
        
        {'event': 'tradable_instruments_update'},
        lambda _: TradableInstrumentsFrame,

        {'event': 'username_update'},
        lambda _: UsernameUpdateFrame,

        {'event': 'unsubscribe', 'instrument': str},
        lambda _: QuoteUnsubscribeResponseFrame,

        {'event': 'price', 'instrument': str},
        lambda _: QuoteResponseFrame,
    )

    async def stream(self):
        # Turn the websocket into an async generator
        async with websockets.connect(
            'wss://echo.websocket.org'
        ) as ws:
            while True:
                yield await websocket.recv()


    async def listen(self):
        async for frame in self.stream():
            # Do some pattern matching and enque the message
            frame_cls = self._match_frame(frame)
            frame = frame_cls(**frame)
            callback = self._resp_callbacks[frame_cls]
            await callback(frame)

    def _match_frame(self, frame):
        return pampy.match(frame, *self._frame_matching_rules)

    def __init__(self, *args):
        self._resp_callbacks = WeakKeyDictionary([
            (TradableInstrumentsFrame, self._on_tradable_instrument),
        ])

        # Maybe refactor this out? 
        self._tradable_instrument_queue = asyncio.LifoQueue()
        self._tradable_instrument_fanout_queues = WeakSet()
        self._tradable_instrument_fanout_task = None

    async def _on_tradable_instrument(self, frame: TradableInstrumentsFrame):
        self._tradable_instrument_queue.put_nowait(frame)

    def get_tradable_instrument_stream(self):
        if not self._tradable_instrument_fanout_task:
            self._tradable_instrument_fanout_task = (
                asyncio.create_task(self._on_tradable_instrument_fanout_job())
            )

        queue = asyncio.Queue()
        print(repr(queue))
        self._tradable_instrument_fanout_queues.add(queue)
        
        async def f():
            while True:
                yield await queue.get()

        return f()

    async def _on_tradable_instrument_fanout_job(self):
        while True:
            frame = await self._tradable_instrument_queue.get()
            for queue in self._tradable_instrument_fanout_queues:
                queue.put_nowait(frame)
